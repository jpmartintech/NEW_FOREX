"""Evaluate the frozen P03.1 finalists on development_wf only."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

from new_forex.backtest.evaluator import Costs, build_market, evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import PROJECT_ROOT, code_version, file_sha256
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.acceptance import classify, load_policy

EXPECTED_DATA_SHA256 = "29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4"
WF_WINDOWS = (("WF1", "2015-01-01", "2016-01-01"), ("WF2", "2016-01-01", "2017-01-01"),
              ("WF3", "2017-01-01", "2018-01-01"), ("WF4", "2018-01-01", "2019-01-01"))
MANIFEST = PROJECT_ROOT / "runs" / "p02-p04-eurusd-real-100k-clean-final" / "p03.1_export" / "finalist_manifest.json"
P04_REPORT = PROJECT_ROOT / "runs" / "p02-p04-eurusd-real-100k-clean-final" / "p04_report.json"
POLICY = PROJECT_ROOT / "configs" / "wf_acceptance.yaml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = load_policy(POLICY)
    access = DataAccessPolicy.load()
    access.assert_range("2015-01-01", "2019-01-01")
    for _, start, end in WF_WINDOWS:
        if access.assert_range(start, end) is not Partition.DEVELOPMENT_WF:
            raise ValueError("P06 window is outside development_wf")

    manifest = json.loads(args.manifest.read_text())
    if manifest.get("contract_version") != "p03.1-v1" or len(manifest.get("finalists", [])) != 25:
        raise ValueError("P06 requires the frozen 25-finalist P03.1 manifest")
    if manifest["config"]["partition"] != "dev_train" or pd.Timestamp(manifest["config"]["end"]) != pd.Timestamp("2015-01-01"):
        raise ValueError("P06 source manifest is not the frozen dev_train export")
    p04 = json.loads(P04_REPORT.read_text())
    dd_limits = _p04_dd_limits(p04)
    market = _load_market_before_2019()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    for finalist in manifest["finalists"]:
        strategy_hash = finalist["strategy_hash"]
        strategy = StrategyDefinition.from_json(json.dumps(finalist["strategy"]))
        if strategy.canonical_hash != strategy_hash:
            raise ValueError(f"frozen strategy identity mismatch: {strategy_hash}")
        ledger = args.manifest.parent / finalist["ledger"]
        if file_sha256(ledger) != finalist["ledger_sha256"]:
            raise ValueError(f"frozen ledger checksum mismatch: {strategy_hash}")
        annual: list[dict] = []
        annual_x2: list[dict] = []
        for name, start, end in WF_WINDOWS:
            window = _window(market, start, end)
            base = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=1.0, window=window)
            x2 = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=2.0, window=window)
            annual.append(_metric_row(name, start, end, base.trades, base.metrics))
            annual_x2.append(_metric_row(name, start, end, x2.trades, x2.metrics))
        aggregate = _aggregate(annual, "baseline")
        costs_x2 = _aggregate(annual_x2, "costs_x2")
        decision = classify(policy, strategy_hash=strategy_hash, aggregate=aggregate, yearly=annual,
                            costs_x2=costs_x2, identity_ok=True, max_drawdown_limit=dd_limits.get(strategy_hash))
        all_rows.append({"strategy_hash": strategy_hash, "annual": _public_rows(annual),
                         "aggregate": _public_aggregate(aggregate), "costs_x2": _public_aggregate(costs_x2),
                         "acceptance": decision})

    report = {
        "contract_version": "p06-frozen-wf-v1", "run_id": output.name, "code_version": code_version(),
        "source_manifest": str(args.manifest), "manifest_sha256": file_sha256(args.manifest),
        "policy": {"path": str(POLICY), "sha256": policy.sha256, "policy_id": policy.policy_id},
        "p04_report_sha256": file_sha256(P04_REPORT), "dataset_sha256": EXPECTED_DATA_SHA256,
        "partition": "development_wf", "period": {"start": "2015-01-01", "end": "2019-01-01"},
        "windows": [{"name": n, "start": s, "end": e} for n, s, e in WF_WINDOWS],
        "risk_policy": {"version": "p06-fixed-fractional-r-v1", "risk_per_trade": market.risk_per_trade},
        "finalist_count": len(all_rows), "results": all_rows,
        "survivors": sum(row["acceptance"]["decision"] == "PASS" for row in all_rows),
        "blocked_certifications": sum(row["acceptance"]["decision"] == "BLOCKED" for row in all_rows),
        "holdout_used": False, "procedure_validation_used": False,
        "rows_at_or_after_2019_loaded": 0,
    }
    (output / "p06_report.json").write_text(json.dumps(report, sort_keys=True, indent=2, default=_json_default) + "\n")
    print(json.dumps({"run_id": report["run_id"], "finalists": 25, "survivors": report["survivors"],
                      "blocked_certifications": report["blocked_certifications"]}, indent=2))
    return 0


def _load_market_before_2019():
    cfg = yaml.safe_load((PROJECT_ROOT / "configs" / "data.yaml").read_text())
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / "EURUSD.parquet"
    if not cache.exists():
        raise FileNotFoundError(cache)
    frame = pd.read_parquet(cache, filters=[("ts_local", "<", datetime(2019, 1, 1))])
    metadata = pq.read_schema(cache).metadata or {}
    frame.attrs.update({key.decode(): value.decode() for key, value in metadata.items()})
    if frame.attrs.get("source_sha256") != EXPECTED_DATA_SHA256:
        raise ValueError("canonical cache source hash does not match frozen P04 input")
    if pd.Timestamp(frame["ts_local"].max()) >= pd.Timestamp("2019-01-01"):
        raise ValueError("P06 market contains rows at or after 2019")
    return build_market("EURUSD", frame, Costs.for_pair("EURUSD"), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


def _metric_row(name: str, start: str, end: str, trades: pd.DataFrame, metrics: dict) -> dict:
    return {"window": name, "start": start, "end": end, "n_trades": int(metrics["n_trades"]),
            "profit_factor": float(metrics["profit_factor"]), "expectancy_R": float(metrics["mean_r"]),
            "return": float(metrics["return"]), "max_drawdown": float(metrics["max_dd"]),
            "max_drawdown_mtm": float(metrics["max_dd_mtm"]), "sharpe": float(metrics["sharpe"]),
            "total_R": float(metrics["total_r"]), "trades": trades}


def _aggregate(rows: list[dict], label: str) -> dict:
    frames = [row["trades"] for row in rows if not row["trades"].empty]
    trade = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["r", "exit_bar_time"])
    r = trade["r"].to_numpy(float) if not trade.empty else np.array([], dtype=float)
    equity = np.cumprod(1.0 + 0.005 * r) if len(r) else np.array([1.0])
    peaks = np.maximum.accumulate(equity)
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    daily = _daily_returns(trade)
    sharpe = float(np.sqrt(260.0) * daily.mean() / daily.std(ddof=0)) if len(daily) and daily.std(ddof=0) > 0 else 0.0
    return {"label": label, "n_trades": int(len(r)), "profit_factor": float(pos / neg) if neg > 0 else (float("inf") if len(r) else 0.0),
            "expectancy_R": float(r.mean()) if len(r) else 0.0, "total_R": float(r.sum()),
            "return": float(equity[-1] - 1.0), "max_drawdown": float(np.max(1.0 - equity / peaks)) if len(r) else 0.0,
            "sharpe": sharpe, "trades": trade.drop(columns=["r"], errors="ignore").to_dict(orient="records")}


def _public_rows(rows: list[dict]) -> list[dict]:
    return [{key: value for key, value in row.items() if key != "trades"} for row in rows]


def _public_aggregate(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "trades"}


def _daily_returns(trades: pd.DataFrame) -> np.ndarray:
    if trades.empty:
        return np.array([], dtype=float)
    frame = trades.assign(day=pd.to_datetime(trades["exit_bar_time"]).dt.date)
    return frame.groupby("day")["r"].apply(lambda x: float(np.prod(1.0 + 0.005 * x) - 1.0)).to_numpy()


def _p04_dd_limits(report: dict) -> dict[str, float]:
    risk = report.get("risk_policy", {})
    if risk.get("version") != "p04-fixed-fractional-r-v1" or float(risk.get("risk_per_trade")) != 0.005:
        raise ValueError("P04 drawdown policy is not comparable to P06")
    methods = ("moving", "stationary", "period_block")
    limits = {}
    for strategy_hash, result in report["monte_carlo"].items():
        values = [float(result[method]["quantiles"]["dd_p95"]) for method in methods]
        if not all(np.isfinite(values)):
            raise ValueError(f"non-comparable P04 drawdown limit for {strategy_hash}")
        limits[strategy_hash] = max(values)
    return limits


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    raise SystemExit(main())
