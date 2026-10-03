"""Reproduce and diagnose the frozen P08/P09 rolling portfolio (pre-holdout only)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "reports" / "p10_artifacts"
P09 = ROOT / "reports" / "p09_artifacts"


def metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    if frame.empty:
        return {"n_trades": 0, "expectancy_R": 0.0, "profit_factor": None, "return": 0.0,
                "max_drawdown": 0.0, "max_loss_streak": 0}
    r = frame["result_R"].astype(float)
    wins, losses = r[r > 0].sum(), -r[r < 0].sum()
    eq = (1 + 0.005 * r).cumprod()
    dd = 1 - eq / eq.cummax()
    signs = (r < 0).astype(int)
    streak = int(signs.groupby((signs != signs.shift()).cumsum()).sum().max())
    return {"n_trades": int(len(frame)), "expectancy_R": float(r.mean()),
            "profit_factor": None if losses == 0 and wins == 0 else (float("inf") if losses == 0 else float(wins / losses)),
            "return": float(eq.iloc[-1] - 1), "max_drawdown": float(dd.max()), "max_loss_streak": streak}


def generation_paths(label: str) -> tuple[Path, Path]:
    if label == "2019Q1":
        return ROOT / "runs/p08-rolling-2019-q1-v3", ROOT / "runs/p08-rolling-2019-q1-v3/ledgers"
    d = ROOT / "runs/p09-rolling-historical-v1" / label
    return d, d / "ledgers"


def read_forward(label: str, selected: list[str]) -> pd.DataFrame:
    _, ledgers = generation_paths(label)
    frames = []
    for h in selected:
        p = ledgers / f"{h}.forward.parquet"
        if not p.exists():
            raise FileNotFoundError(p)
        frames.append(pd.read_parquet(p))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def audit_rows(label: str) -> list[dict]:
    run, _ = generation_paths(label)
    with (run / "selection_audit.jsonl").open() as f:
        return [json.loads(line) for line in f]


def stable_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    generations = json.loads((P09 / "generation_results.json").read_text())
    rows = []
    all_ledgers: list[tuple[str, pd.DataFrame]] = []
    strategy_rows = []
    execution_rows = []
    horizon_rows = []
    quarter_rows = []
    for gen in generations:
        label, selected = gen["label"], gen["selected"]
        fwd = read_forward(label, selected)
        fwd["entry_timestamp"] = pd.to_datetime(fwd["entry_timestamp"], utc=True)
        fwd["exit_timestamp"] = pd.to_datetime(fwd["exit_timestamp"], utc=True)
        all_ledgers.extend((h, fwd[fwd.strategy_hash == h].copy()) for h in selected)
        m = metrics(fwd)
        pm = portfolio_ledger([(h, fwd[fwd.strategy_hash == h]) for h in selected])
        pmetrics = portfolio_metrics(pm)
        birth = pd.Timestamp(gen["birth"], tz="UTC")
        audit = {r["strategy_hash"]: r for r in audit_rows(label)}
        eligible = sum(r.get("acceptance", {}).get("decision") == "PASS" for r in audit.values())
        cost = float(fwd["transaction_cost"].mean()) if len(fwd) else 0.0
        rows.append({"label": label, "pilot": bool(gen.get("pilot", False)), "eligible_candidates": eligible,
                     "selected": len(selected), "forward_operations": len(fwd), **m,
                     "portfolio_return": pmetrics["return"], "portfolio_max_drawdown": pmetrics["max_drawdown"],
                     "mean_transaction_cost_price": cost, "portfolio_contribution": pmetrics["return"]})
        for h in selected:
            sf = fwd[fwd.strategy_hash == h].sort_values("exit_timestamp").copy()
            sm = metrics(sf)
            a = audit.get(h, {})
            strategy_rows.append({"generation": label, "strategy_hash": h, "forward": sm,
                                  "training": a.get("training", {}), "development": a.get("aggregate", {}),
                                  "forward_return": sm["return"], "forward_operations": sm["n_trades"]})
            for days in (30, 60, 90):
                hm = metrics(sf[sf["exit_timestamp"] < birth + pd.Timedelta(days=days)])
                horizon_rows.append({"generation": label, "strategy_hash": h, "horizon_days": days, **hm})
            for q, qf in sf.groupby(sf["exit_timestamp"].dt.tz_localize(None).dt.to_period("Q")):
                quarter_rows.append({"generation": label, "strategy_hash": h, "quarter": str(q), **metrics(qf)})
            gross_r = sf["result_R"] + sf["transaction_cost"] / sf["risk"].replace(0, np.nan)
            execution_rows.append({"generation": label, "strategy_hash": h, "n_trades": len(sf),
                                   "gross_R_total": float(gross_r.sum()), "net_R_total": float(sf.result_R.sum()),
                                   "total_transaction_cost_price": float(sf.transaction_cost.sum()),
                                   "mean_transaction_cost_price": float(sf.transaction_cost.mean()) if len(sf) else 0.0,
                                   "commission_observed": False, "spread_observed": False, "slippage_observed": False,
                                   "decomposition_note": "Ledger records total transaction_cost only; component costs are not identifiable per trade."})
    gen_df = pd.DataFrame(rows)
    gen_df["contribution_share_of_total"] = gen_df["portfolio_contribution"] / gen_df["portfolio_contribution"].sum()
    gen_df.to_csv(ART / "generation_diagnostics.csv", index=False)
    pd.DataFrame(horizon_rows).to_csv(ART / "strategy_horizons_30_60_90.csv", index=False)
    pd.DataFrame(quarter_rows).to_csv(ART / "strategy_quarters.csv", index=False)
    pd.DataFrame(execution_rows).to_csv(ART / "execution_decomposition.csv", index=False)
    pd.DataFrame([{**x, "forward": json.dumps(x["forward"], sort_keys=True),
                   "training": json.dumps(x["training"], sort_keys=True), "development": json.dumps(x["development"], sort_keys=True)}
                  for x in strategy_rows]).to_csv(ART / "strategy_diagnostics.csv", index=False)

    consolidated = json.loads((P09 / "consolidated.json").read_text())
    ledger = pd.read_csv(P09 / "portfolio_ledger.csv", parse_dates=["entry_timestamp", "exit_timestamp", "timestamp"])
    result = {"baseline": consolidated["portfolio"], "costs_x2": consolidated["forward_costs_x2"]["portfolio"],
              "n_portfolio_ledger_rows": len(ledger), "ledger_duplicate_rows": int(ledger.duplicated(["strategy_hash", "entry_timestamp", "exit_timestamp"]).sum()),
              "max_timestamp": str(max(pd.to_datetime(ledger["exit_timestamp"], utc=True))),
              "holdout_rows": int((pd.to_datetime(ledger["exit_timestamp"], utc=True) >= pd.Timestamp("2023-01-01", tz="UTC")).sum()),
              "policy_sha256": stable_hash(ROOT / "configs/rolling_factory.yaml"),
              "null_policy_sha256": stable_hash(ROOT / "configs/p10_null_control.yaml")}
    (ART / "integrity.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    ledger.to_csv(ART / "portfolio_ledger_copy.csv", index=False)
    contribution = (ledger.groupby("strategy_hash", as_index=False)
                    .agg(operations=("result_R", "size"), total_pnl=("pnl", "sum"),
                         mean_R=("result_R", "mean"))
                    .sort_values("total_pnl"))
    contribution["share_of_total_loss_or_gain"] = contribution["total_pnl"] / contribution["total_pnl"].sum()
    contribution.to_csv(ART / "portfolio_strategy_contributions.csv", index=False)
    events = []
    for row in ledger.itertuples():
        events.append((pd.Timestamp(row.entry_timestamp), 1))
        events.append((pd.Timestamp(row.exit_timestamp), -1))
    active = 0
    overlap = []
    for timestamp, delta in sorted(events, key=lambda x: (x[0], 0 if x[1] == -1 else 1)):
        active += delta
        overlap.append({"timestamp": timestamp, "active_positions": active})
    overlap_df = pd.DataFrame(overlap)
    overlap_df.to_csv(ART / "portfolio_overlap.csv", index=False)
    (ART / "null_control_b_estimate.json").write_text(json.dumps({
        "policy_id": "p10-null-control-v1", "status": "proposed_not_executed",
        "full_null_generations": 15, "evaluations_per_generation": 100000,
        "minimum_additional_evaluations": 1500000,
        "estimate_basis": "15 remaining historical generations; Q1 2019 pilot is preserved and not rerun",
        "reason": "No null signal generator was present in the frozen factory; executing B would require specifying and running that generator before any result could be interpreted."
    }, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
