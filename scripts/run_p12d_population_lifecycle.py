"""Evaluate the complete P08 Q1 population over nine causal quarters."""
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
CONFIG = ROOT / "configs/p12d_population_lifecycle.yaml"
OUT = ROOT / "reports/p12d_artifacts"


def _metrics(agg: np.ndarray, prefix: str) -> dict[str, np.ndarray]:
    n = agg[:, AGG["n_trades"]].astype(np.int64)
    total = agg[:, AGG["sum_r"]].astype(float)
    wins = agg[:, AGG["gross_win_r"]].astype(float)
    losses = agg[:, AGG["gross_loss_r"]].astype(float)
    pf = np.divide(wins, losses, out=np.full(len(n), np.nan), where=losses != 0)
    pf[(losses == 0) & (wins > 0)] = np.inf
    pf[(losses == 0) & (wins <= 0)] = 0.0
    ret = agg[:, AGG["final_equity"]].astype(float) - 1.0
    dd = agg[:, AGG["max_dd"]].astype(float)
    efficiency = np.divide(ret, dd, out=np.zeros(len(n)), where=dd != 0)
    return {
        f"{prefix}_n_trades": n,
        f"{prefix}_total_R": total,
        f"{prefix}_expectancy_R": np.divide(total, n, out=np.zeros(len(n)), where=n != 0),
        f"{prefix}_profit_factor": pf,
        f"{prefix}_return": ret,
        f"{prefix}_max_drawdown": dd,
        f"{prefix}_efficiency_return_dd": efficiency,
    }


def load_population(archive: Path, audit: Path) -> list[dict]:
    rows: list[dict] = []
    with archive.open() as archive_file, audit.open() as audit_file:
        for archive_line, audit_line in zip(archive_file, audit_file, strict=True):
            archived = json.loads(archive_line)
            audited = json.loads(audit_line)
            if archived["canonical_hash"] != audited["strategy_hash"]:
                raise ValueError("archive and audit order/hash mismatch")
            strategy = StrategyDefinition.from_json(json.dumps(archived["strategy"]))
            if strategy.canonical_hash != archived["canonical_hash"]:
                raise ValueError(f"canonical hash mismatch: {archived['canonical_hash']}")
            training = audited.get("training", {})
            rows.append({
                "strategy_hash": archived["canonical_hash"],
                "archive_fitness": float(archived["fitness"]),
                "training_n_trades": int(training.get("n_trades", 0)),
                "training_expectancy_R": float(training.get("expectancy_R", 0.0)),
                "training_max_drawdown": float(training.get("max_drawdown", 0.0)),
                "original_filter_decision": audited.get("acceptance", {}).get("decision"),
                "strategy": strategy,
            })
    if len(rows) != 100_000 or len({row["strategy_hash"] for row in rows}) != 100_000:
        raise ValueError("P08 archive is not exactly 100000 unique strategies")
    return rows


def _quarter_label(start: str) -> str:
    stamp = pd.Timestamp(start)
    return f"{stamp.year}Q{((stamp.month - 1) // 3) + 1}"


def _assert_windows(config: dict) -> None:
    policy = DataAccessPolicy.load()
    previous_end = None
    for start, end in config["quarters"]:
        start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
        if previous_end is not None and start_ts != previous_end:
            raise ValueError("quarters are not contiguous")
        if end_ts <= start_ts or end_ts > pd.Timestamp(config["execution"]["source_end_exclusive"]):
            raise ValueError("quarter is outside the authorized source range")
        partition = policy.partition_for(start_ts)
        if partition is Partition.FINAL_HOLDOUT:
            raise ValueError("holdout quarter requested")
        policy.assert_readable(partition)
        previous_end = end_ts


def main() -> None:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    if config["execution"]["ga_rerun"]:
        raise ValueError("P12D forbids GA rerun")
    _assert_windows(config)
    archive = ROOT / config["archive"]
    audit = ROOT / config["selection_audit"]
    p12a_result = ROOT / config["p12a_result"]
    if file_sha256(archive) != config["archive_sha256"]:
        raise ValueError("P08 archive SHA256 mismatch")
    access = DataAccessPolicy.load()
    access.assert_readable(Partition.DEVELOPMENT_WF)
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    rows = load_population(archive, audit)
    OUT.mkdir(parents=True, exist_ok=True)
    parts = OUT / "chunks"
    parts.mkdir(exist_ok=True)
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed": []}

    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until(config["execution"]["source_end_exclusive"])
    strategies = [row["strategy"] for row in rows]
    historical = pd.DataFrame([{key: value for key, value in row.items() if key != "strategy"} for row in rows])
    chunk_size = int(config["evaluation"]["chunk_size"])
    quarter_specs = [(str(start), str(end), _quarter_label(str(start))) for start, end in config["quarters"]]
    for start, end, label in quarter_specs:
        window = _window(market, start, end)
        for chunk_index, first in enumerate(range(0, len(rows), chunk_size)):
            chunk_name = f"{label}-part-{chunk_index:03d}.parquet"
            if chunk_name in checkpoint["completed"]:
                continue
            last = min(first + chunk_size, len(rows))
            base = _metrics(evaluate_light(market, strategies[first:last], exec_tf="M15", cost_multiplier=1.0, window=window), "forward")
            x2 = _metrics(evaluate_light(market, strategies[first:last], exec_tf="M15", cost_multiplier=2.0, window=window), "forward_x2")
            output = historical.iloc[first:last].reset_index(drop=True).copy()
            output["quarter"] = label
            output["quarter_start"] = start
            output["quarter_end_exclusive"] = end
            for key, values in {**base, **x2}.items():
                output[key] = values
            output["active"] = output["forward_n_trades"] > 0
            output["positive_expectancy"] = output["active"] & (output["forward_expectancy_R"] > 0)
            output["positive_return"] = output["active"] & (output["forward_return"] > 0)
            output["positive_both"] = output["positive_expectancy"] & output["positive_return"]
            output.to_parquet(parts / chunk_name, index=False)
            checkpoint["completed"].append(chunk_name)
            checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")

    final_path = OUT / "population_lifecycle.parquet"
    expected_parts = len(quarter_specs) * ((len(rows) + chunk_size - 1) // chunk_size)
    if len(checkpoint["completed"]) != expected_parts:
        raise RuntimeError("incomplete P12D checkpoint")
    if not final_path.exists():
        pd.concat([pd.read_parquet(path) for path in sorted(parts.glob("*.parquet"))], ignore_index=True).to_parquet(final_path, index=False)
    result = pd.read_parquet(final_path)
    if len(result) != 900_000 or result.duplicated(["strategy_hash", "quarter"]).any():
        raise ValueError("P12D longitudinal integrity failure")

    p12a = pd.read_parquet(p12a_result).set_index("strategy_hash").sort_index()
    q1 = result[result["quarter"] == "2019Q1"].set_index("strategy_hash").sort_index()
    for field in ("forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown", "forward_x2_expectancy_R", "forward_x2_return"):
        if not np.allclose(q1[field].to_numpy(), p12a[field].to_numpy(), equal_nan=True):
            raise ValueError(f"P12A equivalence failure: {field}")

    signatures = result.assign(behavior_signature=result[["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"]].astype(str).agg("|".join, axis=1))
    dep = signatures.groupby("quarter", as_index=False).agg(rows=("strategy_hash", "size"), unique_strategies=("strategy_hash", "nunique"), unique_signatures=("behavior_signature", "nunique"))
    dep["duplicate_rows"] = dep["rows"] - dep["unique_signatures"]
    dep.to_csv(OUT / "dependence_by_quarter.csv", index=False)
    (OUT / "equivalence_p12a.json").write_text(json.dumps({"matched": True, "fields": ["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown", "forward_x2_expectancy_R", "forward_x2_return"], "p12a_sha256": file_sha256(p12a_result)}, indent=2) + "\n")
    manifest = {
        "policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "archive_sha256": file_sha256(archive), "audit_sha256": file_sha256(audit),
        "result_sha256": file_sha256(final_path), "n_strategies": 100_000, "n_quarters": 9,
        "n_observations": len(result), "holdout_used": False, "p12a_equivalence": True,
        "elapsed_seconds": time.perf_counter() - started,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
