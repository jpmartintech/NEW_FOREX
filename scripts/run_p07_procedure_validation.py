"""Validate the single frozen P06 survivor on procedure_validation only."""
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
STRATEGY_HASH = "237d10ee505b9bf528a2036d30babb26db137e9de3852a8bb116f73799798ebd"
MANIFEST = PROJECT_ROOT / "runs" / "p02-p04-eurusd-real-100k-clean-final" / "p03.1_export" / "finalist_manifest.json"
P06_REPORT = PROJECT_ROOT / "runs" / "p06-eurusd-frozen-wf-v1" / "p06_report.json"
P04_REPORT = PROJECT_ROOT / "runs" / "p02-p04-eurusd-real-100k-clean-final" / "p04_report.json"
POLICY = PROJECT_ROOT / "configs" / "procedure_validation.yaml"
WINDOWS = (("2019", "2019-01-01", "2020-01-01"), ("2020", "2020-01-01", "2021-01-01"),
           ("2021", "2021-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = load_policy(POLICY)
    access = DataAccessPolicy.load()
    if access.assert_range("2019-01-01", "2023-01-01") is not Partition.PROCEDURE_VALIDATION:
        raise ValueError("P07 range is not procedure_validation")
    for _, start, end in WINDOWS:
        if access.assert_range(start, end) is not Partition.PROCEDURE_VALIDATION:
            raise ValueError("P07 annual window is outside procedure_validation")

    manifest = json.loads(args.manifest.read_text())
    finalist = _frozen_finalist(manifest)
    strategy = StrategyDefinition.from_json(json.dumps(finalist["strategy"]))
    if strategy.canonical_hash != STRATEGY_HASH or strategy.canonical_hash != finalist["strategy_hash"]:
        raise ValueError("P07 strategy identity does not match the frozen P06 survivor")
    ledger = args.manifest.parent / finalist["ledger"]
    if file_sha256(ledger) != finalist["ledger_sha256"]:
        raise ValueError("P03.1 frozen ledger checksum mismatch")
    p04 = json.loads(P04_REPORT.read_text())
    dd_limit = _p04_dd_limit(p04, STRATEGY_HASH)
    market = _load_market_before_holdout()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    annual: list[dict] = []
    annual_x2: list[dict] = []
    for name, start, end in WINDOWS:
        window = _window(market, start, end)
        base = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=1.0, window=window)
        x2 = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=2.0, window=window)
        annual.append(_metric_row(name, base.trades, base.metrics))
        annual_x2.append(_metric_row(name, x2.trades, x2.metrics))
    aggregate = _aggregate(annual, "baseline")
    costs_x2 = _aggregate(annual_x2, "costs_x2")
    decision = classify(policy, strategy_hash=STRATEGY_HASH, aggregate=aggregate, yearly=annual,
                        costs_x2=costs_x2, identity_ok=True, max_drawdown_limit=dd_limit)
    comparison = _comparison()
    report = {
        "contract_version": "p07-procedure-validation-v1", "run_id": output.name, "code_version": code_version(),
        "source_manifest": str(args.manifest), "manifest_sha256": file_sha256(args.manifest),
        "strategy_hash": STRATEGY_HASH, "policy": {"path": str(POLICY), "policy_id": policy.policy_id, "sha256": policy.sha256},
        "p04_report_sha256": file_sha256(P04_REPORT), "p06_report_sha256": file_sha256(P06_REPORT),
        "dataset_sha256": EXPECTED_DATA_SHA256, "partition": "procedure_validation",
        "period": {"start": "2019-01-01", "end": "2023-01-01"},
        "windows": [{"name": n, "start": s, "end": e} for n, s, e in WINDOWS],
        "risk_policy": {"version": "p04-fixed-fractional-r-v1", "risk_per_trade": market.risk_per_trade},
        "identity_verified": True, "baseline": _public(aggregate), "annual": _public_rows(annual),
        "costs_x2": _public(costs_x2), "costs_x2_annual": _public_rows(annual_x2),
        "comparison_prior_periods": comparison, "acceptance": decision,
        "rows_at_or_after_2023_loaded": 0, "holdout_used": False,
    }
    (output / "p07_report.json").write_text(json.dumps(report, sort_keys=True, indent=2, default=_json_default) + "\n")
    print(json.dumps({"run_id": report["run_id"], "strategy_hash": STRATEGY_HASH,
                      "decision": decision["decision"], "trades": aggregate["n_trades"]}, indent=2))
    return 0


def _frozen_finalist(manifest: dict) -> dict:
    if manifest.get("contract_version") != "p03.1-v1":
        raise ValueError("unexpected finalist manifest contract")
    found = [x for x in manifest.get("finalists", []) if x["strategy_hash"] == STRATEGY_HASH]
    if len(found) != 1:
        raise ValueError("P07 requires exactly one frozen P06 survivor in the manifest")
    return found[0]


def _load_market_before_holdout():
    cfg = yaml.safe_load((PROJECT_ROOT / "configs" / "data.yaml").read_text())
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / "EURUSD.parquet"
    frame = pd.read_parquet(cache, filters=[("ts_local", "<", datetime(2023, 1, 1))])
    metadata = pq.read_schema(cache).metadata or {}
    frame.attrs.update({key.decode(): value.decode() for key, value in metadata.items()})
    if frame.attrs.get("source_sha256") != EXPECTED_DATA_SHA256:
        raise ValueError("canonical cache source hash mismatch")
    if pd.Timestamp(frame["ts_local"].max()) >= pd.Timestamp("2023-01-01"):
        raise ValueError("P07 market contains holdout rows")
    return build_market("EURUSD", frame, Costs.for_pair("EURUSD"), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


def _metric_row(name: str, trades: pd.DataFrame, metrics: dict) -> dict:
    return {"window": name, "n_trades": int(metrics["n_trades"]), "profit_factor": float(metrics["profit_factor"]),
            "expectancy_R": float(metrics["mean_r"]), "return": float(metrics["return"]),
            "max_drawdown": float(metrics["max_dd"]), "sharpe": float(metrics["sharpe"]),
            "max_consecutive_losses": int(metrics["max_consec_losses"]), "total_R": float(metrics["total_r"]),
            "trades": trades}


def _aggregate(rows: list[dict], label: str) -> dict:
    frames = [x["trades"] for x in rows if not x["trades"].empty]
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["r", "exit_bar_time"])
    r = frame["r"].to_numpy(float) if not frame.empty else np.array([], dtype=float)
    equity = np.cumprod(1.0 + 0.005 * r) if len(r) else np.array([1.0])
    peaks = np.maximum.accumulate(equity)
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    daily = _daily_returns(frame)
    sharpe = float(np.sqrt(260.0) * daily.mean() / daily.std(ddof=0)) if len(daily) and daily.std(ddof=0) > 0 else 0.0
    return {"label": label, "n_trades": int(len(r)), "profit_factor": float(pos / neg) if neg else (float("inf") if len(r) else 0.0),
            "expectancy_R": float(r.mean()) if len(r) else 0.0, "total_R": float(r.sum()),
            "return": float(equity[-1] - 1.0), "max_drawdown": float(np.max(1.0 - equity / peaks)) if len(r) else 0.0,
            "sharpe": sharpe, "max_consecutive_losses": _loss_streak(r), "trades": frame}


def _daily_returns(frame: pd.DataFrame) -> np.ndarray:
    if frame.empty:
        return np.array([], dtype=float)
    days = pd.to_datetime(frame["exit_bar_time"]).dt.date
    return frame.assign(day=days).groupby("day")["r"].apply(lambda x: float(np.prod(1.0 + 0.005 * x) - 1.0)).to_numpy()


def _loss_streak(r: np.ndarray) -> int:
    best = current = 0
    for value in r:
        current = current + 1 if value < 0 else 0
        best = max(best, current)
    return int(best)


def _p04_dd_limit(report: dict, strategy_hash: str) -> float:
    risk = report.get("risk_policy", {})
    if risk.get("version") != "p04-fixed-fractional-r-v1" or float(risk.get("risk_per_trade")) != 0.005:
        raise ValueError("P04 drawdown policy is not comparable")
    result = report["monte_carlo"][strategy_hash]
    values = [float(result[name]["quantiles"]["dd_p95"]) for name in ("moving", "stationary", "period_block")]
    if not all(np.isfinite(values)):
        raise ValueError("P04 drawdown limit is unavailable")
    return max(values)


def _comparison() -> dict:
    p06 = json.loads(P06_REPORT.read_text())
    manifest = json.loads(MANIFEST.read_text())
    finalist = _frozen_finalist(manifest)
    dev = finalist["metrics"]
    wf = next(x for x in p06["results"] if x["strategy_hash"] == STRATEGY_HASH)
    return {"dev_train": {key: dev[key] for key in ("n_trades", "profit_factor", "mean_r", "return", "max_dd", "sharpe")},
            "development_wf": {key: wf["aggregate"][key] for key in ("n_trades", "profit_factor", "expectancy_R", "return", "max_drawdown", "sharpe")}}


def _public(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "trades"}


def _public_rows(rows: list[dict]) -> list[dict]:
    return [_public(row) for row in rows]


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    raise SystemExit(main())
