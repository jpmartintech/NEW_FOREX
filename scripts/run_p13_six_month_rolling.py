"""Run the frozen six-month monthly GA versus random-search factory."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from new_forex.backtest.evaluator import evaluate_light, evaluate_rich
from new_forex.backtest.semantics import AGG
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.generators.genetic import GAConfig, GAResult, run_genetic, write_archive
from new_forex.grammar import random_strategy
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p13_six_month_rolling.yaml"
OUT = ROOT / "reports/p13_artifacts"


def _metrics(rows: np.ndarray) -> dict[str, np.ndarray]:
    n = rows[:, AGG["n_trades"]].astype(np.int64)
    total = rows[:, AGG["sum_r"]].astype(float)
    wins = rows[:, AGG["gross_win_r"]].astype(float)
    losses = rows[:, AGG["gross_loss_r"]].astype(float)
    pf = np.divide(wins, losses, out=np.zeros(len(n)), where=losses != 0)
    pf[(losses == 0) & (wins > 0)] = np.inf
    return {
        "n_trades": n, "total_R": total, "expectancy_R": np.divide(total, n, out=np.zeros(len(n)), where=n != 0),
        "profit_factor": pf, "return": rows[:, AGG["final_equity"]].astype(float) - 1.0,
        "max_drawdown": rows[:, AGG["max_dd"]].astype(float),
    }


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


def _months(config: dict) -> list[dict]:
    starts = pd.date_range(config["windows"]["start_forward"], config["windows"]["end_forward_exclusive"], freq="MS", inclusive="left")
    out = []
    for index, forward_start in enumerate(starts):
        forward_end = forward_start + pd.DateOffset(months=1)
        train_start = forward_start - pd.DateOffset(months=6)
        out.append({"generation": f"G{index + 1:02d}", "index": index, "training_start": train_start.strftime("%Y-%m-%d"),
                    "training_end": forward_start.strftime("%Y-%m-%d"), "forward_start": forward_start.strftime("%Y-%m-%d"),
                    "forward_end": forward_end.strftime("%Y-%m-%d"), "forward_month": str(forward_start.to_period("M"))})
    return out


def _assert_sources(config: dict) -> None:
    data = ROOT / "data/derived/m15/EURUSD.parquet"
    if file_sha256(ROOT / "configs/splits.yaml") != config["data"]["splits_sha256"]:
        raise ValueError("splits SHA256 mismatch")
    if not data.exists():
        raise FileNotFoundError(data)
    policy = DataAccessPolicy.load()
    policy.assert_readable(Partition.DEVELOPMENT_WF)
    for month in _months(config):
        if pd.Timestamp(month["forward_end"]) > pd.Timestamp(config["execution"]["max_source_end_exclusive"]):
            raise ValueError("P13 window exceeds frozen source end")
        policy.assert_range(month["training_start"], month["forward_end"])


def _archive_path(generation: str, generator: str) -> Path:
    return OUT / generation / f"{generator}_archive.jsonl"


def _write_random_archive(strategies: dict[str, StrategyDefinition], fitness: dict[str, float], path: Path, seed: int, cfg: GAConfig) -> dict:
    result = GAResult(archive={key: (strategy, fitness[key]) for key, strategy in strategies.items()})
    return write_archive(result, path, run_id=path.parent.name + "-random", seed=seed, config=cfg)


def _random_population(pair: str, cfg: GAConfig, seed: int) -> dict[str, StrategyDefinition]:
    rng = np.random.default_rng(seed)
    strategies: dict[str, StrategyDefinition] = {}
    attempts = 0
    while len(strategies) < cfg.max_unique_evaluations:
        strategy = random_strategy(rng, pair, cfg.max_predicates)
        strategies.setdefault(strategy.canonical_hash, strategy)
        attempts += 1
    if attempts < len(strategies):
        raise ValueError("random search attempt accounting failure")
    return strategies


def _evaluate_metrics(market, strategies: list[StrategyDefinition], window: tuple[int, int], cost: float, chunk: int = 5000) -> dict[str, np.ndarray]:
    parts = []
    for first in range(0, len(strategies), chunk):
        parts.append(_metrics(evaluate_light(market, strategies[first:first + chunk], exec_tf="H1", cost_multiplier=cost, window=window)))
    return {key: np.concatenate([part[key] for part in parts]) for key in parts[0]}


def _census(hashes: list[str], training: dict[str, dict], x1: dict[str, np.ndarray], x2: dict[str, np.ndarray]) -> pd.DataFrame:
    rows = []
    for i, key in enumerate(hashes):
        gross_total = 2 * x1["total_R"][i] - x2["total_R"][i]
        n = int(x1["n_trades"][i])
        rows.append({"strategy_hash": key, **training[key], "forward_n_trades": n,
                     "forward_total_R": float(x1["total_R"][i]), "forward_expectancy_R": float(x1["expectancy_R"][i]),
                     "forward_profit_factor": float(x1["profit_factor"][i]), "forward_return": float(x1["return"][i]),
                     "forward_max_drawdown": float(x1["max_drawdown"][i]), "forward_x2_total_R": float(x2["total_R"][i]),
                     "forward_x2_expectancy_R": float(x2["expectancy_R"][i]), "forward_x2_profit_factor": float(x2["profit_factor"][i]),
                     "forward_x2_return": float(x2["return"][i]), "forward_x2_max_drawdown": float(x2["max_drawdown"][i]),
                     "forward_gross_total_R": float(gross_total), "forward_gross_expectancy_R": float(gross_total / n) if n else 0.0,
                     "cost_R_per_trade": float((gross_total - x1["total_R"][i]) / n) if n else np.nan,
                     "active": n > 0})
    return pd.DataFrame(rows)


def _selection(frame: pd.DataFrame, generator: str, generation_index: int, config: dict) -> dict:
    eligible = frame[(frame.training_profit_factor > 1.30) & (frame.training_n_trades > 250)]["strategy_hash"].sort_values().tolist()
    seed = int(config["selection"]["portfolio_seed_base"]) + generation_index * 10 + (0 if generator == "ga" else 1)
    size = int(config["portfolio"]["size"])
    if len(eligible) >= size:
        selected = sorted(random.Random(seed).sample(eligible, size))
        action = "uniform_without_replacement_size_5"
    elif eligible:
        selected = eligible
        action = "use_all_and_leave_capital_unallocated"
    else:
        selected = []
        action = "cash_no_active_strategies"
    return {"generator": generator, "eligible_n": len(eligible), "eligible_pct": len(eligible) / len(frame),
            "seed": seed, "selected": selected, "action": action}


def _portfolio_metrics(frame: pd.DataFrame, cost: str, gross: pd.DataFrame | None = None) -> dict:
    m = portfolio_metrics(frame)
    values = frame["result_R"].to_numpy(float) if not frame.empty else np.array([])
    wins, losses = values[values > 0].sum(), -values[values < 0].sum()
    result = {"cost": cost, "n_trades": m["n_trades"], "return": m["return"], "max_drawdown": m["max_drawdown"],
              "pnl_net": m["pnl"], "expectancy_R": float(values.mean()) if len(values) else 0.0,
              "profit_factor": float(wins / losses) if losses else (math.inf if wins > 0 else 0.0)}
    if gross is not None:
        result["return_gross"] = float(gross["equity"].iloc[-1] - 1.0) if not gross.empty else 0.0
        result["pnl_gross"] = float(gross["pnl"].sum()) if not gross.empty else 0.0
        result["expectancy_gross_R"] = float(gross["result_R"].mean()) if not gross.empty else 0.0
        result["cost_absolute"] = result["pnl_gross"] - result["pnl_net"]
    return result


def _census_summary(census: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (generation, generator), frame in census.groupby(["generation", "generator"], sort=True):
        for population, part in (("full", frame), ("eligible", frame[(frame.training_profit_factor > 1.30) & (frame.training_n_trades > 250)])):
            for cost, prefix in (("baseline", "forward"), ("costs_x2", "forward_x2")):
                active = part.forward_n_trades > 0
                exp = part[f"{prefix}_expectancy_R"]
                ret = part[f"{prefix}_return"]
                signature_frame = part[["forward_n_trades", f"{prefix}_expectancy_R", f"{prefix}_return", f"{prefix}_max_drawdown"]].astype(str)
                signature_count = int(signature_frame.drop_duplicates().shape[0]) if len(part) else 0
                rows.append({"generation": generation, "generator": generator, "population": population, "cost": cost,
                             "strategies": len(part), "active": int(active.sum()), "active_pct": float(active.mean()) if len(part) else 0.0,
                             "operations": int(part.forward_n_trades.sum()), "mean_gross_expectancy_R_active": float(part.loc[active, "forward_gross_expectancy_R"].mean()) if active.any() else None,
                             "median_gross_expectancy_R_active": float(part.loc[active, "forward_gross_expectancy_R"].median()) if active.any() else None,
                             "mean_net_expectancy_R_active": float(exp[active].mean()) if active.any() else None,
                             "median_net_expectancy_R_active": float(exp[active].median()) if active.any() else None,
                             "mean_return": float(ret.mean()) if len(part) else 0.0, "median_return": float(ret.median()) if len(part) else 0.0,
                             "positive_return_pct_active": float((ret[active] > 0).mean()) if active.any() else None,
                             "positive_x2_return_pct_active": float((part.loc[active, "forward_x2_return"] > 0).mean()) if active.any() else None,
                             "mean_cost_R_per_trade": float(part.loc[active, "cost_R_per_trade"].mean()) if active.any() else None,
                             "behavior_signatures": signature_count})
    return pd.DataFrame(rows)


def _rolling_trajectories(portfolios: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (generator, cost), frame in portfolios.groupby(["generator", "cost"], sort=True):
        frame = frame.sort_values("generation")
        curve = np.cumprod(1 + frame["return"].to_numpy(float))
        peaks = np.maximum.accumulate(curve)
        rows.append({"generator": generator, "cost": cost, "months": len(frame), "final_return": float(curve[-1] - 1.0),
                     "max_drawdown": float((1 - curve / peaks).max()), "positive_months": int((frame["return"] > 0).sum()),
                     "negative_months": int((frame["return"] < 0).sum()), "operations": int(frame["n_trades"].sum()),
                     "pnl_net": float(frame["pnl_net"].sum()), "pnl_gross": float(frame["pnl_gross"].sum()),
                     "cost_absolute": float(frame["cost_absolute"].sum())})
    return pd.DataFrame(rows)


def _run_generation(market, month: dict, config: dict, ga_cfg: GAConfig, smoke: bool) -> dict:
    generation_dir = OUT / month["generation"]
    generation_dir.mkdir(parents=True, exist_ok=True)
    train_window = _window(market, month["training_start"], month["training_end"])
    forward_window = _window(market, month["forward_start"], month["forward_end"])
    budget = min(ga_cfg.max_unique_evaluations, 500 if smoke else ga_cfg.max_unique_evaluations)
    local_cfg = GAConfig(**{**ga_cfg.__dict__, "max_unique_evaluations": budget, "generations": min(ga_cfg.generations, 5 if smoke else ga_cfg.generations)})
    populations: dict[str, dict[str, StrategyDefinition]] = {}
    manifests = {}
    for generator, seed in (("ga", int(config["generation"]["ga_seed_base"]) + month["index"]), ("random", int(config["generation"]["random_seed_base"]) + month["index"])):
        archive_path = _archive_path(month["generation"], generator)
        manifest_path = archive_path.with_suffix(archive_path.suffix + ".manifest.json")
        reusable = False
        if archive_path.exists() and manifest_path.exists() and not smoke:
            saved_manifest = json.loads(manifest_path.read_text())
            reusable = int(saved_manifest.get("n_evaluated", -1)) == local_cfg.max_unique_evaluations
        if reusable:
            loaded = {}
            with archive_path.open() as handle:
                for line in handle:
                    row = json.loads(line)
                    loaded[row["canonical_hash"]] = StrategyDefinition.from_json(json.dumps(row["strategy"]))
            populations[generator] = loaded
            manifests[generator] = json.loads(manifest_path.read_text())
            continue
        if generator == "ga":
            def fitness(batch):
                return _metrics(evaluate_light(market, batch, exec_tf="H1", window=train_window))["expectancy_R"]
            result = run_genetic("EURUSD", fitness, local_cfg, seed=seed)
            populations[generator] = {key: value[0] for key, value in result.archive.items()}
            manifests[generator] = write_archive(result, archive_path, run_id=month["generation"] + "-ga", seed=seed, config=local_cfg)
        else:
            population = _random_population("EURUSD", local_cfg, seed)
            strategies = list(population.values())
            fitness_values = _evaluate_metrics(market, strategies, train_window, 1.0)["expectancy_R"]
            fitness = dict(zip(population, fitness_values, strict=True))
            populations[generator] = population
            manifests[generator] = _write_random_archive(population, fitness, archive_path, seed, local_cfg)

    census_rows = []
    selections = []
    portfolio_inputs = []
    for generator, population in populations.items():
        hashes = sorted(population)
        strategies = [population[key] for key in hashes]
        train_x1 = _evaluate_metrics(market, strategies, train_window, 1.0)
        train_x2 = _evaluate_metrics(market, strategies, train_window, 2.0)
        training = {}
        for i, key in enumerate(hashes):
            training[key] = {"training_n_trades": int(train_x1["n_trades"][i]), "training_expectancy_R": float(train_x1["expectancy_R"][i]),
                             "training_profit_factor": float(train_x1["profit_factor"][i]), "training_return": float(train_x1["return"][i]),
                             "training_max_drawdown": float(train_x1["max_drawdown"][i]), "training_x2_expectancy_R": float(train_x2["expectancy_R"][i]),
                             "direction": population[key].direction, "complexity": len(population[key].predicates), "generator": generator}
        forward_x1 = _evaluate_metrics(market, strategies, forward_window, 1.0)
        forward_x2 = _evaluate_metrics(market, strategies, forward_window, 2.0)
        census = _census(hashes, training, forward_x1, forward_x2)
        census["generation"] = month["generation"]
        census["forward_month"] = month["forward_month"]
        census_rows.append(census)
        selection = _selection(census, generator, month["index"], config)
        selections.append({"generation": month["generation"], **selection})
        portfolio_inputs.append((generator, selection, population))
    census = pd.concat(census_rows, ignore_index=True)
    census.to_parquet(generation_dir / "forward_census.parquet", index=False)
    (generation_dir / "selections.json").write_text(json.dumps(selections, sort_keys=True, indent=2) + "\n")

    portfolio_rows = []
    ledgers_dir = generation_dir / "ledgers"
    ledgers_dir.mkdir(exist_ok=True)
    for generator, selection, population in portfolio_inputs:
        chosen = selection["selected"]
        if not chosen:
            for cost in ("baseline", "costs_x2"):
                portfolio_rows.append({"generation": month["generation"], "generator": generator, "cost": cost, "n_trades": 0, "return": 0.0, "return_gross": 0.0, "max_drawdown": 0.0, "pnl_net": 0.0, "pnl_gross": 0.0, "expectancy_R": 0.0, "expectancy_gross_R": 0.0, "cost_absolute": 0.0})
            continue
        cache = {}
        for key in chosen:
            for label, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
                rich = evaluate_rich(market, population[key], exec_tf="H1", cost_multiplier=multiplier, window=forward_window)
                ledger = _ledger_frame(rich.trades, population[key], market)
                ledger.to_parquet(ledgers_dir / f"{generator}_{key}_{label}.parquet", index=False)
                cache[(key, multiplier)] = ledger
        base_frames = [cache[(key, 1.0)] for key in chosen]
        x2_frames = [cache[(key, 2.0)] for key in chosen]
        base = portfolio_ledger(list(zip(chosen, base_frames, strict=True)), risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"])
        x2 = portfolio_ledger(list(zip(chosen, x2_frames, strict=True)), risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"])
        derived = []
        for key, base_frame, x2_frame in zip(chosen, base_frames, x2_frames, strict=True):
            ids = ["entry_timestamp", "exit_timestamp"]
            if len(base_frame) != len(x2_frame) or not base_frame[ids].reset_index(drop=True).equals(x2_frame[ids].reset_index(drop=True)):
                raise ValueError("baseline/x2 portfolio operation identity mismatch")
            gross = base_frame.copy()
            gross["result_R"] = 2 * base_frame["result_R"].to_numpy(float) - x2_frame["result_R"].to_numpy(float)
            derived.append((key, gross))
        gross = portfolio_ledger(derived, risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"])
        for cost, frame in (("baseline", base), ("costs_x2", x2)):
            portfolio_rows.append({"generation": month["generation"], "generator": generator, **_portfolio_metrics(frame, cost, gross)})
    return {"generation": month["generation"], "manifests": manifests, "census": census, "selections": selections, "portfolios": pd.DataFrame(portfolio_rows)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    _assert_sources(config)
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed": []}
    max_end = "2017-08-01" if args.smoke else config["execution"]["max_source_end_exclusive"]
    from run_p08_rolling_factory import _load_market_until
    market = _load_market_until(max_end)
    ga_cfg = GAConfig(population=config["generation"]["population"], generations=config["generation"]["generations"], max_unique_evaluations=config["generation"]["unique_evaluations"], elite=config["generation"]["ga"]["elite"], tournament=config["generation"]["ga"]["tournament"], crossover_rate=config["generation"]["ga"]["crossover_rate"], mutation_rate=config["generation"]["ga"]["mutation_rate"], immigrant_rate=config["generation"]["ga"]["immigrant_rate"], max_predicates=config["generation"]["max_predicates"])
    months = _months(config)[:1] if args.smoke else _months(config)
    all_census, all_portfolios, all_selections = [], [], []
    for month in months:
        if month["generation"] in checkpoint["completed"] and not args.smoke:
            all_census.append(pd.read_parquet(OUT / month["generation"] / "forward_census.parquet"))
            all_portfolios.append(pd.read_csv(OUT / month["generation"] / "portfolio_results.csv"))
            all_selections.extend(json.loads((OUT / month["generation"] / "selections.json").read_text()))
            continue
        result = _run_generation(market, month, config, ga_cfg, args.smoke)
        result["portfolios"].to_csv(OUT / month["generation"] / "portfolio_results.csv", index=False)
        all_census.append(result["census"])
        all_portfolios.append(result["portfolios"])
        all_selections.extend(result["selections"])
        if not args.smoke:
            checkpoint["completed"].append(month["generation"])
            checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")
    census = pd.concat(all_census, ignore_index=True)
    portfolios = pd.concat(all_portfolios, ignore_index=True)
    census.to_parquet(OUT / "forward_census_all.parquet", index=False)
    portfolios.to_csv(OUT / "portfolio_results_all.csv", index=False)
    _census_summary(census).to_csv(OUT / "census_summary.csv", index=False)
    _rolling_trajectories(portfolios).to_csv(OUT / "rolling_trajectories.csv", index=False)
    (OUT / "selections_all.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in all_selections))
    manifests = [json.loads(path.read_text()) for path in OUT.glob("G*/ga_archive.jsonl.manifest.json")]
    random_manifests = [json.loads(path.read_text()) for path in OUT.glob("G*/random_archive.jsonl.manifest.json")]
    manifest = {"policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "generations": len(months), "census_rows": len(census), "portfolio_rows": len(portfolios), "ga_evaluations": sum(item["n_evaluated"] for item in manifests), "random_evaluations": sum(item["n_evaluated"] for item in random_manifests), "budget_exact": all(item["n_evaluated"] == config["generation"]["unique_evaluations"] for item in manifests + random_manifests), "holdout_used": False, "smoke": args.smoke, "elapsed_seconds": time.perf_counter() - started}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
