"""Audit historical selection power without using forward predictors."""
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
from new_forex.strategy.definition import StrategyDefinition
from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12d_1_selection_power.yaml"
P12D = ROOT / "reports/p12d_artifacts/population_lifecycle.parquet"
ARCHIVE = ROOT / "runs/p08-rolling-2019-q1-v3/ga_archive.jsonl"
AUDIT = ROOT / "runs/p08-rolling-2019-q1-v3/selection_audit.jsonl"
OUT = ROOT / "reports/p12d_1_artifacts"


def load_historical() -> tuple[pd.DataFrame, dict[str, StrategyDefinition]]:
    rows: list[dict] = []
    strategies: dict[str, StrategyDefinition] = {}
    with ARCHIVE.open() as archive_file, AUDIT.open() as audit_file:
        for archive_line, audit_line in zip(archive_file, audit_file, strict=True):
            archived, audited = json.loads(archive_line), json.loads(audit_line)
            if archived["canonical_hash"] != audited["strategy_hash"]:
                raise ValueError("archive/audit hash mismatch")
            strategy = StrategyDefinition.from_json(json.dumps(archived["strategy"]))
            if strategy.canonical_hash != archived["canonical_hash"]:
                raise ValueError("canonical strategy hash mismatch")
            training = audited["training"]
            rows.append({
                "strategy_hash": archived["canonical_hash"],
                "training_n_trades": int(training.get("n_trades", 0)),
                "training_expectancy_R": float(training.get("expectancy_R", 0.0)),
                "training_profit_factor": float(training.get("profit_factor", 0.0)),
                "training_return": float(training.get("return", 0.0)),
                "training_max_drawdown": float(training.get("max_drawdown", 0.0)),
                "training_max_loss_streak": int(training.get("max_loss_streak", 0)),
                "direction": strategy.direction,
                "complexity": len(strategy.predicates),
                "original_filter_decision": audited["acceptance"]["decision"],
            })
            strategies[strategy.canonical_hash] = strategy
    historical = pd.DataFrame(rows)
    if len(historical) != 100_000 or historical["strategy_hash"].nunique() != 100_000:
        raise ValueError("historical universe is not exactly 100000 unique strategies")
    return historical, strategies


def mask_for(historical: pd.DataFrame, rule_id: str) -> pd.Series:
    n, pf, exp = historical["training_n_trades"], historical["training_profit_factor"], historical["training_expectancy_R"]
    base = n >= 100
    if rule_id == "full_population":
        return pd.Series(True, index=historical.index)
    if rule_id == "original_pass_benchmark":
        return historical["original_filter_decision"].eq("PASS")
    if rule_id == "train_pf_100_n100":
        return (pf >= 1.0) & base
    if rule_id == "train_pf_105_n100":
        return (pf >= 1.05) & base
    if rule_id == "train_pf_110_n100":
        return (pf >= 1.10) & base
    if rule_id == "train_exp_positive_n100":
        return (exp > 0) & base
    if rule_id == "train_exp_positive_pf105_n100":
        return (exp > 0) & (pf >= 1.05) & base
    if rule_id == "train_return_positive_dd20_n100":
        return (historical["training_return"] > 0) & (historical["training_max_drawdown"] <= 0.20) & base
    if rule_id == "train_pf105_n100_complexity_le2":
        return (pf >= 1.05) & base & (historical["complexity"] <= 2)
    if rule_id == "train_pf105_n100_long":
        return (pf >= 1.05) & base & historical["direction"].eq("LONG")
    if rule_id == "train_pf105_n100_short":
        return (pf >= 1.05) & base & historical["direction"].eq("SHORT")
    raise KeyError(rule_id)


def metric_summary(frame: pd.DataFrame, rule_id: str, quarter: str, cost: str = "forward") -> dict:
    active = frame[f"{cost}_n_trades"] > 0
    pf = frame[f"{cost}_profit_factor"].replace([np.inf, -np.inf], np.nan)
    return {"rule_id": rule_id, "quarter": quarter, "cost": cost, "n": len(frame), "active_pct": float(active.mean()),
            "positive_return_pct": float((active & (frame[f"{cost}_return"] > 0)).mean()),
            "positive_expectancy_pct": float((active & (frame[f"{cost}_expectancy_R"] > 0)).mean()),
            "mean_return": float(frame[f"{cost}_return"].mean()), "mean_expectancy_R": float(frame[f"{cost}_expectancy_R"].mean()),
            "median_return": float(frame[f"{cost}_return"].median()), "median_expectancy_R": float(frame[f"{cost}_expectancy_R"].median()),
            "median_finite_profit_factor": float(pf.median()) if pf.notna().any() else 0.0,
            "profit_factor_gt_1_pct": float((active & (frame[f"{cost}_profit_factor"] > 1)).mean()),
            "mean_max_drawdown": float(frame[f"{cost}_max_drawdown"].mean()),
            "mean_R_per_trade": float(np.divide(frame[f"{cost}_total_R"], frame[f"{cost}_n_trades"].replace(0, np.nan)).mean())}


def quarter_window(label: str) -> tuple[str, str]:
    period = pd.Period(label, freq="Q")
    return period.start_time.strftime("%Y-%m-%d"), (period.start_time + pd.DateOffset(months=3)).strftime("%Y-%m-%d")


def extended_portfolio_metrics(frame: pd.DataFrame) -> dict:
    metrics = portfolio_metrics(frame)
    if frame.empty:
        metrics.update({"expectancy_R": 0.0, "profit_factor": 0.0})
        return metrics
    result = frame["result_R"].to_numpy(float)
    wins = result[result > 0].sum()
    losses = -result[result < 0].sum()
    metrics.update({"expectancy_R": float(result.mean()), "profit_factor": float(wins / losses) if losses else (float("inf") if wins > 0 else 0.0)})
    return metrics


def main() -> None:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    if config["evaluation"]["no_forward_predictors"] is not True or config["evaluation"]["no_reselection"] is not True:
        raise ValueError("P12D.1 causal safeguards are not enabled")
    if file_sha256(ARCHIVE) != config["archive_sha256"]:
        raise ValueError("archive SHA256 mismatch")
    access = DataAccessPolicy.load()
    access.assert_readable(Partition.DEVELOPMENT_WF)
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    historical, strategies = load_historical()
    p12d = pd.read_parquet(P12D)
    if len(p12d) != 900_000 or p12d["strategy_hash"].nunique() != 100_000:
        raise ValueError("P12D longitudinal dataset integrity failure")
    OUT.mkdir(parents=True, exist_ok=True)

    rules = [item["id"] for item in config["rules_tested"]]
    trials: list[dict] = []
    discovery = p12d[p12d["quarter"].isin(config["discovery_quarters"])]
    for rule_id in rules:
        selected = set(historical.loc[mask_for(historical, rule_id), "strategy_hash"])
        frame = discovery[discovery["strategy_hash"].isin(selected)]
        for cost in ("forward", "forward_x2"):
            row = metric_summary(frame, rule_id, "2017_all", cost)
            row["discovery"] = True
            row["tested_definition"] = next(item["definition"] for item in config["rules_tested"] if item["id"] == rule_id)
            trials.append(row)
    pd.DataFrame(trials).to_csv(OUT / "rule_trials_2017.csv", index=False)

    formal = p12d[p12d["quarter"].isin(config["formal_quarters"])].copy()
    formal_rows: list[dict] = []
    for rule_id in ["full_population", "original_pass_benchmark", *config["formal_rules"]]:
        selected = set(historical.loc[mask_for(historical, rule_id), "strategy_hash"])
        frame = formal[formal["strategy_hash"].isin(selected)]
        for quarter, quarter_frame in frame.groupby("quarter", sort=True):
            for cost in ("forward", "forward_x2"):
                formal_rows.append(metric_summary(quarter_frame, rule_id, quarter, cost))
    pd.DataFrame(formal_rows).to_csv(OUT / "formal_individual_by_rule.csv", index=False)

    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until("2019-04-01")
    selected_sets: dict[str, list[str]] = {}
    all_hashes: set[str] = set()
    for rule_index, rule_id in enumerate(["full_population", "original_pass_benchmark", *config["formal_rules"]]):
        universe = sorted(historical.loc[mask_for(historical, rule_id), "strategy_hash"])
        if len(universe) < 5:
            raise ValueError(f"rule {rule_id} has fewer than five strategies")
        rng = random.Random(int(config["evaluation"]["seed_base"]) + rule_index * 100000)
        selected_sets[rule_id] = sorted(rng.sample(universe, 5))
        all_hashes.update(selected_sets[rule_id])
    control_sets: dict[str, list[list[str]]] = {}
    activity_universe = sorted(historical.loc[historical["training_n_trades"] >= 100, "strategy_hash"])
    for rule_index, rule_id in enumerate(config["formal_rules"]):
        control_sets[rule_id] = []
        for replicate in range(int(config["control"]["replicates"])):
            rng = random.Random(int(config["evaluation"]["seed_base"]) + (rule_index + 10) * 100000 + replicate)
            chosen = sorted(rng.sample(activity_universe, 5))
            control_sets[rule_id].append(chosen)
            all_hashes.update(chosen)
    ledger_cache: dict[tuple[str, str, float], pd.DataFrame] = {}
    for quarter in config["formal_quarters"]:
        window = _window(market, *quarter_window(quarter))
        for strategy_hash in sorted(all_hashes):
            strategy = strategies[strategy_hash]
            for multiplier in (1.0, 2.0):
                rich = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=multiplier, window=window)
                ledger_cache[(quarter, strategy_hash, multiplier)] = _ledger_frame(rich.trades, strategy, market)

    portfolio_rows: list[dict] = []
    portfolio_sets = {f"{rule_id}_portfolio": [selected_sets[rule_id]] for rule_id in selected_sets}
    for rule_id, sets in control_sets.items():
        portfolio_sets[f"{rule_id}_random_control"] = sets
    for group, sets in portfolio_sets.items():
        for replicate, chosen in enumerate(sets):
            for quarter in config["formal_quarters"]:
                row = {"group": group, "replicate": replicate, "quarter": quarter, "selected": json.dumps(chosen)}
                for label, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
                    ledgers = [(h, ledger_cache[(quarter, h, multiplier)]) for h in chosen]
                    metrics = extended_portfolio_metrics(portfolio_ledger(ledgers, risk_per_trade=config["evaluation"]["risk_per_trade"], max_aggregate_risk=config["evaluation"]["max_aggregate_risk"]))
                    row.update({f"{label}_{key}": value for key, value in metrics.items()})
                portfolio_rows.append(row)
    portfolio = pd.DataFrame(portfolio_rows)
    portfolio.to_csv(OUT / "portfolio_results.csv", index=False)
    manifest = {"policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "archive_sha256": file_sha256(ARCHIVE), "p12d_sha256": file_sha256(P12D), "rules_tested": len(rules), "formal_rules": config["formal_rules"], "formal_quarters": config["formal_quarters"], "portfolio_rows": len(portfolio), "control_portfolios": sum(len(value) for value in control_sets.values()), "holdout_used": False, "elapsed_seconds": time.perf_counter() - started}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    (OUT / "historical_variables.json").write_text(json.dumps({"available_before_2017": ["training_n_trades", "training_expectancy_R", "training_profit_factor", "training_return", "training_max_drawdown", "training_max_loss_streak", "direction", "complexity", "original_filter_decision"], "excluded_forward_predictors": ["behavior_signature", "forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown", "forward_x2_expectancy_R"]}, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
