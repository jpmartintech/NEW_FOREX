"""Run P13C: a causal six-month training, one-month forward GA factory."""
from __future__ import annotations

import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from new_forex.backtest.evaluator import evaluate_light, evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.generators.genetic import GAConfig, run_genetic, write_archive
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.rolling_historical import portfolio_ledger
from run_p08_rolling_factory import _load_market_until
from run_p13_six_month_rolling import _census, _evaluate_metrics, _metrics, _portfolio_metrics, _window

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p13c_rolling_6m_1m.yaml"
OUT = ROOT / "reports/p13c_artifacts"


def months(config: dict) -> list[dict]:
    starts = pd.date_range(config["calendar"]["start_forward"], config["calendar"]["end_forward_exclusive"], freq="MS", inclusive="left")
    return [{"generation": f"G{index + 1:03d}", "index": index, "training_start": (start - pd.DateOffset(months=6)).strftime("%Y-%m-%d"), "training_end": start.strftime("%Y-%m-%d"), "forward_start": start.strftime("%Y-%m-%d"), "forward_end": (start + pd.DateOffset(months=1)).strftime("%Y-%m-%d"), "forward_month": str(start.to_period("M"))} for index, start in enumerate(starts)]


def assert_sources(config: dict, specs: list[dict]) -> None:
    data = ROOT / "data/derived/m15/EURUSD.parquet"
    if not data.exists() or file_sha256(ROOT / "configs/splits.yaml") != config["data"]["splits_sha256"]:
        raise ValueError("EURUSD source or splits hash mismatch")
    policy = DataAccessPolicy.load()
    policy.assert_readable(Partition.DEVELOPMENT_WF)
    policy.assert_readable(Partition.PROCEDURE_VALIDATION)
    for spec in specs:
        if pd.Timestamp(spec["forward_end"]) > pd.Timestamp(config["execution"]["max_source_end_exclusive"]):
            raise ValueError("P13C window exceeds frozen source end")
        start = pd.Timestamp(spec["training_start"])
        end = pd.Timestamp(spec["forward_end"])
        if policy.partition_for(start) is Partition.FINAL_HOLDOUT or policy.partition_for(end - pd.Timedelta(nanoseconds=1)) is Partition.FINAL_HOLDOUT:
            raise ValueError("P13C window intersects the sealed holdout")
        for partition in (Partition.DEVELOPMENT_WF, Partition.PROCEDURE_VALIDATION):
            window = policy.window(partition)
            if start < (window.end or end) and end > window.start:
                policy.assert_readable(partition)


def archive_path(generation: str) -> Path:
    return OUT / generation / "ga_archive.jsonl"


def load_archive(path: Path) -> dict[str, StrategyDefinition]:
    result = {}
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
            if strategy.canonical_hash != row["canonical_hash"]:
                raise ValueError("canonical archive hash mismatch")
            result[row["canonical_hash"]] = strategy
    return result


def generate_archive(market, spec: dict, config: dict, ga_cfg: GAConfig) -> dict[str, StrategyDefinition]:
    path = archive_path(spec["generation"])
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    if path.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if int(manifest.get("n_evaluated", -1)) == 100_000:
            population = load_archive(path)
            if len(population) == 100_000:
                return population
    train_window = _window(market, spec["training_start"], spec["training_end"])

    def fitness(batch):
        return _metrics(evaluate_light(market, batch, exec_tf="H1", window=train_window))["expectancy_R"]

    seed = int(config["generation"]["seed_base"]) + spec["index"]
    result = run_genetic("EURUSD", fitness, ga_cfg, seed=seed)
    if result.n_evaluated != 100_000:
        raise ValueError(f"incomplete GA generation {spec['generation']}: {result.n_evaluated}")
    write_archive(result, path, run_id=spec["generation"] + "-ga", seed=seed, config=ga_cfg)
    return {key: value[0] for key, value in result.archive.items()}


def training_frame(market, population: dict[str, StrategyDefinition], window: tuple[int, int]) -> pd.DataFrame:
    hashes = sorted(population)
    strategies = [population[key] for key in hashes]
    x1 = _evaluate_metrics(market, strategies, window, 1.0)
    x2 = _evaluate_metrics(market, strategies, window, 2.0)
    rows = []
    for i, key in enumerate(hashes):
        rows.append({"strategy_hash": key, "training_n_trades": int(x1["n_trades"][i]), "training_expectancy_R": float(x1["expectancy_R"][i]), "training_profit_factor": float(x1["profit_factor"][i]), "training_return": float(x1["return"][i]), "training_max_drawdown": float(x1["max_drawdown"][i]), "training_x2_expectancy_R": float(x2["expectancy_R"][i]), "direction": population[key].direction, "complexity": len(population[key].predicates)})
    return pd.DataFrame(rows)


def composition_groups(training: pd.DataFrame, config: dict, index: int) -> list[dict]:
    eligible = sorted(training.loc[(training.training_profit_factor > 1.30) & (training.training_n_trades > 30), "strategy_hash"])
    full = sorted(training.strategy_hash)
    size = int(config["portfolio"]["size"])
    rows = []
    for group, universe, base in (("selected", eligible, config["selection"]["selected_seed_base"]), ("control_a", eligible, config["selection"]["control_a_seed_base"]), ("control_b", full, config["selection"]["control_b_seed_base"])):
        for replicate in range(int(config["selection"]["composition_replicates"])):
            seed = int(base) + index * 100_000 + replicate
            chosen = sorted(random.Random(seed).sample(universe, size)) if len(universe) >= size else list(universe)
            action = "five_uniform_without_replacement" if len(universe) >= size else ("partial_capital" if chosen else "cash")
            rows.append({"generation": f"G{index + 1:03d}", "group": group, "replicate": replicate, "seed": seed, "eligible_n": len(eligible), "universe_n": len(universe), "selected": chosen, "action": action})
    return rows


def evaluate_compositions(market, spec: dict, config: dict, population: dict[str, StrategyDefinition], compositions: list[dict], forward_window: tuple[int, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    ledgers_dir = OUT / spec["generation"] / "ledgers"
    ledgers_dir.mkdir(parents=True, exist_ok=True)
    all_keys = sorted({key for row in compositions for key in row["selected"]})
    cache: dict[tuple[str, float], pd.DataFrame] = {}
    def load_or_evaluate_baseline(key: str) -> tuple[str, pd.DataFrame]:
        baseline_path = ledgers_dir / f"{key}_baseline.parquet"
        if baseline_path.exists():
            baseline = pd.read_parquet(baseline_path)
        else:
            rich = evaluate_rich(market, population[key], exec_tf="H1", cost_multiplier=1.0, window=forward_window)
            baseline = _ledger_frame(rich.trades, population[key], market)
            baseline.to_parquet(baseline_path, index=False)
        return key, baseline

    with ThreadPoolExecutor(max_workers=8) as executor:
        for key, baseline in executor.map(load_or_evaluate_baseline, all_keys):
            cache[(key, 1.0)] = baseline
    for key in all_keys:
        baseline = cache[(key, 1.0)]
        x2_path = ledgers_dir / f"{key}_costs_x2.parquet"
        if x2_path.exists():
            x2 = pd.read_parquet(x2_path)
        else:
            x2 = baseline.copy()
            direction = np.where(x2["direction"].eq("LONG"), 1.0, -1.0)
            gross_pnl = direction * (x2["exit_price"] - x2["entry_price"]) + x2["funding"]
            friction = gross_pnl - x2["pnl_net"]
            x2["pnl_net"] = gross_pnl - 2.0 * friction
            x2["transaction_cost"] = x2["pnl_net"]
            x2["result_R"] = x2["pnl_net"] / x2["risk"]
            x2.to_parquet(x2_path, index=False)
        cache[(key, 2.0)] = x2
    def evaluate_composition(composition: dict) -> list[dict]:
        rows = []
        chosen = composition["selected"]
        for label, cost in (("baseline", 1.0), ("costs_x2", 2.0)):
            frames = [cache[(key, cost)] for key in chosen]
            portfolio = portfolio_ledger(list(zip(chosen, frames, strict=True)), risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"]) if chosen else pd.DataFrame()
            if cost == 1.0 and chosen:
                gross_frames = []
                for key in chosen:
                    base = cache[(key, 1.0)].copy()
                    x2 = cache[(key, 2.0)]
                    ids = ["entry_timestamp", "exit_timestamp"]
                    if not base[ids].reset_index(drop=True).equals(x2[ids].reset_index(drop=True)):
                        raise ValueError("baseline/x2 operation identity mismatch")
                    base["result_R"] = 2 * base["result_R"].to_numpy(float) - x2["result_R"].to_numpy(float)
                    gross_frames.append((key, base))
                gross = portfolio_ledger(gross_frames, risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"])
            metric = _portfolio_metrics(portfolio, label, gross if cost == 1.0 and chosen else None)
            rows.append({**{key: value for key, value in composition.items() if key != "selected"}, "cost": label, "n_trades": metric["n_trades"], "return": metric["return"], "max_drawdown": metric["max_drawdown"], "pnl_net": metric["pnl_net"], "expectancy_R": metric["expectancy_R"], "profit_factor": metric["profit_factor"], "pnl_gross": metric.get("pnl_gross", 0.0), "return_gross": metric.get("return_gross", 0.0), "cost_absolute": metric.get("cost_absolute", 0.0), "expectancy_gross_R": metric.get("expectancy_gross_R", 0.0)})
        return rows

    rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for result in executor.map(evaluate_composition, compositions):
            rows.extend(result)
    return pd.DataFrame(rows), pd.DataFrame(compositions)


def run_generation(market, spec: dict, config: dict, ga_cfg: GAConfig) -> dict:
    generation_dir = OUT / spec["generation"]
    generation_dir.mkdir(parents=True, exist_ok=True)
    population = generate_archive(market, spec, config, ga_cfg)
    train = training_frame(market, population, _window(market, spec["training_start"], spec["training_end"]))
    train["generation"] = spec["generation"]
    train["generator"] = "ga"
    train.to_parquet(generation_dir / "training_metrics.parquet", index=False)
    compositions = composition_groups(train, config, spec["index"])
    forward = _window(market, spec["forward_start"], spec["forward_end"])
    portfolio_results, composition_frame = evaluate_compositions(market, spec, config, population, compositions, forward)
    selected_hashes = sorted({key for row in compositions for key in row["selected"]})
    forward_rows = []
    if selected_hashes:
        x1 = _evaluate_metrics(market, [population[key] for key in selected_hashes], forward, 1.0)
        x2 = _evaluate_metrics(market, [population[key] for key in selected_hashes], forward, 2.0)
        selected_training = train.set_index("strategy_hash").loc[selected_hashes].to_dict(orient="index")
        census = _census(selected_hashes, selected_training, x1, x2)
        census["generation"] = spec["generation"]
        census["forward_month"] = spec["forward_month"]
        census.to_parquet(generation_dir / "selected_forward_metrics.parquet", index=False)
        forward_rows.append(census)
    composition_frame.to_json(generation_dir / "compositions.jsonl", orient="records", lines=True)
    portfolio_results.to_csv(generation_dir / "portfolio_results.csv", index=False)
    return {"generation": spec["generation"], "training": train, "forward": pd.concat(forward_rows, ignore_index=True) if forward_rows else pd.DataFrame(), "portfolios": portfolio_results, "compositions": composition_frame}


def rolling_summary(portfolios: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    for (group, replicate, cost), part in portfolios.groupby(["group", "replicate", "cost"], sort=True):
        part = part.sort_values("generation")
        curve = np.cumprod(1 + part["return"].to_numpy(float))
        peaks = np.maximum.accumulate(curve)
        rows.append({"group": group, "replicate": replicate, "cost": cost, "months": len(part), "final_return": curve[-1] - 1 if len(curve) else 0.0, "cagr": curve[-1] ** (12 / len(part)) - 1 if len(curve) else 0.0, "max_drawdown": float((1 - curve / peaks).max()) if len(curve) else 0.0, "operations": int(part.n_trades.sum()), "positive_months": int((part["return"] > 0).sum()), "negative_months": int((part["return"] < 0).sum()), "best_month": float(part["return"].max()) if len(part) else 0.0, "worst_month": float(part["return"].min()) if len(part) else 0.0})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    specs = months(config)
    if len(specs) != 54:
        raise ValueError("P13C must contain exactly 54 monthly generations")
    assert_sources(config, specs)
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed": []}
    from_run_end = "2016-08-01" if args.smoke else config["execution"]["max_source_end_exclusive"]
    market = _load_market_until(from_run_end)
    ga_cfg = GAConfig(population=1000, generations=102, max_unique_evaluations=100_000, elite=20, tournament=4, crossover_rate=0.7, mutation_rate=0.4, immigrant_rate=0.1, max_predicates=4)
    run_specs = specs[:1] if args.smoke else specs
    all_forward, all_portfolios, all_compositions = [], [], []
    for spec in run_specs:
        if not args.smoke and spec["generation"] in checkpoint["completed"]:
            generation_dir = OUT / spec["generation"]
            all_forward.append(pd.read_parquet(generation_dir / "selected_forward_metrics.parquet") if (generation_dir / "selected_forward_metrics.parquet").exists() else pd.DataFrame())
            all_portfolios.append(pd.read_csv(generation_dir / "portfolio_results.csv"))
            all_compositions.append(pd.read_json(generation_dir / "compositions.jsonl", lines=True))
            continue
        result = run_generation(market, spec, config, ga_cfg)
        all_forward.append(result["forward"])
        all_portfolios.append(result["portfolios"])
        all_compositions.append(result["compositions"])
        if not args.smoke:
            checkpoint["completed"].append(spec["generation"])
            checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")
    forward = pd.concat([x for x in all_forward if not x.empty], ignore_index=True) if any(not x.empty for x in all_forward) else pd.DataFrame()
    portfolios = pd.concat(all_portfolios, ignore_index=True)
    compositions = pd.concat(all_compositions, ignore_index=True)
    if not args.smoke:
        forward.to_parquet(OUT / "selected_forward_metrics_all.parquet", index=False)
        portfolios.to_parquet(OUT / "portfolio_results_all.parquet", index=False)
        compositions.to_json(OUT / "compositions_all.jsonl", orient="records", lines=True)
        rolling = rolling_summary(portfolios, config)
        rolling.to_parquet(OUT / "rolling_trajectories.parquet", index=False)
        monthly = portfolios.groupby(["generation", "group", "cost"], as_index=False).agg(median_return=("return", "median"), positive_pct=("return", lambda x: float((x > 0).mean())), median_max_drawdown=("max_drawdown", "median"), operations=("n_trades", "sum"), median_expectancy_R=("expectancy_R", "median"), median_gross_expectancy_R=("expectancy_gross_R", "median"))
        monthly.to_csv(OUT / "monthly_summary.csv", index=False)
        manifest = {"policy_id": config["policy_id"], "config_sha256": file_sha256(CONFIG), "generations": 54, "census_rows": len(forward), "portfolio_rows": len(portfolios), "composition_rows": len(compositions), "ga_evaluations": 5_400_000, "budget_exact": True, "holdout_used": False, "smoke": False, "elapsed_seconds": time.perf_counter() - started}
        (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        report = ROOT / "reports/p13c_rolling_6m_1m.md"
        report.write_text("\n".join(["# P13C — Rolling Genetic Factory 6M/1M", "", f"Protocol: `{config['policy_id']}`", f"Config SHA256: `{manifest['config_sha256']}`", "", "54 generaciones cronológicas, 100.000 evaluaciones GA exactas por generación. Los resultados mensuales, composiciones, ledgers y trayectorias están en `reports/p13c_artifacts/`.", "", "La interpretación debe separar selección individual, cartera y costes x2. Este estudio reutiliza periodos ya observados en investigaciones anteriores y no es validación completamente independiente.", "", "No se accedió al holdout 2023–2026 ni se ejecutaron operaciones reales.", ""]))
        print(json.dumps(manifest, indent=2))
    else:
        print(json.dumps({"smoke": True, "generations": len(run_specs), "portfolio_rows": len(portfolios)}, indent=2))


if __name__ == "__main__":
    main()
