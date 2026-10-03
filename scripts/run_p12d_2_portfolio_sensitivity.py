"""Measure composition sensitivity inside the frozen P12D.1 eligible population."""
from __future__ import annotations

import hashlib
import json
import random
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from new_forex.backtest.evaluator import evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame
from new_forex.walk_forward.rolling_historical import portfolio_ledger
from run_p12d_1_selection_power import extended_portfolio_metrics, load_historical, quarter_window
from run_p12d_1_selection_power import mask_for as historical_mask

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12d_2_portfolio_sensitivity.yaml"
P12D = ROOT / "reports/p12d_artifacts/population_lifecycle.parquet"
P12D1_PORTFOLIOS = ROOT / "reports/p12d_1_artifacts/portfolio_results.csv"
ARCHIVE = ROOT / "runs/p08-rolling-2019-q1-v3/ga_archive.jsonl"
OUT = ROOT / "reports/p12d_2_artifacts"


def cumulative_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (portfolio_id, cost), frame in results.groupby(["portfolio_id", "cost"], sort=True):
        frame = frame.sort_values("quarter")
        returns = frame["return"].to_numpy(float)
        curve = np.cumprod(1 + returns)
        peaks = np.maximum.accumulate(curve)
        rows.append({"portfolio_id": portfolio_id, "cost": cost, "cumulative_return": float(curve[-1] - 1), "mean_quarterly_return": float(returns.mean()), "positive_quarter_fraction": float((returns > 0).mean()), "max_drawdown": float((1 - curve / peaks).max()), "expectancy_R_mean": float(frame["expectancy_R"].mean()), "profit_factor_mean": float(frame["profit_factor"].replace([np.inf, -np.inf], np.nan).mean()), "n_trades_total": int(frame["n_trades"].sum())})
    return pd.DataFrame(rows)


def load_original() -> list[str]:
    frame = pd.read_csv(P12D1_PORTFOLIOS)
    row = frame[(frame.group == "train_pf_105_n100_portfolio") & (frame.replicate == 0)].iloc[0]
    return json.loads(row.selected)


def main() -> None:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    if config["evaluation"]["no_forward_selection"] is not True or config["evaluation"]["no_reselection"] is not True:
        raise ValueError("P12D.2 causal safeguards are not enabled")
    if file_sha256(ARCHIVE) != config["archive_sha256"]:
        raise ValueError("archive SHA256 mismatch")
    access = DataAccessPolicy.load()
    access.assert_readable(Partition.DEVELOPMENT_WF)
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    historical, strategies = load_historical()
    eligible_mask = historical_mask(historical, "train_pf_105_n100")
    eligible = sorted(historical.loc[eligible_mask, "strategy_hash"])
    if len(eligible) < int(config["evaluation"]["portfolio_size"]):
        raise RuntimeError("fewer than five historically eligible strategies")
    p12d = pd.read_parquet(P12D)
    if len(p12d) != 900_000 or p12d["strategy_hash"].nunique() != 100_000:
        raise ValueError("P12D dataset integrity failure")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eligible_universe.csv").write_text(historical[eligible_mask].to_csv(index=False))
    historical[eligible_mask].describe(include="all").transpose().to_csv(OUT / "eligible_describe.csv")
    structural = historical[eligible_mask].groupby(["direction", "complexity"], as_index=False).size()
    structural.to_csv(OUT / "eligible_structural_families.csv", index=False)

    original = load_original()
    if not set(original) <= set(eligible) or len(original) != 5:
        raise ValueError("P12D.1 original portfolio is not inside the historical eligible universe")
    seed_base = int(config["evaluation"]["seed_base"])
    portfolio_size = int(config["evaluation"]["portfolio_size"])
    n_portfolios = int(config["evaluation"]["portfolios"])
    compositions = [{"portfolio_id": i, "seed": seed_base + i, "selected": sorted(random.Random(seed_base + i).sample(eligible, portfolio_size))} for i in range(n_portfolios)]
    compositions.append({"portfolio_id": "original_p12d1", "seed": None, "selected": sorted(original)})
    (OUT / "compositions.jsonl").write_text("\n".join(json.dumps(row, sort_keys=True) for row in compositions) + "\n")
    all_hashes = set(original)
    for row in compositions[:n_portfolios]:
        all_hashes.update(row["selected"])

    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until("2019-04-01")
    checkpoint_path = OUT / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else {"completed_quarters": []}
    ledger_cache: dict[tuple[str, str, float], pd.DataFrame] = {}
    for quarter in config["quarters"]:
        for cost_name, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
            cache_path = OUT / f"ledgers_{quarter}_{cost_name}.parquet"
            key = f"{quarter}:{cost_name}"
            if key in checkpoint["completed_quarters"] and cache_path.exists():
                cached = pd.read_parquet(cache_path)
                for strategy_hash, frame in cached.groupby("strategy_hash", sort=False):
                    ledger_cache[(quarter, strategy_hash, multiplier)] = frame.drop(columns=["strategy_hash"])
                continue
            window = _window(market, *quarter_window(quarter))
            frames = []
            for strategy_hash in sorted(all_hashes):
                rich = evaluate_rich(market, strategies[strategy_hash], exec_tf="M15", cost_multiplier=multiplier, window=window)
                ledger = _ledger_frame(rich.trades, strategies[strategy_hash], market).copy()
                ledger["strategy_hash"] = strategy_hash
                frames.append(ledger)
                ledger_cache[(quarter, strategy_hash, multiplier)] = ledger.drop(columns=["strategy_hash"])
            pd.concat(frames, ignore_index=True).to_parquet(cache_path, index=False)
            checkpoint["completed_quarters"].append(key)
            checkpoint_path.write_text(json.dumps(checkpoint, sort_keys=True, indent=2) + "\n")

    result_rows = []
    for composition in compositions:
        portfolio_id = str(composition["portfolio_id"])
        for quarter in config["quarters"]:
            for cost_name, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
                ledgers = [(h, ledger_cache[(quarter, h, multiplier)]) for h in composition["selected"]]
                portfolio = portfolio_ledger(ledgers, risk_per_trade=config["evaluation"]["risk_per_trade"], max_aggregate_risk=config["evaluation"]["max_aggregate_risk"])
                metrics = extended_portfolio_metrics(portfolio)
                result_rows.append({"portfolio_id": portfolio_id, "quarter": quarter, "cost": cost_name, **metrics})
    results = pd.DataFrame(result_rows)
    results.to_csv(OUT / "portfolio_results.csv", index=False)
    summary = cumulative_summary(results)
    summary.to_csv(OUT / "portfolio_distributions.csv", index=False)

    original_loo = []
    for removed in original:
        selected = [h for h in original if h != removed]
        for cost_name, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
            rows = []
            for quarter in config["quarters"]:
                ledgers = [(h, ledger_cache[(quarter, h, multiplier)]) for h in selected]
                metrics = extended_portfolio_metrics(portfolio_ledger(ledgers, risk_per_trade=config["evaluation"]["risk_per_trade"], max_aggregate_risk=config["evaluation"]["max_aggregate_risk"]))
                rows.append({"quarter": quarter, **metrics})
            frame = pd.DataFrame(rows)
            curve = np.cumprod(1 + frame["return"].to_numpy(float))
            original_loo.append({"removed_strategy_hash": removed, "cost": cost_name, "cumulative_return": float(curve[-1] - 1), "max_drawdown": float((1 - curve / np.maximum.accumulate(curve)).max()), "n_trades": int(frame.n_trades.sum())})
    pd.DataFrame(original_loo).to_csv(OUT / "original_leave_one_out.csv", index=False)

    formal = p12d[p12d.quarter.isin(config["quarters"])].copy()
    formal["eligible"] = formal.strategy_hash.isin(eligible)
    individual_rows = []
    for quarter, frame in formal.groupby("quarter", sort=True):
        for label, part in (("eligible", frame[frame.eligible]), ("noneligible", frame[~frame.eligible]), ("full", frame)):
            for cost in ("forward", "forward_x2"):
                active = part[f"{cost}_n_trades"] > 0
                individual_rows.append({"quarter": quarter, "group": label, "cost": cost, "n": len(part), "active_pct": float(active.mean()), "positive_return_pct": float((active & (part[f"{cost}_return"] > 0)).mean()), "positive_expectancy_pct": float((active & (part[f"{cost}_expectancy_R"] > 0)).mean()), "mean_expectancy_R": float(part[f"{cost}_expectancy_R"].mean()), "mean_return": float(part[f"{cost}_return"].mean()), "median_return": float(part[f"{cost}_return"].median()), "median_finite_pf": float(part[f"{cost}_profit_factor"].replace([np.inf, -np.inf], np.nan).median()), "mean_max_drawdown": float(part[f"{cost}_max_drawdown"].mean())})
    pd.DataFrame(individual_rows).to_csv(OUT / "individual_comparison.csv", index=False)

    signatures = formal[formal.eligible].assign(signature=formal.loc[formal.eligible, ["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"]].astype(str).agg("|".join, axis=1))
    dependence = signatures.groupby("quarter", as_index=False).agg(eligible_rows=("strategy_hash", "size"), unique_signatures=("signature", "nunique"), largest_signature=("signature", lambda x: int(x.value_counts().iloc[0])))
    dependence["duplicate_rows"] = dependence.eligible_rows - dependence.unique_signatures
    dependence.to_csv(OUT / "behavioral_dependence.csv", index=False)
    manifest = {"policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "archive_sha256": file_sha256(ARCHIVE), "p12d_sha256": file_sha256(P12D), "eligible_n": len(eligible), "eligible_pct": len(eligible) / 100000, "portfolios": n_portfolios, "portfolio_size": portfolio_size, "portfolio_rows": len(results), "holdout_used": False, "elapsed_seconds": time.perf_counter() - started}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
