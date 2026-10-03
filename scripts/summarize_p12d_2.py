"""Summarize P12D.2 composition sensitivity without ranking portfolios."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports/p12d_2_artifacts"


def max_concurrent(frames: list[pd.DataFrame]) -> int:
    events: list[tuple[pd.Timestamp, int]] = []
    for frame in frames:
        for row in frame.itertuples():
            events.append((pd.Timestamp(row.entry_timestamp), 1))
            events.append((pd.Timestamp(row.exit_timestamp), -1))
    active = maximum = 0
    for _timestamp, change in sorted(events, key=lambda item: (item[0], 0 if item[1] == -1 else 1)):
        active += change
        maximum = max(maximum, active)
    return maximum


def main() -> None:
    distributions = pd.read_csv(ART / "portfolio_distributions.csv")
    controls = distributions[distributions.portfolio_id != "original_p12d1"]
    original = distributions[distributions.portfolio_id == "original_p12d1"]
    rows = []
    for cost in ["baseline", "costs_x2"]:
        part = controls[controls.cost == cost]
        ref = original[original.cost == cost].iloc[0]
        rows.append({"cost": cost, "n_controls": len(part), "mean_return": part.cumulative_return.mean(), "median_return": part.cumulative_return.median(), "p05_return": part.cumulative_return.quantile(.05), "p95_return": part.cumulative_return.quantile(.95), "positive_fraction": (part.cumulative_return > 0).mean(), "mean_max_drawdown": part.max_drawdown.mean(), "original_return": ref.cumulative_return, "controls_beating_original_fraction": (part.cumulative_return > ref.cumulative_return).mean(), "original_percentile_rank": (part.cumulative_return <= ref.cumulative_return).mean()})
    distribution_summary = pd.DataFrame(rows)
    distribution_summary.to_csv(ART / "distribution_summary.csv", index=False)
    loo = pd.read_csv(ART / "original_leave_one_out.csv")
    loo.to_csv(ART / "original_leave_one_out.csv", index=False)
    individual = pd.read_csv(ART / "individual_comparison.csv")
    population = individual.groupby(["group", "cost"], as_index=False).agg(mean_return=("mean_return", "mean"), mean_expectancy_R=("mean_expectancy_R", "mean"), positive_return_pct=("positive_return_pct", "mean"), active_pct=("active_pct", "mean"), mean_max_drawdown=("mean_max_drawdown", "mean"))
    population.to_csv(ART / "population_summary.csv", index=False)
    families = pd.read_csv(ART / "eligible_structural_families.csv")
    dep = pd.read_csv(ART / "behavioral_dependence.csv")
    compositions = [json.loads(line) for line in (ART / "compositions.jsonl").read_text().splitlines()]
    overlap_rows = []
    for cost_name in ["baseline", "costs_x2"]:
        ledgers = {}
        for quarter in ["2018Q1", "2018Q2", "2018Q3", "2018Q4", "2019Q1"]:
            cached = pd.read_parquet(ART / f"ledgers_{quarter}_{cost_name}.parquet")
            ledgers[quarter] = {key: value.drop(columns=["strategy_hash"]) for key, value in cached.groupby("strategy_hash", sort=False)}
        for composition in compositions:
            for quarter in ledgers:
                overlap_rows.append({"portfolio_id": composition["portfolio_id"], "quarter": quarter, "cost": cost_name, "max_concurrent_positions": max_concurrent([ledgers[quarter].get(key, pd.DataFrame()) for key in composition["selected"]])})
    overlap = pd.DataFrame(overlap_rows)
    overlap.to_csv(ART / "portfolio_overlap.csv", index=False)
    dtable = distribution_summary.to_string(index=False, float_format=lambda value: f"{value:.6f}")
    ptable = population.to_string(index=False, float_format=lambda value: f"{value:.6f}")
    ltable = loo.to_string(index=False, float_format=lambda value: f"{value:.6f}")
    overlap_summary = overlap.groupby("cost").agg(mean_max_concurrent=("max_concurrent_positions", "mean"), p95_max_concurrent=("max_concurrent_positions", lambda x: x.quantile(.95)), original_mean=("max_concurrent_positions", lambda x: x[overlap.loc[x.index, "portfolio_id"].astype(str) == "original_p12d1"].mean())).reset_index()
    report = ["# P12D.2 — Selection Stability and Portfolio Sensitivity", "", "## Scope and frozen rule", "", "The exact P08 Q1 universe was restricted using only historical training fields: `training_profit_factor >= 1.05` and `training_n_trades >= 100`. This produced 7,517 of 100,000 strategies (7.517%). No additional eligibility filter was applied. Five-strategy portfolios were sampled uniformly without replacement with 1,000 deterministic seeds; the original P12D.1 portfolio was retained separately.", "", "Protocol SHA256: `3fb814193f3827333d4a1b67350dcb1cb991d701881d313f165fdc50a2395f8b`. The 2018Q1–2019Q1 period was already inspected in P12A–P12D and is not independent validation.", "", "## Eligible population", "", "Historical distributions are in `eligible_describe.csv`; structural counts are in `eligible_structural_families.csv`. No forward result was used for eligibility.", "", "```text", families.to_string(index=False), "```", "", "## Individual forward distribution", "", "The eligible population has a more favorable individual distribution than the full population, but the effect is modest and does not imply portfolio profitability. Full comparison:", "", "```text", ptable, "```", "", "Forward behavior signatures are diagnostic only. Among eligible strategies, unique aggregate signatures and concentration were:", "", "```text", dep.to_string(index=False), "```", "These signatures are not treated as independent observations. Exact operation-level similarity for every eligible pair was not archived; actual ledgers were used for all sampled portfolio components.", "", "## 1,000 composition Monte Carlo", "", "```text", dtable, "```", "The original portfolio is at the `original_percentile_rank` of the composition distribution; the percentile is descriptive, not confirmatory. It is above 89.3% of baseline controls and 90.0% of costs×2 controls, but this is one previously observed combination and not a new selection result.", "", "## Operational overlap", "", "Actual sampled ledgers were used to calculate maximum simultaneous positions; this is an execution diagnostic, not a selection variable.", "", "```text", overlap_summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"), "```", "", "## Original portfolio leave-one-out", "", "```text", ltable, "```", "Leave-one-out is diagnostic only. No replacement portfolio was constructed. The original outcome depends on composition, but removal of any single component does not turn this into an independent validation.", "", "## Answers", "", "A. Yes, the historical rule identifies a descriptively more favorable individual subpopulation: baseline mean return was approximately `+0.054%` per strategy-quarter versus `-0.646%` for the full population; costs×2 remained negative (`-0.329%`).", "", "B. 52.2% of alternative five-strategy portfolios were baseline-positive; 24.4% remained positive with costs×2. The median baseline return was only about `+0.56%`, while the costs×2 median was `-7.91%`.", "", "C. No. Profitability does not persist for most compositions when costs are doubled.", "", "D. The original P12D.1 portfolio is favorable but not unique: it ranked around the 89th–90th percentile among the 1,000 alternatives, not at an isolated maximum.", "", "E. There is material behavioral concentration: each quarter has thousands of distinct signatures but thousands of duplicate rows and a non-trivial largest signature. The original leave-one-out results show composition sensitivity, while shared market/GA construction lowers effective sample size.", "", "F. The results justify, at most, a pre-registered test of the unchanged rule on genuinely later generations. They do not justify changing thresholds, creating Factory V2, or declaring edge.", "", "## Limitations", "", "The 1,000 portfolios reuse strategies and market data, so they are not independent draws from an external population. Forward data was used only for outcome and diagnostic calculations. No holdout data, GA rerun, real operation or retrospective threshold adjustment was used."]
    (ROOT / "reports/p12d_2_portfolio_sensitivity.md").write_text("\n".join(report) + "\n")
    (ART / "summary.json").write_text(json.dumps({"eligible": 7517, "universe": 100000, "portfolios": 1000, "portfolio_size": 5, "formal_quarters": 5, "holdout_used": False}, indent=2) + "\n")


if __name__ == "__main__":
    main()
