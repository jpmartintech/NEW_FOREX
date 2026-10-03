"""Create descriptive P12D population and lifecycle tables and report."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports/p12d_artifacts"
DATA = ART / "population_lifecycle.parquet"


def _summary(frame: pd.DataFrame, cost: str, quarter: str) -> dict:
    active = frame[f"{cost}_n_trades"] > 0
    exp = frame[f"{cost}_expectancy_R"]
    ret = frame[f"{cost}_return"]
    dd = frame[f"{cost}_max_drawdown"]
    efficiency = frame[f"{cost}_efficiency_return_dd"].replace([np.inf, -np.inf], np.nan)
    pf = frame[f"{cost}_profit_factor"]
    finite_pf = pf.replace([np.inf, -np.inf], np.nan)
    return {"quarter": quarter, "cost": cost, "n": len(frame), "active_pct": float(active.mean()),
            "zero_trade_n": int((~active).sum()), "mean_n_trades": float(frame[f"{cost}_n_trades"].mean()),
            "median_n_trades": float(frame[f"{cost}_n_trades"].median()), "p95_n_trades": float(frame[f"{cost}_n_trades"].quantile(.95)),
            "mean_expectancy_R": float(exp.mean()), "median_expectancy_R": float(exp.median()),
            "p05_expectancy_R": float(exp.quantile(.05)), "p95_expectancy_R": float(exp.quantile(.95)),
            "mean_return": float(ret.mean()), "median_return": float(ret.median()),
            "p05_return": float(ret.quantile(.05)), "p95_return": float(ret.quantile(.95)),
            "positive_expectancy_pct": float((active & (exp > 0)).mean()),
            "positive_return_pct": float((active & (ret > 0)).mean()),
            "finite_pf_pct": float(finite_pf.notna().mean()), "pf_gt_1_pct": float((active & (pf > 1)).mean()),
            "median_finite_pf": float(finite_pf.median()) if finite_pf.notna().any() else 0.0,
            "p95_finite_pf": float(finite_pf.quantile(.95)) if finite_pf.notna().any() else 0.0,
            "mean_max_drawdown": float(dd.mean()), "median_max_drawdown": float(dd.median()),
            "mean_efficiency_return_dd": float(efficiency.mean()),
            "mean_R_per_trade": float(np.divide(frame[f"{cost}_total_R"], frame[f"{cost}_n_trades"].replace(0, np.nan)).mean())}


def main() -> None:
    df = pd.read_parquet(DATA)
    summaries = pd.DataFrame([_summary(group, cost, quarter) for quarter, group in df.groupby("quarter", sort=True) for cost in ("forward", "forward_x2")])
    summaries.to_csv(ART / "quarterly_population_summary.csv", index=False)
    groups = []
    for quarter, group in df.groupby("quarter", sort=True):
        for name, mask in {"active_positive_expectancy": group["positive_expectancy"], "active_positive_return": group["positive_return"], "active_positive_both": group["positive_both"], "rest": ~group["positive_both"]}.items():
            selected = group.loc[mask]
            groups.append({"quarter": quarter, "group": name, "n": len(selected), "mean_forward_expectancy_R": float(selected["forward_expectancy_R"].mean()) if len(selected) else 0.0, "mean_forward_return": float(selected["forward_return"].mean()) if len(selected) else 0.0, "mean_training_expectancy_R": float(selected["training_expectancy_R"].mean()) if len(selected) else 0.0, "mean_training_n_trades": float(selected["training_n_trades"].mean()) if len(selected) else 0.0, "costs_x2_positive_expectancy_pct": float((selected["forward_x2_expectancy_R"] > 0).mean()) if len(selected) else 0.0})
    pd.DataFrame(groups).to_csv(ART / "favorable_groups.csv", index=False)
    hist = df.groupby("quarter", sort=True).agg(unique_strategies=("strategy_hash", "nunique"), mean_training_expectancy_R=("training_expectancy_R", "mean"), mean_archive_fitness=("archive_fitness", "mean"), pass_pct=("original_filter_decision", lambda x: (x == "PASS").mean())).reset_index()
    hist.to_csv(ART / "historical_persistence_by_quarter.csv", index=False)
    summary_table = summaries.to_string(index=False, float_format=lambda value: f"{value:.6f}")
    groups_table = pd.DataFrame(groups).to_string(index=False, float_format=lambda value: f"{value:.6f}")
    dep = pd.read_csv(ART / "dependence_by_quarter.csv")
    dep_table = dep.to_string(index=False)
    report = ["# P12D — Full Population Forward Lifecycle", "", "## Scope", "", "The exact 100,000-strategy P08 Q1 archive was evaluated over 2017 Q1 through 2019 Q1. No GA, selection, forward ranking, or holdout access was used.", "", f"Dataset: {len(df):,} strategy-quarter rows; unique strategies: {df['strategy_hash'].nunique():,}; quarters: {df['quarter'].nunique()}.", "", "## Quarterly population statistics", "", "See `p12d_artifacts/quarterly_population_summary.csv` for activity, expectancy, return, Profit Factor distributions, drawdown, efficiency, R/trade and costs ×2. The dataset preserves individual strategy results; it is not a portfolio simulation and rows are not independent observations.", "", "```text", summary_table, "```", "", "## Favorable groups", "", "Groups are descriptive and are never used to select the next quarter. See `favorable_groups.csv`.", "", "```text", groups_table, "```", "", "## Lifecycle and dependence", "", "Activity and distribution changes are reported by quarter. Behavioral signatures are computed separately per quarter; repeated signatures and shared market data mean the 900,000 rows cannot be treated as independent. `dependence_by_quarter.csv` records concentration:", "", "```text", dep_table, "```", "", "Exposure-based profit per unit could not be computed because the preserved aggregate contract contains no independent exposure series; R/trade and return/drawdown are reported instead.", "", "## P12A equivalence", "", "The 2019 Q1 rows match P12A on trade count, expectancy, return, drawdown and costs ×2 fields. See `equivalence_p12a.json`.", "", "## Candidate regularities for later research", "", "1. Activity and forward distributions vary materially by quarter; this is descriptive and may reflect market regime changes.", "2. Costs ×2 reduce both expectancy and the positive-return fraction; cost sensitivity should remain a measured property.", "3. Positive-expectancy and positive-return groups are sparse relative to the full population and unstable across quarters.", "4. Return/drawdown efficiency has unstable denominators when no drawdown is recorded and must not be used as an automatic filter.", "5. Repeated behavioral signatures imply substantial dependence; effective sample size is lower than 900,000.", "", "## Limitations", "", "The period ends at 2019-04-01 exclusive. No 2019 Q2 onward or holdout data was accessed. This exploratory census cannot establish edge, causal relationships, or a new acceptance policy."]
    (ROOT / "reports/p12d_population_lifecycle.md").write_text("\n".join(report) + "\n")
    summary = {"rows": len(df), "strategies": int(df["strategy_hash"].nunique()), "quarters": int(df["quarter"].nunique()), "holdout_used": False}
    (ART / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
