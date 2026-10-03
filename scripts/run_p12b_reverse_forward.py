"""Build the exploratory P12B reverse-forward dataset from frozen P12A/P08 artifacts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from new_forex.provenance import file_sha256

ROOT = Path(__file__).resolve().parents[1]
P12A = ROOT / "reports/p12a_artifacts/full_forward_census.parquet"
AUDIT = ROOT / "runs/p08-rolling-2019-q1-v3/selection_audit.jsonl"
OUT = ROOT / "reports/p12b_artifacts"


def classify(n_trades: int, expectancy: float, return_: float) -> str:
    if n_trades == 0:
        return "A_no_forward_trades"
    if expectancy <= 0:
        return "B_active_nonpositive_expectancy"
    if return_ <= 0:
        return "C_positive_expectancy_nonpositive_return"
    return "D_positive_expectancy_and_return"


def metric(row: dict, name: str) -> float:
    return float(row.get(name, np.nan))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = pd.read_parquet(P12A)
    if len(data) != 100_000 or data.strategy_hash.duplicated().any():
        raise ValueError("P12A dataset is not exactly 100000 unique canonical strategies")
    historical = []
    with AUDIT.open() as handle:
        for line in handle:
            row = json.loads(line)
            strategy = row["strategy"]
            if not strategy:
                raise ValueError("missing historical strategy definition")
            train, dev, x2 = row.get("training", {}), row.get("aggregate", {}), row.get("costs_x2", {})
            checks = row.get("acceptance", {}).get("checks", {})
            eligible_for_years = all(checks.get(name, {}).get("status") == "PASS" for name in
                                     ("min_dev_wf_trades", "min_aggregate_expectancy_R", "min_profit_factor",
                                      "require_finite_profit_factor", "costs_x2_expectancy_R"))
            years = row.get("years", [{}, {}])
            historical.append({"strategy_hash": row["strategy_hash"], "direction": strategy["direction"],
                               "timeframe": strategy.get("timeframe"), "grammar_version": strategy.get("grammar_version"),
                               "n_predicates": len(strategy["predicates"]),
                               "n_unique_features": len({p["feature"] for p in strategy["predicates"]}),
                               "predicate_features": json.dumps(sorted(p["feature"] for p in strategy["predicates"])),
                               "sl_atr": strategy["sl_atr"], "tp_atr": strategy["tp_atr"], "max_bars": strategy["max_bars"],
                               "training_n_trades": train.get("n_trades", np.nan), "training_profit_factor": train.get("profit_factor", np.nan),
                               "training_expectancy_R": train.get("expectancy_R", np.nan), "training_return": train.get("return", np.nan),
                               "training_max_drawdown": train.get("max_drawdown", np.nan), "training_sharpe": train.get("sharpe", np.nan),
                               "training_max_loss_streak": train.get("max_loss_streak", np.nan),
                               "development_n_trades": dev.get("n_trades", np.nan), "development_profit_factor": dev.get("profit_factor", np.nan),
                               "development_expectancy_R": dev.get("expectancy_R", np.nan), "development_return": dev.get("return", np.nan),
                               "development_max_drawdown": dev.get("max_drawdown", np.nan), "development_sharpe": dev.get("sharpe", np.nan),
                               "development_max_loss_streak": dev.get("max_loss_streak", np.nan),
                               "development_x2_expectancy_R": x2.get("expectancy_R", np.nan),
                               "development_x2_return": x2.get("return", np.nan), "development_x2_max_drawdown": x2.get("max_drawdown", np.nan),
                               "historical_year_metrics_available": eligible_for_years,
                               "historical_year1_n_trades": years[0].get("n_trades", np.nan) if eligible_for_years else np.nan,
                               "historical_year2_n_trades": years[1].get("n_trades", np.nan) if eligible_for_years else np.nan,
                               "historical_positive_years": sum(y.get("n_trades", 0) > 0 and y.get("expectancy_R", 0) > 0 for y in years) if eligible_for_years else np.nan,
                               "historical_win_rate_available": False})
    hist = pd.DataFrame(historical)
    if len(hist) != len(data) or set(hist.strategy_hash) != set(data.strategy_hash):
        raise ValueError("P12A and historical audit identities do not match")
    combined = data.merge(hist, on="strategy_hash", how="left", validate="one_to_one", suffixes=("", "_audit"))
    combined = combined.drop(columns=[column for column in combined.columns if column.endswith("_audit")])
    combined["forward_class"] = [classify(int(n), float(e), float(r)) for n, e, r in
                                  zip(combined.forward_n_trades, combined.forward_expectancy_R, combined.forward_return, strict=True)]
    combined["forward_signature"] = combined[["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"]].astype(str).agg("|".join, axis=1)
    combined["strategy_family"] = combined.direction + "_p" + combined.n_predicates.astype(str) + "_" + combined.timeframe.astype(str)
    combined.to_parquet(OUT / "reverse_forward_dataset.parquet", index=False)
    group = combined.groupby("forward_class").agg(n=("strategy_hash", "size"), mean_forward_expectancy_R=("forward_expectancy_R", "mean"),
        median_forward_expectancy_R=("forward_expectancy_R", "median"), mean_forward_return=("forward_return", "mean"),
        median_forward_return=("forward_return", "median"), positive_costs_x2_expectancy=("forward_x2_expectancy_R", lambda x: (x > 0).mean()),
        mean_forward_trades=("forward_n_trades", "mean"), mean_development_expectancy_R=("development_expectancy_R", "mean"),
        mean_development_profit_factor=("development_profit_factor", "mean")).reset_index()
    group.to_csv(OUT / "forward_class_summary.csv", index=False)
    reasons = []
    for reason in sorted({item for value in combined.original_filter_failed_checks for item in json.loads(value)}):
        subset = combined[combined.original_filter_failed_checks.map(lambda x, reason=reason: reason in json.loads(x))]
        reasons.append({"rejection_reason": reason, "n": len(subset), "forward_positive_expectancy": (subset.forward_expectancy_R > 0).mean(),
                        "forward_positive_return": (subset.forward_return > 0).mean(), "mean_forward_return": subset.forward_return.mean(),
                        "mean_forward_x2_expectancy_R": subset.forward_x2_expectancy_R.mean()})
    pd.DataFrame(reasons).to_csv(OUT / "rejection_reason_summary.csv", index=False)
    combined.groupby("forward_signature").agg(n=("strategy_hash", "size"), mean_forward_return=("forward_return", "mean"),
        mean_forward_expectancy_R=("forward_expectancy_R", "mean"), mean_forward_trades=("forward_n_trades", "mean")).sort_values("n", ascending=False).head(1000).to_csv(OUT / "top_behavioral_groups.csv")
    family = combined.groupby("strategy_family").agg(n=("strategy_hash", "size"), positive_forward_expectancy=("forward_expectancy_R", lambda x: (x > 0).mean()),
        mean_forward_expectancy_R=("forward_expectancy_R", "mean"), mean_forward_return=("forward_return", "mean"), mean_forward_trades=("forward_n_trades", "mean")).reset_index()
    family.to_csv(OUT / "strategy_family_summary.csv", index=False)
    numerical = ["training_expectancy_R", "training_profit_factor", "training_n_trades", "training_max_drawdown",
                 "development_expectancy_R", "development_profit_factor", "development_n_trades", "development_max_drawdown",
                 "n_predicates", "n_unique_features", "max_bars", "sl_atr", "tp_atr", "forward_n_trades", "forward_expectancy_R", "forward_return"]
    combined[numerical].replace([np.inf, -np.inf], np.nan).corr()[["forward_expectancy_R", "forward_return"]].to_csv(OUT / "reverse_correlations.csv")
    manifest = {"dataset_sha256": file_sha256(OUT / "reverse_forward_dataset.parquet"), "source_p12a_sha256": file_sha256(P12A),
                "source_audit_sha256": file_sha256(AUDIT), "n_strategies": len(combined), "holdout_used": False,
                "historical_win_rate_available": False, "historical_year_metrics_available": int(combined.historical_year_metrics_available.sum())}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
