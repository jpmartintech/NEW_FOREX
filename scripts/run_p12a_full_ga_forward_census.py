"""Evaluate every preserved P08 GA archive strategy on 2019 Q1 forward."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from new_forex.backtest.evaluator import evaluate_light
from new_forex.backtest.semantics import AGG
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import file_sha256
from new_forex.strategy.definition import StrategyDefinition

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12a_full_ga_forward.yaml"
ARCHIVE = ROOT / "runs/p08-rolling-2019-q1-v3/ga_archive.jsonl"
AUDIT = ROOT / "runs/p08-rolling-2019-q1-v3/selection_audit.jsonl"
OUT = ROOT / "reports/p12a_artifacts"


def flatten_metrics(agg: np.ndarray, prefix: str) -> dict[str, np.ndarray]:
    n = agg[:, AGG["n_trades"]].astype(np.int64)
    total = agg[:, AGG["sum_r"]].astype(float)
    wins = agg[:, AGG["gross_win_r"]].astype(float)
    losses = agg[:, AGG["gross_loss_r"]].astype(float)
    pf = np.divide(wins, losses, out=np.full(len(n), np.nan), where=losses != 0)
    pf[(losses == 0) & (wins > 0)] = np.inf
    pf[(losses == 0) & (wins <= 0)] = 0.0
    return {f"{prefix}_n_trades": n, f"{prefix}_total_R": total,
            f"{prefix}_expectancy_R": np.divide(total, n, out=np.zeros(len(n)), where=n != 0),
            f"{prefix}_profit_factor": pf, f"{prefix}_return": agg[:, AGG["final_equity"]] - 1.0,
            f"{prefix}_max_drawdown": agg[:, AGG["max_dd"]], f"{prefix}_sharpe": agg[:, AGG["sharpe"]],
            f"{prefix}_max_loss_streak": agg[:, AGG["max_consec_losses"]].astype(np.int64)}


def load_rows() -> list[dict]:
    rows = []
    with ARCHIVE.open() as archive, AUDIT.open() as audit:
        for archive_line, audit_line in zip(archive, audit, strict=True):
            archived = json.loads(archive_line)
            audited = json.loads(audit_line)
            if archived["canonical_hash"] != audited["strategy_hash"]:
                raise ValueError("archive and audit order/hash mismatch")
            strategy = StrategyDefinition.from_json(json.dumps(archived["strategy"]))
            if strategy.canonical_hash != archived["canonical_hash"]:
                raise ValueError(f"canonical hash mismatch: {archived['canonical_hash']}")
            acceptance = audited["acceptance"]
            failed = [name for name, check in acceptance.get("checks", {}).items() if check.get("status") == "FAIL"]
            rows.append({"strategy_hash": archived["canonical_hash"], "strategy_payload": strategy.canonical_json,
                         "archive_fitness": archived["fitness"],
                         "training": audited.get("training", {}), "development": audited.get("aggregate", {}),
                         "development_costs_x2": audited.get("costs_x2", {}), "years": audited.get("years", []),
                         "original_filter_decision": acceptance.get("decision"),
                         "original_filter_failed_checks": json.dumps(failed, sort_keys=True),
                         "strategy": strategy})
    return rows


def main() -> None:
    started = time.perf_counter()
    cfg = yaml.safe_load(CONFIG.read_bytes())
    if cfg["execution"]["ga_rerun"]:
        raise ValueError("P12A forbids GA rerun")
    if file_sha256(ARCHIVE) != cfg["archive_sha256"]:
        raise ValueError("P08 archive SHA256 mismatch")
    access = DataAccessPolicy.load()
    access.assert_range("2019-01-01", "2019-04-01")
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    OUT.mkdir(parents=True, exist_ok=True)
    parts = OUT / "chunks"
    parts.mkdir(exist_ok=True)
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed_chunks": []}
    rows = load_rows()
    if len(rows) != 100_000 or len({r["strategy_hash"] for r in rows}) != 100_000:
        raise ValueError("P08 archive is not exactly 100000 unique strategies")
    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until("2019-04-01")
    window = _window(market, "2019-01-01", "2019-04-01")
    chunk_size = int(cfg["execution"]["chunk_size"])
    for chunk_index, start in enumerate(range(0, len(rows), chunk_size)):
        chunk_name = f"part-{chunk_index:03d}.parquet"
        if chunk_name in checkpoint["completed_chunks"]:
            continue
        subset = rows[start:start + chunk_size]
        strategies = [row["strategy"] for row in subset]
        base = flatten_metrics(evaluate_light(market, strategies, exec_tf="M15", cost_multiplier=1.0, window=window), "forward")
        x2 = flatten_metrics(evaluate_light(market, strategies, exec_tf="M15", cost_multiplier=2.0, window=window), "forward_x2")
        output = pd.DataFrame({"strategy_hash": [r["strategy_hash"] for r in subset],
                               "strategy_payload": [r["strategy_payload"] for r in subset],
                               "archive_fitness": [r["archive_fitness"] for r in subset],
                               "training_expectancy_R": [r["training"].get("expectancy_R", 0.0) for r in subset],
                               "training_n_trades": [r["training"].get("n_trades", 0) for r in subset],
                               "development_expectancy_R": [r["development"].get("expectancy_R", 0.0) for r in subset],
                               "development_profit_factor": [r["development"].get("profit_factor", 0.0) for r in subset],
                               "development_n_trades": [r["development"].get("n_trades", 0) for r in subset],
                               "development_x2_expectancy_R": [r["development_costs_x2"].get("expectancy_R", 0.0) for r in subset],
                               "original_filter_decision": [r["original_filter_decision"] for r in subset],
                               "original_filter_failed_checks": [r["original_filter_failed_checks"] for r in subset],
                               **base, **x2})
        output.to_parquet(parts / chunk_name, index=False)
        checkpoint["completed_chunks"].append(chunk_name)
        checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")
    final_path = OUT / "full_forward_census.parquet"
    if not final_path.exists():
        pd.concat([pd.read_parquet(path) for path in sorted(parts.glob("part-*.parquet"))], ignore_index=True).to_parquet(final_path, index=False)
    manifest = {"policy_id": cfg["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
                "archive_sha256": file_sha256(ARCHIVE), "audit_sha256": file_sha256(AUDIT),
                "dataset_source_sha256": "29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4",
                "n_strategies": len(rows), "n_chunks": len(checkpoint["completed_chunks"]),
                "holdout_used": False, "elapsed_seconds": time.perf_counter() - started,
                "result_sha256": file_sha256(final_path)}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
