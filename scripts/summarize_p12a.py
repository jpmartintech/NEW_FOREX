"""Create reproducible P12A census summaries from the frozen Parquet result."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports/p12a_artifacts"


def main() -> None:
    data = pd.read_parquet(ART / "full_forward_census.parquet")
    data["forward_positive_expectancy"] = data.forward_expectancy_R > 0
    data["forward_positive_return"] = data.forward_return > 0
    data["forward_pf_finite"] = np.isfinite(data.forward_profit_factor)
    data["forward_pf_valid"] = data.forward_n_trades > 0
    comparison = (data.groupby("original_filter_decision", dropna=False)
                  .agg(n=("strategy_hash", "size"), mean_forward_expectancy_R=("forward_expectancy_R", "mean"),
                       median_forward_expectancy_R=("forward_expectancy_R", "median"),
                       positive_expectancy_fraction=("forward_positive_expectancy", "mean"),
                       positive_return_fraction=("forward_positive_return", "mean"),
                       mean_forward_return=("forward_return", "mean"), median_forward_return=("forward_return", "median"),
                       mean_forward_trades=("forward_n_trades", "mean"), zero_trade_fraction=("forward_n_trades", lambda x: (x == 0).mean()),
                       finite_pf_fraction=("forward_pf_finite", "mean"), valid_pf_fraction=("forward_pf_valid", "mean"))
                  .reset_index())
    comparison.to_csv(ART / "accepted_vs_rejected.csv", index=False)
    cols = ["archive_fitness", "training_expectancy_R", "development_expectancy_R", "development_profit_factor",
            "development_n_trades"]
    quantiles = []
    for column in cols:
        work = data[[column, "forward_expectancy_R", "forward_return", "forward_n_trades", "forward_positive_expectancy"]].copy()
        finite = np.isfinite(work[column])
        work = work[finite].copy()
        work["bucket"] = pd.qcut(work[column].rank(method="first"), 10, labels=False) + 1
        grouped = work.groupby("bucket", observed=True).agg(n=(column, "size"), source_median=(column, "median"),
            forward_expectancy_R=("forward_expectancy_R", "mean"), forward_return=("forward_return", "mean"),
            forward_positive_fraction=("forward_positive_expectancy", "mean"), mean_forward_trades=("forward_n_trades", "mean"))
        grouped.insert(0, "source_metric", column)
        grouped.insert(1, "decile", grouped.index)
        quantiles.append(grouped.reset_index(drop=True))
    pd.concat(quantiles, ignore_index=True).to_csv(ART / "historical_metric_deciles.csv", index=False)
    operation_buckets = pd.cut(data.forward_n_trades, [-1, 0, 5, 20, 50, 100, np.inf],
                                labels=["0", "1-5", "6-20", "21-50", "51-100", ">100"])
    ops = data.assign(operation_bucket=operation_buckets).groupby("operation_bucket", observed=False).agg(
        n=("strategy_hash", "size"), positive_expectancy_fraction=("forward_positive_expectancy", "mean"),
        mean_expectancy_R=("forward_expectancy_R", "mean"), mean_return=("forward_return", "mean"),
        median_return=("forward_return", "median"), mean_max_drawdown=("forward_max_drawdown", "mean")).reset_index()
    ops.to_csv(ART / "operation_buckets.csv", index=False)
    corr_cols = ["archive_fitness", "training_expectancy_R", "development_expectancy_R", "development_profit_factor",
                 "development_n_trades", "forward_n_trades", "forward_expectancy_R", "forward_return"]
    data[corr_cols].replace([np.inf, -np.inf], np.nan).corr()["forward_expectancy_R"].to_csv(ART / "correlations_with_forward_expectancy.csv")
    signature = data.groupby(["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"], dropna=False).size()
    signature_counts = signature.sort_values(ascending=False)
    (ART / "behavioral_dependence.json").write_text(json.dumps({
        "strategies": len(data), "unique_strategy_payloads": int(data.strategy_payload.nunique()),
        "unique_forward_signatures": int(len(signature)), "duplicate_signature_rows": int(len(data) - len(signature)),
        "largest_signature_multiplicity": int(signature_counts.iloc[0]),
        "top_signatures": [{"signature": list(map(float, key if isinstance(key, tuple) else [key])), "multiplicity": int(value)}
                           for key, value in signature_counts.head(10).items()]
    }, indent=2) + "\n")
    summary = {"n_strategies": len(data), "accepted": int((data.original_filter_decision == "PASS").sum()),
               "rejected": int((data.original_filter_decision == "FAIL").sum()),
               "zero_forward_trades": int((data.forward_n_trades == 0).sum()),
               "positive_forward_expectancy": int(data.forward_positive_expectancy.sum()),
               "positive_forward_return": int(data.forward_positive_return.sum()),
               "infinite_forward_pf": int(np.isinf(data.forward_profit_factor).sum()),
               "mean_forward_expectancy_R": float(data.forward_expectancy_R.mean()),
               "median_forward_expectancy_R": float(data.forward_expectancy_R.median()),
               "mean_forward_return": float(data.forward_return.mean()), "median_forward_return": float(data.forward_return.median()),
               "mean_forward_x2_expectancy_R": float(data.forward_x2_expectancy_R.mean()),
               "mean_forward_trades": float(data.forward_n_trades.mean())}
    (ART / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
