"""Summarize P12C temporal censuses and frozen portfolio controls."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports/p12c_artifacts"
LABELS = [p.name for p in sorted(ART.iterdir()) if p.is_dir() and (p / "part-000.parquet").exists()]


def read_generation(label: str) -> pd.DataFrame:
    return pd.concat((pd.read_parquet(p) for p in sorted((ART / label).glob("part-*.parquet"))), ignore_index=True)


def add_groups(frame: pd.DataFrame) -> pd.DataFrame:
    d = frame.copy()
    d["h1_activity"] = pd.cut(d.development_n_trades, [-1, 0, 5, 20, 50, 100, np.inf], labels=["0", "1-5", "6-20", "21-50", "51-100", ">100"])
    d["h2_development_positive"] = np.where(d.development_expectancy_R > 0, "development_exp_positive", "development_exp_nonpositive")
    d["h3_cost_robust"] = np.where(d.development_x2_expectancy_R > 0, "development_x2_positive", "development_x2_nonpositive")
    d["h4_direction_complexity"] = d.direction + np.where(d.n_predicates <= 2, "_1_2_predicates", "_3_4_predicates")
    d["h5_filter"] = d.original_filter_decision
    return d


def stats(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    return (frame.groupby(group_cols, observed=False, dropna=False).agg(n=("strategy_hash", "size"), active=("forward_n_trades", lambda x: (x > 0).sum()),
        positive_expectancy=("forward_expectancy_R", lambda x: (x > 0).mean()), positive_return=("forward_return", lambda x: (x > 0).mean()),
        mean_expectancy_R=("forward_expectancy_R", "mean"), median_expectancy_R=("forward_expectancy_R", "median"),
        mean_return=("forward_return", "mean"), median_return=("forward_return", "median"), mean_operations=("forward_n_trades", "mean"),
        mean_max_drawdown=("forward_max_drawdown", "mean"), costs_x2_positive_expectancy=("forward_x2_expectancy_R", lambda x: (x > 0).mean()),
        mean_costs_x2_expectancy_R=("forward_x2_expectancy_R", "mean")).reset_index())


def main() -> None:
    all_groups, real_rows, dep_rows = [], [], []
    for label in LABELS:
        data = add_groups(read_generation(label))
        data["generation"] = label
        all_groups.extend([stats(data, ["generation", "h1_activity"]).assign(hypothesis="H1_activity_moderate"),
                           stats(data, ["generation", "h2_development_positive"]).assign(hypothesis="H2_development_positive_insufficient"),
                           stats(data, ["generation", "h3_cost_robust"]).assign(hypothesis="H3_cost_robustness"),
                           stats(data, ["generation", "h4_direction_complexity"]).assign(hypothesis="H4_direction_complexity"),
                           stats(data, ["generation", "h5_filter"]).assign(hypothesis="H5_rejected_population")])
        for scenario in ("baseline", "costs_x2"):
            p = json.loads((ART / label / f"original_portfolio_{scenario}.json").read_text())
            real_rows.append({"generation": label, "scenario": scenario, **p})
        sig = data.groupby(["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"], dropna=False).size()
        dep_rows.append({"generation": label, "n_strategies": len(data), "unique_forward_signatures": len(sig),
                         "duplicate_rows": len(data) - len(sig), "largest_signature": int(sig.max())})
    pd.concat(all_groups, ignore_index=True).to_csv(ART / "hypothesis_by_generation.csv", index=False)
    pd.DataFrame(real_rows).to_csv(ART / "original_portfolio_by_generation.csv", index=False)
    pd.DataFrame(dep_rows).to_csv(ART / "dependence_by_generation.csv", index=False)
    random = [json.loads(line) for line in (ART / "random_control_results.jsonl").open()]
    random_rows = []
    real_df = pd.DataFrame(real_rows)
    for row in random:
        for scenario in ("baseline", "costs_x2"):
            real = real_df[(real_df.generation == row["generation"]) & (real_df.scenario == scenario)].iloc[0]
            random_rows.append({"generation": row["generation"], "replicate": row["replicate"], "scenario": scenario,
                                **row[scenario], "real_return": real["return"], "exceeds_real": row[scenario]["return"] > real["return"]})
    random_df = pd.DataFrame(random_rows)
    random_df.to_csv(ART / "random_control_by_generation.csv", index=False)
    random_summary = random_df.groupby(["generation", "scenario"]).agg(replicates=("replicate", "size"), mean_return=("return", "mean"),
        median_return=("return", "median"), mean_max_drawdown=("max_drawdown", "mean"), mean_operations=("n_trades", "mean"),
        fraction_exceeds_real=("exceeds_real", "mean")).reset_index()
    random_summary.to_csv(ART / "random_control_summary.csv", index=False)
    all_data = pd.concat((add_groups(read_generation(label)).assign(generation=label) for label in LABELS), ignore_index=True)
    overall = stats(all_data, ["h5_filter"])
    overall.to_csv(ART / "overall_pass_fail.csv", index=False)
    summary = {"generations": LABELS, "strategies": int(len(all_data)), "positive_forward_expectancy": int((all_data.forward_expectancy_R > 0).sum()),
               "mean_forward_return": float(all_data.forward_return.mean()), "random_control_portfolios": len(random),
               "original_portfolio_generations": len(real_df) // 2, "holdout_used": False,
               "max_forward_timestamp": "2022-12-31T23:59:59 exclusive"}
    (ART / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
