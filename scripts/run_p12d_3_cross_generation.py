"""Replicate the frozen P12D.1 rule across the 15 P09 generations."""
from __future__ import annotations

import hashlib
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from new_forex.backtest.evaluator import evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import file_sha256
from new_forex.selection.export import _ledger_frame
from new_forex.strategy.definition import StrategyDefinition

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12d_3_cross_generation.yaml"
P12C = ROOT / "reports/p12c_artifacts"
P09 = ROOT / "runs/p09-rolling-historical-v1"
OUT = ROOT / "reports/p12d_3_artifacts"
ARCHIVE_SHA256S = {}


def generation_data(label: str) -> tuple[pd.DataFrame, dict, list[str]]:
    directory = P12C / label
    parts = sorted(directory.glob("part-*.parquet"))
    if len(parts) != 20:
        raise RuntimeError(f"{label}: expected 20 P12C parts, found {len(parts)}")
    forward = pd.concat([pd.read_parquet(path) for path in parts], ignore_index=True)
    forward["quarter"] = label
    if len(forward) != 100_000 or forward["strategy_hash"].nunique() != 100_000:
        raise ValueError(f"{label}: invalid P12C population")
    audit_rows = []
    audit_path = P09 / label / "selection_audit.jsonl"
    with audit_path.open() as handle:
        for line in handle:
            row = json.loads(line)
            training = row["training"]
            audit_rows.append({"strategy_hash": row["strategy_hash"], "training_profit_factor": float(training.get("profit_factor", 0.0)), "audit_training_n_trades": int(training.get("n_trades", 0)), "audit_training_expectancy_R": float(training.get("expectancy_R", 0.0)), "audit_training_return": float(training.get("return", 0.0)), "audit_training_max_drawdown": float(training.get("max_drawdown", 0.0))})
    audit = pd.DataFrame(audit_rows)
    if len(audit) != 100_000 or audit["strategy_hash"].nunique() != 100_000:
        raise ValueError(f"{label}: incomplete historical audit")
    merged = forward.merge(audit, on="strategy_hash", validate="one_to_one")
    checks = [
        np.allclose(merged.training_n_trades, merged.audit_training_n_trades),
        np.allclose(merged.training_expectancy_R, merged.audit_training_expectancy_R),
        np.allclose(merged.training_max_drawdown, merged.audit_training_max_drawdown),
    ]
    if not all(checks):
        raise ValueError(f"{label}: P12C and generation-specific training statistics disagree")
    report = json.loads((P09 / label / "generation.json").read_text())
    archive = P09 / label / "ga_archive.jsonl"
    if file_sha256(archive) != report["ga"]["archive_sha256"]:
        raise ValueError(f"{label}: archive checksum mismatch")
    ARCHIVE_SHA256S[label] = file_sha256(archive)
    return merged, report, parts


def load_strategies(label: str, wanted: set[str]) -> dict[str, StrategyDefinition]:
    result = {}
    with (P09 / label / "ga_archive.jsonl").open() as handle:
        for line in handle:
            row = json.loads(line)
            if row["canonical_hash"] not in wanted:
                continue
            strategy = StrategyDefinition.from_json(json.dumps(row["strategy"]))
            if strategy.canonical_hash != row["canonical_hash"]:
                raise ValueError(f"{label}: strategy hash mismatch")
            result[row["canonical_hash"]] = strategy
    if set(result) != wanted:
        raise ValueError(f"{label}: missing definitions for sampled strategies")
    return result


def window(label: str) -> tuple[str, str]:
    period = pd.Period(label, freq="Q")
    return period.start_time.strftime("%Y-%m-%d"), (period.start_time + pd.DateOffset(months=3)).strftime("%Y-%m-%d")


def max_concurrent(frames: list[pd.DataFrame]) -> int:
    events = []
    for frame in frames:
        for row in frame.itertuples():
            events.extend(((pd.Timestamp(row.entry_timestamp), 1), (pd.Timestamp(row.exit_timestamp), -1)))
    active = maximum = 0
    for _timestamp, change in sorted(events, key=lambda item: (item[0], 0 if item[1] < 0 else 1)):
        active += change
        maximum = max(maximum, active)
    return maximum


def portfolio_metrics(ledgers: list[tuple[str, pd.DataFrame]], config: dict) -> dict:
    return fast_portfolio_metrics(ledgers, config)


def evaluate_strategy_ledger(item: tuple[str, StrategyDefinition, object, float, tuple[int, int], object]) -> tuple[str, pd.DataFrame]:
    strategy_hash, strategy, market, multiplier, window_indices, market_object = item
    rich = evaluate_rich(market_object, strategy, exec_tf="M15", cost_multiplier=multiplier, window=window_indices)
    frame = _ledger_frame(rich.trades, strategy, market).copy()
    frame["strategy_hash"] = strategy_hash
    return strategy_hash, frame


def fast_portfolio_metrics(ledgers: list[tuple[str, pd.DataFrame]], config: dict) -> dict:
    """Equivalent event sweep to portfolio_ledger, retaining the frozen contract."""
    risk = float(config["evaluation"]["risk_per_trade"])
    cap = float(config["evaluation"]["max_aggregate_risk"])
    events = []
    for strategy_hash, frame in ledgers:
        for row in frame.itertuples():
            entry = pd.Timestamp(row.entry_timestamp)
            exit_time = pd.Timestamp(row.exit_timestamp)
            same_bar = entry == exit_time
            events.append((entry, 0 if same_bar else 1, strategy_hash, 1, float(row.result_R)))
            events.append((exit_time, 1 if same_bar else 0, strategy_hash, 0, float(row.result_R)))
    if not events:
        return {"n_trades": 0, "pnl": 0.0, "return": 0.0, "max_drawdown": 0.0, "active_strategies": 0, "expectancy_R": 0.0, "profit_factor": 0.0, "max_concurrent_positions": 0}
    events.sort(key=lambda row: (row[0], row[1], row[2]))
    active: dict[str, list[float]] = {}
    active_count = 0
    equity = 1.0
    results = []
    equities = []
    max_concurrent_positions = 0
    for _timestamp, _priority, strategy_hash, kind, result_r in events:
        if kind == 1:
            if (len(active) + 1) * risk > cap + 1e-12:
                raise ValueError("portfolio aggregate risk cap exceeded")
            active.setdefault(strategy_hash, []).append(equity)
            active_count += 1
            max_concurrent_positions = max(max_concurrent_positions, active_count)
        else:
            entries = active.get(strategy_hash, [])
            if not entries:
                raise ValueError("exit without active portfolio position")
            entry_equity = entries.pop(0)
            if not entries:
                active.pop(strategy_hash)
            active_count -= 1
            pnl = entry_equity * risk * result_r
            equity += pnl
            results.append(result_r)
            equities.append(equity)
    if active:
        raise ValueError("portfolio contains open positions after forward window")
    result_array = np.asarray(results, dtype=float)
    equity_array = np.asarray(equities, dtype=float)
    peaks = np.maximum.accumulate(equity_array)
    wins = result_array[result_array > 0].sum()
    losses = -result_array[result_array < 0].sum()
    return {"n_trades": int(len(result_array)), "pnl": float(equity - 1.0), "return": float(equity - 1.0), "max_drawdown": float((1.0 - equity_array / peaks).max()), "active_strategies": len({strategy_hash for strategy_hash, _frame in ledgers}), "expectancy_R": float(result_array.mean()), "profit_factor": float(wins / losses) if losses else (float("inf") if wins > 0 else 0.0), "max_concurrent_positions": max_concurrent_positions}


def main() -> None:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    if config["evaluation"]["no_forward_selection"] is not True or config["evaluation"]["no_reselection"] is not True:
        raise ValueError("P12D.3 causal safeguards are not enabled")
    access = DataAccessPolicy.load()
    access.assert_readable(Partition.PROCEDURE_VALIDATION)
    access.assert_range("2019-01-01", "2023-01-01")
    OUT.mkdir(parents=True, exist_ok=True)
    market = None
    from run_p08_rolling_factory import _load_market_until, _window

    market = _load_market_until("2023-01-01")
    composition_rows = []
    portfolio_rows = []
    individual_rows = []
    eligibility_rows = []
    dependence_rows = []
    trajectory_inputs = {"eligible": [], "full_random": [], "activity_matched": []}
    original_inputs = []
    for generation_index, label in enumerate(config["generations"]):
        population, report, _parts = generation_data(label)
        eligible_mask = (population.training_profit_factor >= config["rule"]["training_profit_factor_gte"]) & (population.training_n_trades >= config["rule"]["training_n_trades_gte"])
        eligible = sorted(population.loc[eligible_mask, "strategy_hash"])
        full = sorted(population.strategy_hash)
        activity = sorted(population.loc[population.training_n_trades >= config["controls"]["activity_matched_training_n_gte"], "strategy_hash"])
        if len(eligible) < 5 or len(activity) < 5:
            eligibility_rows.append({"generation": label, "total": len(full), "eligible": len(eligible), "eligible_pct": len(eligible) / len(full), "insufficient": True})
            continue
        eligibility_rows.append({"generation": label, "total": len(full), "eligible": len(eligible), "eligible_pct": len(eligible) / len(full), "activity_matched_universe": len(activity), "insufficient": False, "training_pf_median": population.training_profit_factor.median(), "training_pf_p95": population.training_profit_factor.quantile(.95), "training_n_median": population.training_n_trades.median(), "training_n_p95": population.training_n_trades.quantile(.95)})
        for group, values in (("eligible", eligible), ("full_random", full), ("activity_matched", activity)):
            for replicate in range(config["evaluation"]["portfolios_per_generation"]):
                seed_base = config["evaluation"][f"seed_base_{'eligible' if group == 'eligible' else ('full_control' if group == 'full_random' else 'activity_control')}"]
                seed = int(seed_base) + generation_index * 100000 + replicate
                selected = sorted(random.Random(seed).sample(values, config["evaluation"]["portfolio_size"]))
                composition_rows.append({"generation": label, "group": group, "replicate": replicate, "seed": seed, "selected": selected})
                if replicate < 1000:
                    trajectory_inputs[group].append((label, replicate, selected))
        original = list(report["finalists"])
        original_inputs.append((label, original))
        wanted = set(original)
        for row in composition_rows[-3000:]:
            if row["generation"] == label:
                wanted.update(row["selected"])
        strategies = load_strategies(label, wanted)
        windows = _window(market, *window(label))
        ledgers = {"baseline": {}, "costs_x2": {}}
        for cost_name, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
            cache_path = OUT / f"ledgers_{label}_{cost_name}.parquet"
            if cache_path.exists():
                cached = pd.read_parquet(cache_path)
                for strategy_hash, frame in cached.groupby("strategy_hash", sort=False):
                    ledgers[cost_name][strategy_hash] = frame.drop(columns=["strategy_hash"])
            else:
                items = [(strategy_hash, strategies[strategy_hash], market, multiplier, windows, market) for strategy_hash in sorted(wanted)]
                with ThreadPoolExecutor(max_workers=int(config["evaluation"]["worker_threads"])) as executor:
                    frames = [frame for _strategy_hash, frame in executor.map(evaluate_strategy_ledger, items)]
                for frame in frames:
                    ledgers[cost_name][frame["strategy_hash"].iloc[0] if not frame.empty else ""] = frame.drop(columns=["strategy_hash"])
                for strategy_hash in sorted(wanted):
                    if strategy_hash not in ledgers[cost_name]:
                        ledgers[cost_name][strategy_hash] = pd.DataFrame()
                pd.concat(frames, ignore_index=True).to_parquet(cache_path, index=False)
        for row in [item for item in composition_rows if item["generation"] == label]:
            for cost_name in ("baseline", "costs_x2"):
                metrics = portfolio_metrics([(h, ledgers[cost_name].get(h, pd.DataFrame())) for h in row["selected"]], config)
                portfolio_rows.append({"generation": label, "group": row["group"], "replicate": row["replicate"], "cost": cost_name, **metrics})
        for cost_name in ("baseline", "costs_x2"):
            metrics = portfolio_metrics([(h, ledgers[cost_name].get(h, pd.DataFrame())) for h in original], config)
            portfolio_rows.append({"generation": label, "group": "original_p09", "replicate": -1, "cost": cost_name, **metrics})
            original_inputs[-1] = (label, original, metrics)
        formal = population.copy()
        for group, mask in (("eligible", eligible_mask), ("noneligible", ~eligible_mask), ("full", pd.Series(True, index=population.index))):
            part = formal[mask]
            for cost in ("forward", "forward_x2"):
                active = part[f"{cost}_n_trades"] > 0
                individual_rows.append({"generation": label, "group": group, "cost": cost, "n": len(part), "active_pct": active.mean(), "positive_return_pct": (active & (part[f"{cost}_return"] > 0)).mean(), "positive_expectancy_pct": (active & (part[f"{cost}_expectancy_R"] > 0)).mean(), "mean_return": part[f"{cost}_return"].mean(), "mean_expectancy_R": part[f"{cost}_expectancy_R"].mean(), "median_return": part[f"{cost}_return"].median(), "mean_max_drawdown": part[f"{cost}_max_drawdown"].mean()})
        signature = formal[eligible_mask].assign(signature=formal.loc[eligible_mask, ["forward_n_trades", "forward_expectancy_R", "forward_return", "forward_max_drawdown"]].astype(str).agg("|".join, axis=1))
        dependence_rows.append({"generation": label, "eligible": len(signature), "unique_signatures": signature.signature.nunique(), "duplicate_rows": len(signature) - signature.signature.nunique(), "largest_signature": signature.signature.value_counts().iloc[0]})

    compositions_path = OUT / "compositions.jsonl"
    compositions_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in composition_rows) + "\n")
    pd.DataFrame(eligibility_rows).to_csv(OUT / "eligibility_by_generation.csv", index=False)
    pd.DataFrame(individual_rows).to_csv(OUT / "individual_by_generation.csv", index=False)
    pd.DataFrame(portfolio_rows).to_csv(OUT / "portfolio_results.csv", index=False)
    pd.DataFrame(dependence_rows).to_csv(OUT / "dependence_by_generation.csv", index=False)
    all_results = pd.DataFrame(portfolio_rows)
    trajectories = []
    for group in trajectory_inputs:
        for replicate in range(config["trajectories"]["count"]):
            for cost in ("baseline", "costs_x2"):
                part = all_results[(all_results.group == group) & (all_results.replicate == replicate) & (all_results.cost == cost)].sort_values("generation")
                curve = np.cumprod(1 + part["return"].to_numpy(float))
                trajectories.append({"group": group, "replicate": replicate, "cost": cost, "cumulative_return": curve[-1] - 1, "max_drawdown": (1 - curve / np.maximum.accumulate(curve)).max(), "positive": curve[-1] > 1})
    pd.DataFrame(trajectories).to_csv(OUT / "rolling_trajectories.csv", index=False)
    summary_rows = []
    for (generation, group, cost), part in all_results[all_results.group != "original_p09"].groupby(["generation", "group", "cost"]):
        summary_rows.append({"generation": generation, "group": group, "cost": cost, "n": len(part), "mean_return": part["return"].mean(), "median_return": part["return"].median(), "p05_return": part["return"].quantile(.05), "p25_return": part["return"].quantile(.25), "p75_return": part["return"].quantile(.75), "p95_return": part["return"].quantile(.95), "positive_fraction": (part["return"] > 0).mean(), "mean_expectancy_R": part["expectancy_R"].mean(), "mean_profit_factor": part["profit_factor"].replace([np.inf, -np.inf], np.nan).mean(), "mean_max_drawdown": part["max_drawdown"].mean(), "mean_n_trades": part["n_trades"].mean()})
    pd.DataFrame(summary_rows).to_csv(OUT / "generation_summary.csv", index=False)
    manifest = {"policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(), "generations": len(config["generations"]), "generation_archive_sha256": ARCHIVE_SHA256S, "eligible_total_records": int(sum(row["eligible"] for row in eligibility_rows)), "portfolio_rows": len(all_results), "trajectory_rows": len(trajectories), "holdout_used": False, "elapsed_seconds": time.perf_counter() - started}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
