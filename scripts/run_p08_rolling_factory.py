"""Run one quarterly P08 rolling-factory generation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from new_forex.backtest.evaluator import Costs, build_market, evaluate_light, evaluate_rich
from new_forex.backtest.semantics import AGG
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.generators.genetic import GAConfig, run_genetic, write_archive
from new_forex.monte_carlo.bootstrap import MonteCarloConfig, run_monte_carlo, run_period_block_monte_carlo
from new_forex.provenance import PROJECT_ROOT, code_version, file_sha256, load_config, require_committed
from new_forex.selection.export import _ledger_frame, validate_ledger
from new_forex.strategy.definition import StrategyDefinition
from new_forex.stress.evaluator import evaluate_scenario
from new_forex.walk_forward.rolling import classify_candidate, load_policy, rank_and_select
from new_forex.walk_forward.rolling_factory import generation_windows

POLICY_PATH = PROJECT_ROOT / "configs" / "rolling_factory.yaml"
DATA_SHA256 = "29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--birth", default="2019-01-01")
    parser.add_argument("--max-evals", type=int, default=100_000)
    parser.add_argument("--population", type=int, default=1_000)
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--mc-iterations", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    policy = load_policy(POLICY_PATH)
    require_committed(POLICY_PATH)
    if args.max_evals > policy.raw["ga"]["max_unique_evaluations"]:
        raise ValueError("requested GA budget exceeds frozen P08 budget")
    if args.max_evals == policy.raw["ga"]["max_unique_evaluations"] and args.seed is None:
        seed = int(policy.raw["ga"]["base_seed"])
    else:
        seed = int(args.seed if args.seed is not None else policy.raw["ga"]["base_seed"])
    windows = generation_windows(args.birth)
    _assert_authorized_windows(windows)
    market = _load_market_until(windows["forward"][1])
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    metrics_cache: dict[str, dict] = {}
    train_window = _window(market, *windows["training"])

    def fitness(batch):
        agg = evaluate_light(market, batch, exec_tf="M15", window=train_window)
        values = []
        for strategy, row in zip(batch, agg, strict=True):
            metrics_cache.setdefault(strategy.canonical_hash, {})["training"] = _metrics(row)
            values.append(metrics_cache[strategy.canonical_hash]["training"]["expectancy_R"])
        return np.asarray(values, dtype=float)

    ga_cfg = GAConfig(population=args.population, generations=args.generations, max_unique_evaluations=args.max_evals,
                      elite=min(20, max(1, args.population - 1)), tournament=min(4, args.population), crossover_rate=0.7,
                      mutation_rate=0.4, immigrant_rate=0.1, max_predicates=4)
    ga = run_genetic("EURUSD", fitness, ga_cfg, seed=seed)
    archive_path = output / "ga_archive.jsonl"
    archive_manifest = write_archive(ga, archive_path, run_id=output.name, seed=seed, config=ga_cfg)
    strategies = {key: value[0] for key, value in ga.archive.items()}
    hashes = sorted(strategies)
    dev_window = _window(market, *windows["development_wf"])
    dev_agg = evaluate_light(market, [strategies[key] for key in hashes], exec_tf="M15", window=dev_window)
    x2_agg = evaluate_light(market, [strategies[key] for key in hashes], exec_tf="M15", cost_multiplier=2.0, window=dev_window)
    prequalified: list[str] = []
    for key, base, x2 in zip(hashes, dev_agg, x2_agg, strict=True):
        metrics_cache[key]["development"] = _metrics(base)
        metrics_cache[key]["development_costs_x2"] = _metrics(x2)
        base_m = metrics_cache[key]["development"]
        x2_m = metrics_cache[key]["development_costs_x2"]
        if (base_m["n_trades"] >= policy.raw["selection"]["min_dev_wf_trades"]
                and base_m["expectancy_R"] > 0 and base_m["profit_factor"] > policy.raw["selection"]["min_profit_factor"]
                and np.isfinite(base_m["profit_factor"]) and x2_m["expectancy_R"] > 0):
            prequalified.append(key)
    year_metrics = _year_metrics(market, strategies, prequalified)
    rows = []
    for key in hashes:
        years = year_metrics.get(key, [{"n_trades": 0, "expectancy_R": 0.0}] * 2)
        rows.append({"strategy_hash": key, "strategy": strategies[key].payload(),
                     "training": metrics_cache[key]["training"], "aggregate": metrics_cache[key]["development"],
                     "costs_x2": metrics_cache[key]["development_costs_x2"], "years": years,
                     "acceptance": classify_candidate(policy, strategy_hash=key,
                                                        aggregate=metrics_cache[key]["development"], years=years,
                                                        costs_x2=metrics_cache[key]["development_costs_x2"])})
    selected, audit = rank_and_select(policy, rows)
    _write_jsonl(output / "selection_audit.jsonl", rows)
    finalists = [next(row for row in rows if row["strategy_hash"] == item["strategy_hash"]) for item in selected]
    (output / "finalists.json").write_text(json.dumps(finalists, sort_keys=True, indent=2, default=str) + "\n")

    dev_ledgers, forward_ledgers = _export_ledgers(output, market, finalists, windows)
    mc = _run_mc(output, dev_ledgers, args.mc_iterations, seed)
    stress = _run_stress(market, finalists, dev_window)
    forward = _run_forward(market, finalists, _window(market, *windows["forward"]))
    report = {"contract_version": "p08-rolling-factory-v1", "run_id": output.name, "code_version": code_version(),
              "policy_id": policy.raw["policy_id"], "policy_sha256": policy.sha256, "birth_date": args.birth,
              "windows": windows, "partition": "pre-holdout-development-and-forward", "dataset_sha256": DATA_SHA256,
              "split_sha256": file_sha256(PROJECT_ROOT / "configs" / "splits.yaml"), "seed": seed,
              "ga": archive_manifest, "selection": audit, "finalists": [x["strategy_hash"] for x in finalists],
              "active_risk": len(finalists) * policy.raw["portfolio"]["risk_per_trade"],
              "max_aggregate_risk": policy.raw["portfolio"]["max_aggregate_risk"], "ledgers": {"development": dev_ledgers, "forward": forward_ledgers},
              "monte_carlo": mc, "stress": stress, "forward": forward,
              "holdout_used": False, "rows_at_or_after_forward_end_loaded": 0,
              "config_hashes": {"rolling_factory": policy.sha256, "data": file_sha256(PROJECT_ROOT / "configs" / "data.yaml"),
                                "ga": file_sha256(PROJECT_ROOT / "configs" / "ga.yaml"), "splits": file_sha256(PROJECT_ROOT / "configs" / "splits.yaml")}}
    (output / "generation.json").write_text(json.dumps(report, sort_keys=True, indent=2, default=str) + "\n")
    print(json.dumps({"run_id": output.name, "birth": args.birth, "evaluated": len(ga.archive),
                      "eligible": audit["eligible"], "selected": audit["selected"], "forward_rows": len(forward)}, indent=2))
    return 0


def _assert_authorized_windows(windows: dict[str, tuple[str, str]]) -> None:
    policy = DataAccessPolicy.load()
    if pd.Timestamp(windows["forward"][1]) > policy.window(Partition.FINAL_HOLDOUT).start:
        raise ValueError("rolling generation reaches sealed holdout")
    for start, end in windows.values():
        if pd.Timestamp(end) <= pd.Timestamp(start):
            raise ValueError("invalid generation window")


def _load_market_until(end: str):
    cfg = load_config("data")
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / "EURUSD.parquet"
    frame = pd.read_parquet(cache, filters=[("ts_local", "<", pd.Timestamp(end).to_pydatetime())])
    metadata = pq.read_schema(cache).metadata or {}
    frame.attrs.update({key.decode(): value.decode() for key, value in metadata.items()})
    if frame.attrs.get("source_sha256") != DATA_SHA256:
        raise ValueError("canonical cache source hash mismatch")
    if pd.Timestamp(frame["ts_local"].max()) >= pd.Timestamp(end):
        raise ValueError("market contains rows after authorized generation end")
    return build_market("EURUSD", frame, Costs.for_pair("EURUSD"), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


def _metrics(agg: np.ndarray) -> dict:
    n = int(agg[AGG["n_trades"]])
    total = float(agg[AGG["sum_r"]])
    wins, losses = float(agg[AGG["gross_win_r"]]), float(agg[AGG["gross_loss_r"]])
    return {"n_trades": n, "total_R": total, "expectancy_R": total / n if n else 0.0,
            "profit_factor": wins / losses if losses else (math.inf if wins > 0 else 0.0),
            "max_drawdown": float(agg[AGG["max_dd"]]), "return": float(agg[AGG["final_equity"]] - 1.0),
            "sharpe": float(agg[AGG["sharpe"]]), "max_loss_streak": int(agg[AGG["max_consec_losses"]])}


def _year_metrics(market, strategies: dict, keys: list[str]) -> dict[str, list[dict]]:
    result = {key: [] for key in keys}
    for start, end in (("2017-01-01", "2018-01-01"), ("2018-01-01", "2019-01-01")):
        agg = evaluate_light(market, [strategies[key] for key in keys], exec_tf="M15", window=_window(market, start, end))
        for key, row in zip(keys, agg, strict=True):
            result[key].append(_metrics(row))
    return result


def _export_ledgers(output, market, finalists, windows):
    dev_paths, forward_paths = [], []
    for row in finalists:
        strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
        for label, bounds, paths in (("development", windows["development_wf"], dev_paths), ("forward", windows["forward"], forward_paths)):
            rich = evaluate_rich(market, strategy, exec_tf="M15", window=_window(market, *bounds))
            ledger = _ledger_frame(rich.trades, strategy, market)
            validate_ledger(ledger, strategy, rich.metrics)
            path = output / "ledgers" / f"{strategy.canonical_hash}.{label}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            ledger.to_parquet(path, index=False)
            paths.append({"strategy_hash": strategy.canonical_hash, "path": str(path.relative_to(output)), "sha256": file_sha256(path), "n_trades": len(ledger)})
    return dev_paths, forward_paths


def _run_mc(output, ledgers, iterations, seed):
    if not ledgers:
        return {"status": "NO_ACTIVE_STRATEGIES"}
    cfg = MonteCarloConfig(iterations=max(5_000, iterations), seed=seed, block_length=20, method="moving", ruin_floor=0.5)
    results = {}
    for item in ledgers:
        r = pd.read_parquet(output / item["path"])["result_R"].to_numpy(float) * 0.005
        if len(r) < 2:
            results[item["strategy_hash"]] = {"status": "INSUFFICIENT_TRADES"}
            continue
        periods = (pd.to_datetime(pd.read_parquet(output / item["path"])["entry_timestamp"], utc=True)
                   .dt.tz_localize(None).dt.to_period("M").astype(str).to_numpy())
        results[item["strategy_hash"]] = {"moving": run_monte_carlo(r, cfg).quantiles,
                                           "stationary": run_monte_carlo(r, MonteCarloConfig(**{**cfg.__dict__, "method": "stationary", "seed": seed + 1})).quantiles,
                                           "period_block": run_period_block_monte_carlo(r, periods, cfg).quantiles}
    return {"iterations": cfg.iterations, "results": results}


def _run_stress(market, finalists, window):
    rows = []
    for row in finalists:
        strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
        for name, multiplier in (("baseline_x1", 1.0), ("costs_x2", 2.0)):
            _, metrics = evaluate_scenario(market, strategy, window=window, cost_multiplier=multiplier)
            rows.append({"strategy_hash": strategy.canonical_hash, "scenario": name, "metrics": _summary_metrics(metrics)})
    return rows if rows else {"status": "NO_ACTIVE_STRATEGIES"}


def _run_forward(market, finalists, window):
    rows = []
    for row in finalists:
        strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
        rich = evaluate_rich(market, strategy, exec_tf="M15", window=window)
        rows.append({"strategy_hash": strategy.canonical_hash, "metrics": _summary_metrics(rich.metrics)})
    return rows


def _summary_metrics(metrics: dict) -> dict:
    return {key: float(metrics[key]) if key not in {"n_trades", "max_consec_losses"} else int(metrics[key])
            for key in ("n_trades", "mean_r", "profit_factor", "return", "max_dd", "sharpe", "max_consec_losses")}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
