"""Resumable chronological evaluator for P09 Q2-2019 through Q4-2022."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from new_forex.backtest.evaluator import Costs, build_market, evaluate_rich
from new_forex.provenance import PROJECT_ROOT, file_sha256, load_config
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.rolling_historical import checkpoint_path, portfolio_ledger, portfolio_metrics, remaining_generations

POLICY = PROJECT_ROOT / "configs" / "rolling_factory.yaml"
POLICY_SHA256 = "73f7bb0649c814a0ec076fff9d9e3413ba480fb31eca765ed18b860f6e1c72ed"
PILOT = PROJECT_ROOT / "runs" / "p08-rolling-2019-q1-v3" / "generation.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT / "runs" / "p09-rolling-historical-v1")
    parser.add_argument("--artifacts", type=Path, default=PROJECT_ROOT / "reports" / "p09_artifacts")
    args = parser.parse_args()
    if file_sha256(POLICY) != POLICY_SHA256:
        raise ValueError("P08 policy SHA256 changed")
    pilot = json.loads(PILOT.read_text())
    if pilot["policy_sha256"] != POLICY_SHA256 or pilot["birth_date"] != "2019-01-01":
        raise ValueError("P08 pilot is not the frozen reference generation")
    args.root.mkdir(parents=True, exist_ok=True)
    args.artifacts.mkdir(parents=True, exist_ok=True)
    checkpoint = checkpoint_path(args.artifacts)
    state = json.loads(checkpoint.read_text()) if checkpoint.exists() else {"completed": [], "failures": []}
    completed = set(state.get("completed", []))
    for generation in remaining_generations():
        if generation.label in completed:
            continue
        output = args.root / generation.label
        command = [sys.executable, str(PROJECT_ROOT / "scripts" / "run_p08_rolling_factory.py"),
                   "--output", str(output), "--birth", generation.birth, "--max-evals", "100000",
                   "--population", "1000", "--generations", "102", "--mc-iterations", "5000",
                   "--seed", str(20261003 + generation.index)]
        try:
            subprocess.run(command, cwd=PROJECT_ROOT, check=True, env={"PYTHONPATH": "src", **dict(os.environ)})
            report = json.loads((output / "generation.json").read_text())
            _verify_generation(report, generation, output)
            completed.add(generation.label)
            state["completed"] = sorted(completed)
            state["last_completed"] = generation.label
            state["policy_sha256"] = POLICY_SHA256
            checkpoint.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n")
        except Exception as exc:
            state.setdefault("failures", []).append({"generation": generation.label, "error": repr(exc)})
            checkpoint.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n")
            raise
    consolidated = _consolidate(args.root, args.artifacts, pilot)
    (args.artifacts / "consolidated.json").write_text(json.dumps(consolidated, sort_keys=True, indent=2, default=str) + "\n")
    print(json.dumps({"completed": len(completed), "generations": 15, "portfolio_trades": consolidated["portfolio"]["n_trades"]}, indent=2))
    return 0


def _verify_generation(report: dict, generation, output: Path) -> None:
    if report["policy_id"] != "p08-rolling-factory-v1" or report["policy_sha256"] != POLICY_SHA256:
        raise ValueError(f"{generation.label}: policy mismatch")
    if report["birth_date"] != generation.birth or report["windows"]["forward"][1] != generation.forward_end:
        raise ValueError(f"{generation.label}: window mismatch")
    if report["ga"]["n_evaluated"] != 100_000 or report["holdout_used"]:
        raise ValueError(f"{generation.label}: GA budget or holdout check failed")
    for item in report["ledgers"]["forward"]:
        path = output / item["path"]
        if file_sha256(path) != item["sha256"]:
            raise ValueError(f"{generation.label}: ledger checksum mismatch")
        frame = pd.read_parquet(path)
        if len(frame) != item["n_trades"]:
            raise ValueError(f"{generation.label}: ledger trade count mismatch")
        if not frame.empty and (pd.to_datetime(frame["entry_timestamp"], utc=True).dt.tz_localize(None) < pd.Timestamp(generation.birth)).any():
            raise ValueError(f"{generation.label}: forward entry before birth")
        if not frame.empty and (pd.to_datetime(frame["exit_timestamp"], utc=True).dt.tz_localize(None) >= pd.Timestamp(generation.forward_end)).any():
            raise ValueError(f"{generation.label}: forward exit outside quarter")


def _consolidate(root: Path, artifacts: Path, pilot: dict) -> dict:
    rows = [{"label": "2019Q1", "birth": "2019-01-01", "forward_end": "2019-04-01", "pilot": True,
             "selected": pilot["finalists"], "forward": pilot["forward"]}]
    ledgers: list[tuple[str, pd.DataFrame]] = []
    by_generation: list[tuple[str, str, list[tuple[str, pd.DataFrame]]]] = []
    pilot_ledgers: list[tuple[str, pd.DataFrame]] = []
    for item in pilot["ledgers"]["forward"]:
        frame = pd.read_parquet(PROJECT_ROOT / "runs" / "p08-rolling-2019-q1-v3" / item["path"])
        pilot_ledgers.append((item["strategy_hash"], frame))
    ledgers.extend(pilot_ledgers)
    by_generation.append(("2019Q1", "2019-01-01", pilot_ledgers))
    for generation in remaining_generations():
        report = json.loads((root / generation.label / "generation.json").read_text())
        rows.append({"label": generation.label, "birth": generation.birth, "forward_end": generation.forward_end,
                     "pilot": False, "selected": report["finalists"], "forward": report["forward"]})
        generation_ledgers = []
        for item in report["ledgers"]["forward"]:
            frame = pd.read_parquet(root / generation.label / item["path"])
            ledgers.append((item["strategy_hash"], frame))
            generation_ledgers.append((item["strategy_hash"], frame))
        by_generation.append((generation.label, generation.birth, generation_ledgers))
    portfolio = portfolio_ledger(ledgers)
    if not portfolio.empty and (pd.to_datetime(portfolio["exit_timestamp"], utc=True) >= pd.Timestamp("2023-01-01", tz="UTC")).any():
        raise ValueError("portfolio contains rows at or after final holdout")
    portfolio_by_generation = []
    horizons = []
    for label, birth, generation_ledgers in by_generation:
        generation_portfolio = portfolio_ledger(generation_ledgers)
        portfolio_by_generation.append({"label": label, "birth": birth, **portfolio_metrics(generation_portfolio)})
        for days in (30, 60, 90):
            end = pd.Timestamp(birth, tz="UTC") + pd.Timedelta(days=days)
            part = generation_portfolio[generation_portfolio["timestamp"] < end]
            horizons.append({"label": label, "birth": birth, "horizon_days": days, **portfolio_metrics(part)})
    costs_x2 = _forward_costs_x2(root, by_generation)
    portfolio.to_csv(artifacts / "portfolio_ledger.csv", index=False)
    pd.DataFrame(portfolio_by_generation).to_csv(artifacts / "portfolio_by_generation.csv", index=False)
    pd.DataFrame(horizons).to_csv(artifacts / "portfolio_horizons_30_60_90.csv", index=False)
    (artifacts / "forward_costs_x2.json").write_text(json.dumps(costs_x2, sort_keys=True, indent=2, default=str) + "\n")
    pd.DataFrame(rows).to_json(artifacts / "generation_results.json", orient="records", indent=2)
    return {"policy_sha256": POLICY_SHA256, "pilot_preserved": True, "generations": rows,
            "portfolio": portfolio_metrics(portfolio), "portfolio_by_generation": portfolio_by_generation,
            "portfolio_horizons": "portfolio_horizons_30_60_90.csv", "forward_costs_x2": costs_x2,
            "portfolio_ledger": "portfolio_ledger.csv",
            "no_holdout_rows": True}


def _forward_costs_x2(root: Path, by_generation: list[tuple[str, str, list[tuple[str, pd.DataFrame]]]]) -> dict:
    cfg = load_config("data")
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / "EURUSD.parquet"
    frame = pd.read_parquet(cache, filters=[("ts_local", "<", pd.Timestamp("2023-01-01").to_pydatetime())])
    metadata = pq.read_schema(cache).metadata or {}
    frame.attrs.update({key.decode(): value.decode() for key, value in metadata.items()})
    if frame.attrs.get("source_sha256") != "29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4":
        raise ValueError("P09 costs-x2 cache hash mismatch")
    market = build_market("EURUSD", frame, Costs.for_pair("EURUSD"), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))
    results = {}
    portfolio_ledgers: list[tuple[str, pd.DataFrame]] = []
    for label, _birth, _ledgers in by_generation:
        run_dir = PROJECT_ROOT / "runs" / "p08-rolling-2019-q1-v3" if label == "2019Q1" else root / label
        report = json.loads((run_dir / "generation.json").read_text())
        result_rows = []
        for item in report["ledgers"]["forward"]:
            strategy = StrategyDefinition.from_json(json.dumps(next(x["strategy"] for x in json.loads((run_dir / "finalists.json").read_text())
                                                                   if x["strategy_hash"] == item["strategy_hash"])))
            bounds = tuple(report["windows"]["forward"])
            rich = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=2.0, window=_window(market, *bounds))
            portfolio_ledgers.append((strategy.canonical_hash, pd.DataFrame({
                "entry_timestamp": pd.to_datetime(rich.trades["entry_time"], utc=True),
                "exit_timestamp": pd.to_datetime(rich.trades["exit_bar_time"], utc=True),
                "result_R": rich.trades["r"].to_numpy(float),
            })))
            result_rows.append({"strategy_hash": strategy.canonical_hash, "n_trades": int(rich.metrics["n_trades"]),
                                "expectancy_R": float(rich.metrics["mean_r"]), "profit_factor": float(rich.metrics["profit_factor"]),
                                "return": float(rich.metrics["return"]), "max_drawdown": float(rich.metrics["max_dd"])})
        results[label] = result_rows
    return {"by_generation": results, "portfolio": portfolio_metrics(portfolio_ledger(portfolio_ledgers))}


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


if __name__ == "__main__":
    raise SystemExit(main())
