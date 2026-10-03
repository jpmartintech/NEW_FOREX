"""Run frozen P12C full-archive temporal validation for P09 generations."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from new_forex.backtest.evaluator import evaluate_light, evaluate_rich
from new_forex.backtest.semantics import AGG
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame, validate_ledger
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.random_control import seed_for
from new_forex.walk_forward.rolling_factory import generation_windows
from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12c_temporal_validation.yaml"
OUT = ROOT / "reports/p12c_artifacts"
RUNS = ROOT / "runs/p09-rolling-historical-v1"


def metric_arrays(agg: np.ndarray, prefix: str) -> dict[str, np.ndarray]:
    n = agg[:, AGG["n_trades"]].astype(np.int64)
    total = agg[:, AGG["sum_r"]].astype(float)
    wins, losses = agg[:, AGG["gross_win_r"]], agg[:, AGG["gross_loss_r"]]
    pf = np.divide(wins, losses, out=np.full(len(n), np.nan), where=losses != 0)
    pf[(losses == 0) & (wins > 0)] = np.inf
    pf[(losses == 0) & (wins <= 0)] = 0.0
    return {f"{prefix}_n_trades": n, f"{prefix}_expectancy_R": np.divide(total, n, out=np.zeros(len(n)), where=n != 0),
            f"{prefix}_profit_factor": pf, f"{prefix}_return": agg[:, AGG["final_equity"]] - 1,
            f"{prefix}_max_drawdown": agg[:, AGG["max_dd"]], f"{prefix}_max_loss_streak": agg[:, AGG["max_consec_losses"]].astype(int)}


def load_generation(label: str) -> tuple[list[dict], dict[str, StrategyDefinition], set[str]]:
    path = RUNS / label
    rows, strategies = [], {}
    with (path / "ga_archive.jsonl").open() as archive, (path / "selection_audit.jsonl").open() as audit:
        for archive_line, audit_line in zip(archive, audit, strict=True):
            a, x = json.loads(archive_line), json.loads(audit_line)
            if a["canonical_hash"] != x["strategy_hash"]:
                raise ValueError(f"archive/audit mismatch in {label}")
            strategy = StrategyDefinition.from_json(json.dumps(a["strategy"]))
            if strategy.canonical_hash != a["canonical_hash"]:
                raise ValueError(f"canonical hash mismatch in {label}")
            strategies[a["canonical_hash"]] = strategy
            checks = x["acceptance"]["checks"]
            prequalified = all(checks.get(k, {}).get("status") == "PASS" for k in
                               ("min_dev_wf_trades", "min_aggregate_expectancy_R", "min_profit_factor",
                                "require_finite_profit_factor", "costs_x2_expectancy_R"))
            train, dev, x2 = x.get("training", {}), x.get("aggregate", {}), x.get("costs_x2", {})
            rows.append({"strategy_hash": a["canonical_hash"], "archive_fitness": a["fitness"],
                         "original_filter_decision": x["acceptance"]["decision"], "direction": strategy.direction,
                         "n_predicates": len(strategy.predicates), "development_n_trades": dev.get("n_trades", np.nan),
                         "development_expectancy_R": dev.get("expectancy_R", np.nan), "development_profit_factor": dev.get("profit_factor", np.nan),
                         "development_x2_expectancy_R": x2.get("expectancy_R", np.nan),
                         "training_expectancy_R": train.get("expectancy_R", np.nan), "training_n_trades": train.get("n_trades", np.nan),
                         "training_max_drawdown": train.get("max_drawdown", np.nan), "historical_year_metrics_available": prequalified,
                         "strategy": strategy})
    selected = {x["strategy_hash"] for x in json.loads((path / "finalists.json").read_text())}
    if len(rows) != 100_000 or len(strategies) != 100_000 or len(selected) != 5:
        raise ValueError(f"incomplete full universe in {label}")
    return rows, strategies, selected


def evaluate_portfolio(market, strategies: dict[str, StrategyDefinition], hashes: list[str], window: tuple[int, int], multiplier: float) -> dict:
    ledgers = []
    for key in hashes:
        rich = evaluate_rich(market, strategies[key], exec_tf="M15", cost_multiplier=multiplier, window=window)
        ledger = _ledger_frame(rich.trades, strategies[key], market)
        validate_ledger(ledger, strategies[key], rich.metrics)
        ledgers.append((key, ledger))
    return portfolio_metrics(portfolio_ledger(ledgers))


def main() -> None:
    started = time.perf_counter()
    cfg = __import__("yaml").safe_load(CONFIG.read_bytes())
    access = DataAccessPolicy.load()
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed": []}
    labels = cfg["generations"]
    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until("2023-01-01")
    for generation_index, label in enumerate(labels):
        gen_dir = OUT / label
        gen_dir.mkdir(exist_ok=True)
        if label not in checkpoint["completed"]:
            rows, strategies, selected = load_generation(label)
            windows = generation_windows(pd.Period(label, freq="Q").start_time.strftime("%Y-%m-%d"))
            window = _window(market, *windows["forward"])
            for chunk_index, start in enumerate(range(0, len(rows), cfg["evaluation"]["chunk_size"])):
                part = gen_dir / f"part-{chunk_index:03d}.parquet"
                if part.exists():
                    continue
                subset = rows[start:start + cfg["evaluation"]["chunk_size"]]
                strategies_chunk = [r["strategy"] for r in subset]
                base = metric_arrays(evaluate_light(market, strategies_chunk, exec_tf="M15", window=window), "forward")
                x2 = metric_arrays(evaluate_light(market, strategies_chunk, exec_tf="M15", cost_multiplier=2.0, window=window), "forward_x2")
                out = pd.DataFrame({"strategy_hash": [r["strategy_hash"] for r in subset], "archive_fitness": [r["archive_fitness"] for r in subset],
                    "original_filter_decision": [r["original_filter_decision"] for r in subset], "direction": [r["direction"] for r in subset],
                    "n_predicates": [r["n_predicates"] for r in subset], "development_n_trades": [r["development_n_trades"] for r in subset],
                    "development_expectancy_R": [r["development_expectancy_R"] for r in subset], "development_profit_factor": [r["development_profit_factor"] for r in subset],
                    "development_x2_expectancy_R": [r["development_x2_expectancy_R"] for r in subset], "training_expectancy_R": [r["training_expectancy_R"] for r in subset],
                    "training_n_trades": [r["training_n_trades"] for r in subset], "training_max_drawdown": [r["training_max_drawdown"] for r in subset],
                    "historical_year_metrics_available": [r["historical_year_metrics_available"] for r in subset],
                    "selected_original": [r["strategy_hash"] in selected for r in subset], **base, **x2})
                out.to_parquet(part, index=False)
            selected_metrics = pd.concat(pd.read_parquet(p) for p in sorted(gen_dir.glob("part-*.parquet")))
            for scenario, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
                pm = evaluate_portfolio(market, strategies, sorted(selected), window, multiplier)
                (gen_dir / f"original_portfolio_{scenario}.json").write_text(json.dumps(pm, sort_keys=True, indent=2) + "\n")
            eligible = selected_metrics[selected_metrics.original_filter_decision == "PASS"].strategy_hash.tolist()
            generation_random_rows = []
            for replicate in range(cfg["control"]["replicates_per_generation"]):
                seed = seed_for(cfg["control"]["seed_base"], generation_index, replicate)
                sample = list(np.random.default_rng(seed).choice(sorted(strategies), 5, replace=False))
                row = {"generation": label, "replicate": replicate, "seed": seed, "selected": sample,
                       "baseline": evaluate_portfolio(market, strategies, sample, window, 1.0),
                       "costs_x2": evaluate_portfolio(market, strategies, sample, window, 2.0),
                       "eligible_universe_size": len(eligible)}
                generation_random_rows.append(row)
            with (gen_dir / "random_control.jsonl").open("w") as handle:
                for row in generation_random_rows:
                    handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            checkpoint["completed"].append(label)
            checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")
    # Consolidate per-generation random results on every resume.
    random_path = OUT / "random_control_results.jsonl"
    with random_path.open("w") as handle:
        for label in labels:
            path = OUT / label / "random_control.jsonl"
            if not path.exists():
                raise RuntimeError(f"missing random control checkpoint for {label}")
            handle.write(path.read_text())
    manifest = {"policy_id": cfg["policy_id"], "config_sha256": file_sha256(CONFIG), "generations": len(labels),
                "holdout_used": False, "elapsed_seconds": time.perf_counter() - started,
                "completed": checkpoint["completed"]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
