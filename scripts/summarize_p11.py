"""Summarize completed P11 Control A results without touching market data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports/p11_artifacts"


def trade_metrics(frames: list[pd.DataFrame]) -> dict:
    trades = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    r = trades["result_R"].astype(float) if not trades.empty else pd.Series(dtype=float)
    losses = -r[r < 0].sum()
    wins = r[r > 0].sum()
    gross = (r + trades["transaction_cost"] / trades["risk"].replace(0, np.nan)).sum() if not trades.empty else 0.0
    return {"n_trades": int(len(r)), "expectancy_R": float(r.mean()) if len(r) else 0.0,
            "profit_factor": None if not len(r) else (float(wins / losses) if losses else (float("inf") if wins > 0 else 0.0)),
            "net_R": float(r.sum()), "gross_R": float(gross)}


def main() -> None:
    results = [json.loads(line) for line in (ART / "random_selection_results.jsonl").open()]
    by_generation = {}
    for label in sorted({row["generation"] for row in results}):
        cached = pd.read_parquet(ART / f"ledgers_{label}.parquet")
        by_generation[label] = {(scenario, h): frame for (scenario, h), frame in cached.groupby(["scenario", "strategy_hash"], sort=False)}
    rows = []
    for row in results:
        out = {"generation": row["generation"], "replicate": row["replicate"], "seed": row["seed"]}
        for scenario in ("baseline", "costs_x2"):
            frames = [by_generation[row["generation"]].get((scenario, h), pd.DataFrame(columns=["result_R", "transaction_cost", "risk"]))
                      for h in row["selected"]]
            out[scenario] = {**row[scenario], **trade_metrics(frames)}
        rows.append(out)
    flat = []
    for row in rows:
        for scenario in ("baseline", "costs_x2"):
            flat.append({"generation": row["generation"], "replicate": row["replicate"], "seed": row["seed"],
                         "scenario": scenario, **row[scenario]})
    flat_df = pd.DataFrame(flat)
    flat_df.to_csv(ART / "control_metrics.csv", index=False)
    gen_summary = (flat_df.groupby(["generation", "scenario"])
                   .agg(replicates=("replicate", "size"), mean_return=("return", "mean"),
                        median_return=("return", "median"), mean_expectancy_R=("expectancy_R", "mean"),
                        mean_profit_factor=("profit_factor", "mean"), mean_max_drawdown=("max_drawdown", "mean"),
                        median_max_drawdown=("max_drawdown", "median"), mean_net_R=("net_R", "mean"),
                        mean_gross_R=("gross_R", "mean"))
                   .reset_index())
    gen_summary.to_csv(ART / "control_by_generation.csv", index=False)
    rolling = [json.loads(line) for line in (ART / "rolling_trajectories.jsonl").open()]
    rolling_df = pd.DataFrame([{**{"replicate": x["replicate"], "scenario": s}, **x[s]} for x in rolling for s in ("baseline", "costs_x2")])
    rolling_df.to_csv(ART / "rolling_summary.csv", index=False)
    real_gen = pd.read_csv(ROOT / "reports/p10_artifacts/generation_diagnostics.csv")
    comparisons = []
    for generation, group in flat_df[flat_df.scenario == "baseline"].groupby("generation"):
        real = real_gen[real_gen.label == generation].iloc[0]
        comparisons.append({"generation": generation, "real_return": real.portfolio_return,
                            "control_mean_return": group["return"].mean(), "control_median_return": group["return"].median(),
                            "control_fraction_beating_real": float((group["return"] > real.portfolio_return).mean()),
                            "real_max_drawdown": real.portfolio_max_drawdown,
                            "control_mean_max_drawdown": group.max_drawdown.mean()})
    pd.DataFrame(comparisons).to_csv(ART / "comparison_by_generation.csv", index=False)
    real = {"return": -0.16989758559123935, "max_drawdown": 0.29149734017067674}
    unique_evaluations = sum(pd.read_parquet(ART / f"ledgers_{label}.parquet").strategy_hash.nunique()
                             for label in sorted(by_generation))
    rolling_base = rolling_df[rolling_df.scenario == "baseline"]
    rolling_x2 = rolling_df[rolling_df.scenario == "costs_x2"]
    summary = {"n_control_portfolios": len(results), "n_rolling_trajectories": len(rolling),
               "sampled_strategy_forward_slots": 8000, "unique_strategy_forward_evaluations": unique_evaluations,
               "real": real,
               "control_baseline": {"mean_return": float(flat_df[flat_df.scenario == "baseline"]["return"].mean()),
                                    "median_return": float(flat_df[flat_df.scenario == "baseline"]["return"].median()),
                                    "fraction_beating_real": float((flat_df[flat_df.scenario == "baseline"]["return"] > real["return"]).mean()),
                                    "real_rolling_percentile": float((rolling_base["return"] < real["return"]).mean() * 100),
                                    "mean_max_drawdown": float(flat_df[flat_df.scenario == "baseline"].max_drawdown.mean())},
               "control_costs_x2": {"mean_return": float(flat_df[flat_df.scenario == "costs_x2"]["return"].mean()),
                                    "median_return": float(flat_df[flat_df.scenario == "costs_x2"]["return"].median()),
                                    "fraction_beating_real": float((flat_df[flat_df.scenario == "costs_x2"]["return"] > -0.2875914285608481).mean()),
                                    "real_rolling_percentile": float((rolling_x2["return"] < -0.2875914285608481).mean() * 100),
                                    "mean_max_drawdown": float(flat_df[flat_df.scenario == "costs_x2"].max_drawdown.mean())}}
    (ART / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    manifest = json.loads((ART / "manifest.json").read_text())
    manifest["sampled_strategy_forward_slots"] = 8000
    manifest["unique_strategy_forward_evaluations"] = unique_evaluations
    manifest["summary_sha256"] = hashlib.sha256((ART / "summary.json").read_bytes()).hexdigest()
    (ART / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
