"""Measure fixed P12F cohort persistence over the nine pre-holdout quarters."""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from new_forex.backtest.evaluator import evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12g_fixed_cohort.yaml"
OUT = ROOT / "reports/p12g_artifacts"
P12F_ELIGIBILITY = ROOT / "reports/p12f_artifacts/eligibility.parquet"
P12F_COMPOSITIONS = ROOT / "reports/p12f_artifacts/portfolio_compositions.jsonl"
P12D = ROOT / "reports/p12d_artifacts/population_lifecycle.parquet"
ARCHIVE = ROOT / "runs/p08-rolling-2019-q1-v3/ga_archive.jsonl"

sys.path.insert(0, str(ROOT / "scripts"))
from run_p08_rolling_factory import _load_market_until, _window  # noqa: E402


def _assert_sources(config: dict) -> None:
    expected = {
        P12F_ELIGIBILITY: config["source"]["p12f_eligibility_sha256"],
        P12F_COMPOSITIONS: config["source"]["p12f_compositions_sha256"],
        P12D: config["source"]["p12d_population_sha256"],
        ARCHIVE: config["source"]["archive_sha256"],
    }
    for path, digest in expected.items():
        if file_sha256(path) != digest:
            raise ValueError(f"source SHA256 mismatch: {path}")


def _load_strategies(keys: set[str]) -> dict[str, StrategyDefinition]:
    strategies: dict[str, StrategyDefinition] = {}
    with ARCHIVE.open() as handle:
        for line in handle:
            row = json.loads(line)
            key = row["canonical_hash"]
            if key not in keys:
                continue
            strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
            if strategy.canonical_hash != key:
                raise ValueError(f"strategy identity mismatch: {key}")
            strategies[key] = strategy
    if set(strategies) != keys:
        raise ValueError("archive does not contain every frozen cohort strategy")
    return strategies


def _load_cohort(config: dict) -> tuple[pd.DataFrame, list[dict], dict[str, StrategyDefinition]]:
    eligibility = pd.read_parquet(P12F_ELIGIBILITY)
    cohort = eligibility[eligibility["high_quality"]].copy()
    if len(cohort) != int(config["cohort"]["expected_strategies"]) or not cohort["strategy_hash"].is_unique:
        raise ValueError("P12F frozen cohort identity failure")
    compositions = [json.loads(line) for line in P12F_COMPOSITIONS.read_text().splitlines() if line.strip()]
    compositions = [row for row in compositions if row["group"] == config["cohort"]["composition_group"]]
    if len(compositions) != int(config["cohort"]["expected_compositions"]):
        raise ValueError("P12F frozen composition count failure")
    cohort_keys = set(cohort["strategy_hash"])
    for row in compositions:
        selected = json.loads(row["selected"])
        if len(selected) != 5 or len(set(selected)) != 5 or not set(selected) <= cohort_keys:
            raise ValueError("P12F composition is not five distinct frozen cohort strategies")
        row["selected"] = selected
    return cohort, compositions, _load_strategies(cohort_keys)


def _individual(cohort: pd.DataFrame, p12d: pd.DataFrame, quarters: list[str]) -> pd.DataFrame:
    selected = p12d[p12d["strategy_hash"].isin(cohort["strategy_hash"]) & p12d["quarter"].isin(quarters)].copy()
    if len(selected) != len(cohort) * len(quarters) or selected.duplicated(["strategy_hash", "quarter"]).any():
        raise ValueError("P12D fixed-cohort longitudinal integrity failure")
    if (selected["forward_n_trades"] != selected["forward_x2_n_trades"]).any():
        raise ValueError("baseline/x2 operation counts differ")
    selected = selected.merge(cohort[["strategy_hash", "training_profit_factor", "training_n_trades", "direction", "complexity"]], on="strategy_hash", how="left", validate="many_to_one")
    selected["gross_total_R"] = 2 * selected["forward_total_R"] - selected["forward_x2_total_R"]
    selected["gross_expectancy_R"] = np.divide(selected["gross_total_R"], selected["forward_n_trades"], out=np.zeros(len(selected)), where=selected["forward_n_trades"].to_numpy() != 0)
    selected["cost_R_total"] = selected["gross_total_R"] - selected["forward_total_R"]
    selected["cost_R_per_trade"] = np.divide(selected["cost_R_total"], selected["forward_n_trades"], out=np.full(len(selected), np.nan), where=selected["forward_n_trades"].to_numpy() != 0)
    return selected


def _individual_summary(individual: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for quarter, frame in individual.groupby("quarter", sort=True):
        active = frame.forward_n_trades > 0
        for label, prefix in (("baseline", "forward"), ("costs_x2", "forward_x2")):
            exp = frame[f"{prefix}_expectancy_R"]
            ret = frame[f"{prefix}_return"]
            rows.append({
                "quarter": quarter, "cost": label, "strategies": len(frame), "active": int(active.sum()),
                "active_pct": float(active.mean()), "operations": int(frame["forward_n_trades"].sum()),
                "mean_gross_expectancy_R_active": float(frame.loc[active, "gross_expectancy_R"].mean()),
                "median_gross_expectancy_R_active": float(frame.loc[active, "gross_expectancy_R"].median()),
                "mean_net_expectancy_R_active": float(exp[active].mean()),
                "median_net_expectancy_R_active": float(exp[active].median()),
                "mean_return": float(ret.mean()), "median_return": float(ret.median()),
                "p05_return": float(ret.quantile(.05)), "p95_return": float(ret.quantile(.95)),
                "median_profit_factor_finite": float(frame[f"{prefix}_profit_factor"].replace([np.inf, -np.inf], np.nan).median()),
                "mean_max_drawdown": float(frame[f"{prefix}_max_drawdown"].mean()),
                "mean_cost_R_per_trade": float(frame.loc[active, "cost_R_per_trade"].mean()),
                "gross_capitalized_individual_return_available": False,
            })
    return pd.DataFrame(rows)


def _portfolio_metrics(frame: pd.DataFrame, gross: pd.DataFrame | None, cost: str) -> dict:
    metrics = portfolio_metrics(frame)
    values = frame["result_R"].to_numpy(float) if not frame.empty else np.array([], dtype=float)
    wins, losses = values[values > 0].sum(), -values[values < 0].sum()
    result = {
        "n_trades": metrics["n_trades"], "return": metrics["return"], "max_drawdown": metrics["max_drawdown"],
        "pnl_net": metrics["pnl"], "expectancy_R": float(values.mean()) if len(values) else 0.0,
        "profit_factor": float(wins / losses) if losses else (math.inf if wins > 0 else 0.0), "cost": cost,
    }
    if gross is not None:
        result["pnl_gross"] = float(gross["pnl"].sum()) if not gross.empty else 0.0
        result["return_gross"] = float(gross["equity"].iloc[-1] - 1.0) if not gross.empty else 0.0
        result["expectancy_gross_R"] = float(gross["result_R"].mean()) if not gross.empty else 0.0
        result["cost_absolute"] = result["pnl_gross"] - result["pnl_net"]
    return result


def _evaluate_portfolios(compositions: list[dict], strategies: dict[str, StrategyDefinition], market, quarters: list[str], config: dict) -> pd.DataFrame:
    ledgers: dict[tuple[str, str, float], pd.DataFrame] = {}
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed": []}
    quarter_dates = {q: (str(pd.Period(q, freq="Q").start_time.date()), str((pd.Period(q, freq="Q").start_time + pd.DateOffset(months=3)).date())) for q in quarters}
    keys = sorted({key for row in compositions for key in row["selected"]})
    for quarter in quarters:
        window = _window(market, *quarter_dates[quarter])
        for multiplier in (1.0, 2.0):
            marker = f"{quarter}:{multiplier:g}"
            path = OUT / f"ledgers_{quarter}_{multiplier:g}.parquet"
            if marker in checkpoint["completed"] and path.exists():
                cached = pd.read_parquet(path)
                for key, frame in cached.groupby("strategy_hash", sort=False):
                    ledgers[(key, quarter, multiplier)] = frame.drop(columns="strategy_hash")
                continue
            frames = []
            for key in keys:
                rich = evaluate_rich(market, strategies[key], exec_tf="M15", cost_multiplier=multiplier, window=window)
                ledger = _ledger_frame(rich.trades, strategies[key], market).copy()
                ledger["strategy_hash"] = key
                frames.append(ledger)
                ledgers[(key, quarter, multiplier)] = ledger.drop(columns="strategy_hash")
            pd.concat(frames, ignore_index=True).to_parquet(path, index=False)
            checkpoint["completed"].append(marker)
            checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")

    rows = []
    for composition in compositions:
        for quarter in quarters:
            base_frames = [ledgers[(key, quarter, 1.0)] for key in composition["selected"]]
            x2_frames = [ledgers[(key, quarter, 2.0)] for key in composition["selected"]]
            base_ledgers = list(zip(composition["selected"], base_frames, strict=True))
            x2_ledgers = list(zip(composition["selected"], x2_frames, strict=True))
            base = portfolio_ledger(base_ledgers, risk_per_trade=config["evaluation"]["risk_per_trade"], max_aggregate_risk=config["evaluation"]["max_aggregate_risk"])
            x2 = portfolio_ledger(x2_ledgers, risk_per_trade=config["evaluation"]["risk_per_trade"], max_aggregate_risk=config["evaluation"]["max_aggregate_risk"])
            derived = []
            for key, base_frame, x2_frame in zip(composition["selected"], base_frames, x2_frames, strict=True):
                identity = ["entry_timestamp", "exit_timestamp"]
                if len(base_frame) != len(x2_frame) or not base_frame[identity].reset_index(drop=True).equals(x2_frame[identity].reset_index(drop=True)):
                    raise ValueError("baseline/x2 operation identity mismatch")
                gross_frame = base_frame.copy()
                gross_frame["result_R"] = 2 * base_frame["result_R"].to_numpy(float) - x2_frame["result_R"].to_numpy(float)
                derived.append((key, gross_frame))
            gross = portfolio_ledger(derived, risk_per_trade=config["evaluation"]["risk_per_trade"], max_aggregate_risk=config["evaluation"]["max_aggregate_risk"])
            base_metrics = _portfolio_metrics(base, gross, "baseline")
            x2_metrics = _portfolio_metrics(x2, gross, "costs_x2")
            for _label, metrics in (("baseline", base_metrics), ("costs_x2", x2_metrics)):
                rows.append({"composition_id": composition["replicate"], "seed": composition["seed"], "quarter": quarter, **metrics})
    result = pd.DataFrame(rows)
    x2 = result.cost.eq("costs_x2")
    base = result[result.cost.eq("baseline")].set_index(["composition_id", "quarter"])
    idx = pd.MultiIndex.from_frame(result.loc[x2, ["composition_id", "quarter"]])
    result.loc[x2, ["pnl_gross", "return_gross", "expectancy_gross_R"]] = base.reindex(idx)[["pnl_gross", "return_gross", "expectancy_gross_R"]].to_numpy()
    result.loc[x2, "cost_absolute"] = result.loc[x2, "pnl_gross"] - result.loc[x2, "pnl_net"]
    return result


def _trajectory(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (composition, cost), frame in results.groupby(["composition_id", "cost"], sort=True):
        frame = frame.sort_values("quarter")
        curve = np.cumprod(1 + frame["return"].to_numpy(float))
        gross_curve = np.cumprod(1 + frame["return_gross"].to_numpy(float))
        peaks = np.maximum.accumulate(curve)
        rows.append({
            "composition_id": composition, "cost": cost, "final_return": float(curve[-1] - 1),
            "final_gross_return": float(gross_curve[-1] - 1), "max_drawdown": float((1 - curve / peaks).max()),
            "positive_quarters": int((frame["return"] > 0).sum()), "n_trades": int(frame["n_trades"].sum()),
            "cost_total": float(frame["cost_absolute"].sum()),
        })
    return pd.DataFrame(rows)


def main() -> None:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    _assert_sources(config)
    DataAccessPolicy.load().assert_readable(Partition.DEVELOPMENT_WF)
    quarters = config["source"]["forward_quarters"]
    cohort, compositions, strategies = _load_cohort(config)
    p12d = pd.read_parquet(P12D)
    individual = _individual(cohort, p12d, quarters)
    q1 = individual[individual.quarter.eq("2017Q1")].set_index("strategy_hash").sort_index()
    p12f = pd.read_parquet(ROOT / "reports/p12f_artifacts/individual_population.parquet").set_index("strategy_hash").sort_index()
    for field in ("forward_n_trades", "forward_total_R", "forward_expectancy_R", "forward_return", "forward_x2_total_R", "forward_x2_expectancy_R", "forward_x2_return"):
        if not np.allclose(q1[field].to_numpy(), p12f.loc[q1.index, field].to_numpy(), equal_nan=True):
            raise ValueError(f"P12F Q1 equivalence failure: {field}")
    OUT.mkdir(parents=True, exist_ok=True)
    individual.to_parquet(OUT / "individual_quarterly.parquet", index=False)
    _individual_summary(individual).to_csv(OUT / "individual_quarterly_summary.csv", index=False)
    signatures = individual.assign(signature=individual[["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"]].astype(str).agg("|".join, axis=1))
    dependence = signatures.groupby("quarter", as_index=False).agg(observations=("strategy_hash", "size"), unique_strategies=("strategy_hash", "nunique"), unique_signatures=("signature", "nunique"))
    dependence["duplicate_signature_rows"] = dependence["observations"] - dependence["unique_signatures"]
    dependence.to_csv(OUT / "dependence.csv", index=False)
    market = _load_market_until(config["evaluation"]["source_end_exclusive"])
    results = _evaluate_portfolios(compositions, strategies, market, quarters, config)
    results.to_csv(OUT / "portfolio_quarterly.csv", index=False)
    trajectory = _trajectory(results)
    trajectory.to_csv(OUT / "trajectories.csv", index=False)
    portfolio_summary = results.groupby(["quarter", "cost"], as_index=False).agg(
        compositions=("composition_id", "nunique"), operations_median=("n_trades", "median"),
        positive_fraction=("return", lambda s: float((s > 0).mean())), median_return=("return", "median"),
        p05_return=("return", lambda s: s.quantile(.05)), p95_return=("return", lambda s: s.quantile(.95)),
        median_gross_return=("return_gross", "median"), median_max_drawdown=("max_drawdown", "median"),
        median_cost_absolute=("cost_absolute", "median"),
    )
    portfolio_summary.to_csv(OUT / "portfolio_summary.csv", index=False)
    manifest = {
        "policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "p12f_eligibility_sha256": file_sha256(P12F_ELIGIBILITY), "p12f_compositions_sha256": file_sha256(P12F_COMPOSITIONS),
        "p12d_sha256": file_sha256(P12D), "archive_sha256": file_sha256(ARCHIVE), "strategies": len(cohort),
        "compositions": len(compositions), "quarters": quarters, "individual_rows": len(individual),
        "portfolio_rows": len(results), "trajectory_rows": len(trajectory), "p12f_q1_equivalence": True,
        "holdout_used": False, "elapsed_seconds": time.perf_counter() - started,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
