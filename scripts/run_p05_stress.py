"""Run P05 stress on the frozen P03.1 EURUSD finalist manifest only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

from new_forex.backtest.evaluator import Costs, build_market
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import PROJECT_ROOT, code_version, file_sha256
from new_forex.strategy.definition import StrategyDefinition
from new_forex.stress.evaluator import evaluate_scenario

EXPECTED_DATA_SHA256 = "29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4"
DEV_START = "2003-01-01"
DEV_END = "2015-01-01"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", default=DEV_START)
    parser.add_argument("--end", default=DEV_END)
    args = parser.parse_args()
    stress_config_path = PROJECT_ROOT / "configs" / "stress.yaml"
    stress_cfg = yaml.safe_load(stress_config_path.read_text())
    if stress_cfg["version"] != "p05-stress-v1":
        raise ValueError("unexpected P05 stress configuration version")
    manifest = json.loads(args.manifest.read_text())
    if len(manifest["finalists"]) != 25:
        raise ValueError("P05 requires the frozen 25-finalist manifest")
    if manifest["config"]["partition"] != "dev_train" or manifest["config"]["end"] != DEV_END:
        raise ValueError("P05 manifest is not the frozen DEV/TRAIN export")
    partition = DataAccessPolicy.load().assert_range(args.start, args.end)
    if partition is Partition.FINAL_HOLDOUT:
        raise ValueError("P05 cannot access final holdout")

    market = _load_market_from_cache("EURUSD")
    window = _window(market, args.start, args.end)
    scenarios = _scenarios(stress_cfg)
    rows: list[dict] = []
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for finalist in manifest["finalists"]:
        strategy_hash = finalist["strategy_hash"]
        strategy = StrategyDefinition.from_json(json.dumps(finalist["strategy"]))
        if strategy.canonical_hash != strategy_hash:
            raise ValueError(f"strategy hash mismatch: {strategy_hash}")
        ledger_path = args.manifest.parent / finalist["ledger"]
        if file_sha256(ledger_path) != finalist["ledger_sha256"]:
            raise ValueError(f"frozen ledger checksum mismatch: {strategy_hash}")
        frozen = pd.read_parquet(ledger_path)
        baseline_frozen = _frozen_metrics(frozen)
        baseline_live = None
        for scenario in scenarios:
            trades, metrics = evaluate_scenario(market, strategy, window=window, **scenario["parameters"])
            summary = _metrics(metrics)
            if scenario["name"] == "baseline_x1":
                baseline_live = summary
                _assert_baseline_parity(baseline_frozen, summary, strategy_hash)
            rows.append({"strategy_hash": strategy_hash, "scenario": scenario["name"],
                         "scenario_version": stress_cfg["version"], "metrics": summary,
                         "delta_vs_baseline": _delta(summary, baseline_live or baseline_frozen),
                         "technical_acceptance": _technical_acceptance(trades, strategy_hash),
                         "performance_acceptance": "NOT_EVALUATED_NO_PREESTABLISHED_P05_GATE"})

    report = {
        "contract_version": "p05-stress-v1",
        "run_id": output.name,
        "code_version": code_version(),
        "source_manifest": str(args.manifest),
        "manifest_sha256": _sha256_bytes(args.manifest.read_bytes()),
        "dataset_sha256": EXPECTED_DATA_SHA256,
        "partition": partition.value,
        "period": {"start": args.start, "end": args.end},
        "scenario_config": stress_cfg,
        "scenario_config_sha256": file_sha256(stress_config_path),
        "finalist_count": 25,
        "rows": rows,
        "null_world_interpretation": {
            "positive_fraction": 1.0,
            "meaning": "fraction of selected candidates with positive one-score null training metric",
            "conditioning": "conditioned on top_k selection within each null world",
            "out_of_sample": False,
            "predictive_validity": "not measured",
        },
        "gate": "BLOCKED_NO_PREESTABLISHED_P05_PERFORMANCE_CRITERIA",
        "holdout_used": False,
    }
    (output / "p05_report.json").write_text(json.dumps(report, sort_keys=True, indent=2, default=str) + "\n")
    print(json.dumps({"run_id": report["run_id"], "finalists": 25,
                      "scenarios": len(scenarios), "rows": len(rows), "gate": report["gate"]}, indent=2))
    return 0


def _load_market_from_cache(pair: str):
    cfg = yaml.safe_load((PROJECT_ROOT / "configs" / "data.yaml").read_text())
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / f"{pair}.parquet"
    if not cache.exists():
        raise FileNotFoundError(cache)
    m15 = pd.read_parquet(cache)
    metadata = pq.read_schema(cache).metadata or {}
    m15.attrs.update({key.decode(): value.decode() for key, value in metadata.items()})
    if m15.attrs.get("source_sha256") != EXPECTED_DATA_SHA256:
        raise ValueError("canonical cache source hash does not match frozen P04 input")
    return build_market(pair, m15, Costs.for_pair(pair), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


def _scenarios(cfg: dict) -> list[dict]:
    variable = cfg["variable_slippage"]
    common = {"slippage_min_pips": variable["extra_side_pips_min"],
              "slippage_max_pips": variable["extra_side_pips_max"], "range_cap_pips": variable["range_cap_pips"],
              "perturbation_amplitude": cfg["price_perturbation"]["amplitude"],
              "perturbation_period_m15": cfg["price_perturbation"]["period_m15_bars"]}
    return [
        {"name": "baseline_x1", "parameters": {"cost_multiplier": 1.0}},
        {"name": "cost_x1_5", "parameters": {"cost_multiplier": 1.5}},
        {"name": "cost_x2", "parameters": {"cost_multiplier": 2.0}},
        {"name": "variable_slippage", "parameters": {**common, "variable_slippage": True}},
        {"name": "delay_m15_1", "parameters": {"m15_delay_bars": 1}},
        {"name": "delay_m15_2", "parameters": {"m15_delay_bars": 2}},
        {"name": "price_perturbation", "parameters": {**common, "price_perturbation": True}},
        {"name": "combined_adverse", "parameters": {**common, "cost_multiplier": 2.0,
                                                         "variable_slippage": True, "m15_delay_bars": 2}},
    ]


def _metrics(metrics: dict) -> dict:
    return {"profit_factor": float(metrics["profit_factor"]), "mean_r": float(metrics["mean_r"]),
            "cumulative_return": float(metrics["return"]), "max_drawdown": float(metrics["max_dd"]),
            "n_trades": int(metrics["n_trades"]), "total_r": float(metrics["total_r"])}


def _frozen_metrics(frame: pd.DataFrame) -> dict:
    r = frame["result_R"].to_numpy(float)
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    equity = (1.0 + 0.005 * r).cumprod()
    peaks = np.maximum.accumulate(equity)
    return {"profit_factor": float(wins / losses) if losses else float("inf"), "mean_r": float(r.mean()),
            "cumulative_return": float(equity[-1] - 1.0), "max_drawdown": float((1 - equity / peaks).max()),
            "n_trades": int(len(r)), "total_r": float(r.sum())}


def _assert_baseline_parity(frozen: dict, live: dict, strategy_hash: str) -> None:
    if frozen["n_trades"] != live["n_trades"] or abs(frozen["total_r"] - live["total_r"]) > 1e-8:
        raise ValueError(f"baseline backtester parity failed for {strategy_hash}")


def _delta(current: dict, baseline: dict) -> dict:
    return {key: float(current[key] - baseline[key]) if key != "n_trades" else int(current[key] - baseline[key])
            for key in current}


def _technical_acceptance(trades: pd.DataFrame, strategy_hash: str) -> str:
    required = {"entry_time", "exit_bar_time", "entry_idx", "exit_idx"}
    if not required.issubset(trades.columns) or not (trades["exit_idx"] >= trades["entry_idx"]).all():
        return f"REJECT_TECHNICAL:{strategy_hash}"
    return "PASS_TECHNICAL"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
