"""Summarize the frozen P12D.1 historical selection-power experiment."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports/p12d_1_artifacts"


def cumulative(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for (group, replicate), part in frame.groupby(["group", "replicate"], sort=True):
        part = part.sort_values("quarter")
        returns = part[f"{label}_return"].to_numpy(float)
        curve = (1 + returns).cumprod()
        peaks = np.maximum.accumulate(curve)
        rows.append({"group": group, "replicate": replicate, "cumulative_return": float(curve[-1] - 1), "quarterly_mean_return": float(returns.mean()), "quarterly_positive_fraction": float((returns > 0).mean()), "max_drawdown": float((1 - curve / peaks).max()), "mean_profit_factor": float(part[f"{label}_profit_factor"].replace([float("inf"), -float("inf")], float("nan")).mean())})
    return pd.DataFrame(rows)


def main() -> None:
    individual = pd.read_csv(ART / "formal_individual_by_rule.csv")
    portfolios = pd.read_csv(ART / "portfolio_results.csv")
    trial = pd.read_csv(ART / "rule_trials_2017.csv")
    formal_rules = ["train_pf_105_n100", "train_pf105_n100_long", "train_pf105_n100_short"]
    summary_rows = []
    for rule in ["full_population", "original_pass_benchmark", *formal_rules]:
        for cost, suffix in [("forward", "baseline"), ("forward_x2", "costs_x2")]:
            part = individual[(individual.rule_id == rule) & (individual.cost == cost)]
            summary_rows.append({"rule_id": rule, "scenario": suffix, "observations": int(part.n.sum()), "mean_return": float(part.mean_return.mean()), "mean_expectancy_R": float(part.mean_expectancy_R.mean()), "positive_return_pct_mean": float(part.positive_return_pct.mean()), "median_finite_PF_mean": float(part.median_finite_profit_factor.mean()), "mean_max_drawdown": float(part.mean_max_drawdown.mean())})
    pd.DataFrame(summary_rows).to_csv(ART / "formal_individual_summary.csv", index=False)
    base = cumulative(portfolios, "baseline")
    x2 = cumulative(portfolios, "costs_x2")
    base.to_csv(ART / "portfolio_cumulative_baseline.csv", index=False)
    x2.to_csv(ART / "portfolio_cumulative_costs_x2.csv", index=False)
    comparison = []
    for rule in formal_rules:
        actual = base[base.group == f"{rule}_portfolio"].iloc[0]
        controls = base[base.group == f"{rule}_random_control"]
        actual_x2 = x2[x2.group == f"{rule}_portfolio"].iloc[0]
        controls_x2 = x2[x2.group == f"{rule}_random_control"]
        comparison.append({"rule_id": rule, "actual_baseline_cumulative_return": actual.cumulative_return, "control_baseline_mean": controls.cumulative_return.mean(), "control_baseline_fraction_beating_actual": (controls.cumulative_return > actual.cumulative_return).mean(), "actual_costs_x2_cumulative_return": actual_x2.cumulative_return, "control_costs_x2_mean": controls_x2.cumulative_return.mean(), "control_costs_x2_fraction_beating_actual": (controls_x2.cumulative_return > actual_x2.cumulative_return).mean()})
    comparison_frame = pd.DataFrame(comparison)
    comparison_frame.to_csv(ART / "control_comparison.csv", index=False)
    trial_table = trial[["rule_id", "n", "mean_return", "mean_expectancy_R", "positive_return_pct", "mean_R_per_trade"]].to_string(index=False)
    formal_table = pd.DataFrame(summary_rows).to_string(index=False, float_format=lambda value: f"{value:.6f}")
    portfolio_table = comparison_frame.to_string(index=False, float_format=lambda value: f"{value:.6f}")
    report = ["# P12D.1 — Historical Selection Power Audit", "", "## Scope and causal boundary", "", "This is an exploratory audit of the exact 100,000-strategy P08 Q1 population using the 900,000 P12D rows. Rule discovery used 2017Q1–2017Q4 only. Formal evaluation used fixed rules over 2018Q1–2019Q1. This is not an independent validation: 2018–2019 was already inspected in P12A–P12D.", "", "The protocol was frozen before formal evaluation. PASS is retained only as a retrospective benchmark because its original decision used later development information; it is not a causal candidate rule.", "", "## Historical variables audit", "", "Available before forward evaluation: training number of trades, expectancy R, profit factor, return, MaxDD, maximum loss streak, direction, predicate count/complexity, and original PASS/FAIL decision. Per-year training regularity and an independent exposure series were not archived. Forward behavior signatures, forward activity and all forward metrics were excluded as predictors.", "", "## Rules tested during discovery", "", "All 11 definitions and their 2017 results are in `rule_trials_2017.csv`. No identifier-based rule or forward signature was tested.", "", "```text", trial_table, "```", "", "## Formal individual results", "", "The complete table is in `formal_individual_by_rule.csv`; percentages are population fractions, not economic portfolio returns.", "", "```text", formal_table, "```", "", "## Formal portfolios and controls", "", "Each frozen group used one deterministic five-strategy portfolio. Each formal rule also has 100 uniform, without-replacement controls of five strategies from the same historical-activity base (`training_n_trades >= 100`). The original execution engine, 0.5% risk per trade and 2.5% aggregate risk cap were used; portfolios were built from actual rich ledgers, not aggregate statistics.", "", "```text", portfolio_table, "```", "", "Cumulative returns compound the five chronological quarterly portfolio returns. They are not sums of individual strategy returns. Full portfolio details are in `portfolio_results.csv` and cumulative controls in the accompanying CSV files.", "", "## Answers", "", "1. Retrospectively favorable subpopulations exist descriptively: the original PASS group and some 2017 rule groups show higher positive fractions, but this does not establish a usable rule.", "2. Historical training variables identify differences in population distributions, but the formal rules do not produce a robust positive portfolio. The PF/activity/direction rules were not sufficient.", "3. No formal rule maintained favorable results across all five quarters. The aggregate `train_pf_105_n100` portfolio was positive baseline, but costs ×2 were positive only weakly and its quarter-to-quarter behavior was not stable.", "4. The rule portfolios outperformed the matched random controls in the recorded comparison, but controls remained negative on average and this does not demonstrate edge; the comparison is conditional on one frozen five-strategy sample and shared market data.", "5. No new-rule portfolio provides evidence of stable positive net profitability after costs. The original PASS benchmark also had negative cumulative portfolio performance under this fixed sample.", "", "## Dependence and limitations", "", "Strategies share the same GA, market, indicators and execution process. Positive percentages are not independent evidence, and the five-strategy portfolios are sensitive to overlap and path dependence. The experiment does not estimate an unbiased discovery-to-validation performance because the 2018–2019 period has already been inspected in prior phases. No thresholds were changed after formal results.", "", "## Conclusion", "", "Historical statistics can describe subpopulation differences, but this experiment does not justify a new acceptance policy or Factory V2. No strategies were modified, no GA was rerun, no holdout data was opened, and no real operations were performed."]
    (ROOT / "reports/p12d_1_selection_power_audit.md").write_text("\n".join(report) + "\n")
    (ART / "summary.json").write_text(json.dumps({"strategies": 100000, "discovery_quarters": 4, "formal_quarters": 5, "rules_tested": 11, "formal_rules": formal_rules, "holdout_used": False}, indent=2) + "\n")


if __name__ == "__main__":
    main()
