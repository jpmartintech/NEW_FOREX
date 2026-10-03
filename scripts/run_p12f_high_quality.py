"""Evaluate the frozen P12F high-quality population on 2017Q1 only."""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
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
CONFIG = ROOT / "configs/p12f_high_quality.yaml"
OUT = ROOT / "reports/p12f_artifacts"
P12D = ROOT / "reports/p12d_artifacts/population_lifecycle.parquet"
ARCHIVE = ROOT / "runs/p08-rolling-2019-q1-v3/ga_archive.jsonl"
AUDIT = ROOT / "runs/p08-rolling-2019-q1-v3/selection_audit.jsonl"

sys.path.insert(0, str(ROOT / "scripts"))
from run_p08_rolling_factory import _load_market_until, _window  # noqa: E402


def _load_population() -> tuple[pd.DataFrame, dict[str, StrategyDefinition]]:
    rows: list[dict] = []
    strategies: dict[str, StrategyDefinition] = {}
    with ARCHIVE.open() as archive_file, AUDIT.open() as audit_file:
        for archive_line, audit_line in zip(archive_file, audit_file, strict=True):
            archived, audited = json.loads(archive_line), json.loads(audit_line)
            key = archived["canonical_hash"]
            if key != audited["strategy_hash"]:
                raise ValueError("archive/audit hash mismatch")
            strategy = StrategyDefinition.from_json(json.dumps(archived["strategy"]))
            if strategy.canonical_hash != key:
                raise ValueError(f"canonical strategy hash mismatch: {key}")
            training = audited["training"]
            rows.append({
                "strategy_hash": key,
                "training_profit_factor": float(training.get("profit_factor", 0.0)),
                "training_n_trades": int(training.get("n_trades", 0)),
                "training_expectancy_R": float(training.get("expectancy_R", 0.0)),
                "training_return": float(training.get("return", 0.0)),
                "training_max_drawdown": float(training.get("max_drawdown", 0.0)),
                "direction": strategy.direction,
                "complexity": len(strategy.predicates),
                "original_filter_decision": audited["acceptance"]["decision"],
            })
            strategies[key] = strategy
    historical = pd.DataFrame(rows)
    if len(historical) != 100_000 or historical["strategy_hash"].nunique() != 100_000:
        raise ValueError("P08 universe is not exactly 100000 unique strategies")
    return historical, strategies


def _assert_sources(config: dict) -> None:
    source = config["source"]
    expected = {
        ARCHIVE: source["archive_sha256"],
        AUDIT: source["selection_audit_sha256"],
        P12D: source["p12d_population_sha256"],
    }
    for path, digest in expected.items():
        if file_sha256(path) != digest:
            raise ValueError(f"source SHA256 mismatch: {path}")
    if config["evaluation"]["holdout_used"] or config["evaluation"]["no_later_quarters"] is not True:
        raise ValueError("P12F temporal safeguards are disabled")


def _masks(historical: pd.DataFrame) -> dict[str, pd.Series]:
    pf = historical["training_profit_factor"]
    n = historical["training_n_trades"]
    return {
        "full_population": pd.Series(True, index=historical.index),
        "prior_filter": (pf >= 1.05) & (n >= 100),
        "high_quality": (pf > 1.30) & (n > 250),
    }


def _summary(frame: pd.DataFrame, group: str, cost: str) -> dict:
    prefix = "forward" if cost == "baseline" else "forward_x2"
    active = frame["forward_n_trades"] > 0
    exp = frame[f"{prefix}_expectancy_R"]
    ret = frame[f"{prefix}_return"]
    gross_exp = frame["forward_gross_expectancy_R"]
    return {
        "group": group,
        "cost": cost,
        "n": int(len(frame)),
        "active_n": int(active.sum()),
        "active_pct": float(active.mean()),
        "mean_expectancy_R": float(exp.mean()),
        "median_expectancy_R": float(exp.median()),
        "mean_gross_expectancy_R": float(gross_exp[active].mean()) if active.any() else None,
        "median_gross_expectancy_R": float(gross_exp[active].median()) if active.any() else None,
        "mean_return": float(ret.mean()),
        "median_return": float(ret.median()),
        "p05_return": float(ret.quantile(0.05)),
        "p25_return": float(ret.quantile(0.25)),
        "p50_return": float(ret.quantile(0.50)),
        "p75_return": float(ret.quantile(0.75)),
        "p95_return": float(ret.quantile(0.95)),
        "positive_net_pct_active": float((ret[active] > 0).mean()) if active.any() else None,
        "positive_expectancy_pct_active": float((exp[active] > 0).mean()) if active.any() else None,
        "mean_cost_R_per_trade": float(frame["cost_R_per_trade"].replace([np.inf, -np.inf], np.nan).mean()),
        "median_cost_R_per_trade": float(frame["cost_R_per_trade"].replace([np.inf, -np.inf], np.nan).median()),
        "gross_positive_net_negative_pct_active": float(((gross_exp[active] > 0) & (exp[active] < 0)).mean()) if active.any() else None,
        "mean_n_trades_active": float(frame.loc[active, "forward_n_trades"].mean()) if active.any() else 0.0,
        "mean_max_drawdown": float(frame["forward_max_drawdown"].mean()),
        "gross_return_available": False,
    }


def _make_activity_bins(values: pd.Series, bins: int) -> tuple[pd.Series, np.ndarray]:
    ranks = values.rank(method="first")
    labels = np.minimum(((ranks - 1) * bins / len(values)).astype(int), bins - 1)
    return labels.astype(int), np.arange(bins)


def _sample_portfolios(historical: pd.DataFrame, masks: dict[str, pd.Series], config: dict) -> list[dict]:
    size = int(config["portfolio"]["size"])
    replicas = int(config["portfolio"]["replicates"])
    seed_base = int(config["portfolio"]["seed_base"])
    sets: list[dict] = []
    for group_index, group in enumerate(config["portfolio"]["groups"]):
        universe = sorted(historical.loc[masks[group], "strategy_hash"])
        if len(universe) < size:
            raise ValueError(f"group {group} has fewer than five strategies")
        for replicate in range(replicas):
            seed = seed_base + group_index * 100_000 + replicate
            selected = sorted(random.Random(seed).sample(universe, size))
            sets.append({"group": group, "replicate": replicate, "seed": seed, "selected": selected})
    return sets


def _sample_controls(historical: pd.DataFrame, high: pd.Series, config: dict) -> list[dict]:
    size = int(config["portfolio"]["size"])
    bins = int(config["controls"]["activity_matched"]["matching_bins"])
    full = sorted(historical["strategy_hash"])
    high_values = historical.loc[high, "training_n_trades"]
    full_bins, labels = _make_activity_bins(historical["training_n_trades"], bins)
    high_bins, _ = _make_activity_bins(high_values, bins)
    target_counts = high_bins.value_counts().reindex(labels, fill_value=0).astype(int).to_dict()
    members = {int(label): sorted(historical.loc[full_bins == label, "strategy_hash"]) for label in labels}
    controls: list[dict] = []
    for group, settings in (("control_full", config["controls"]["full_population"]), ("control_activity", config["controls"]["activity_matched"])):
        for replicate in range(int(settings["replicates"])):
            seed = int(settings["seed_base"]) + replicate
            rng = random.Random(seed)
            if group == "control_full":
                selected = sorted(rng.sample(full, size))
            else:
                selected = []
                target_labels = list(target_counts)
                weights = [target_counts[label] for label in target_labels]
                for _ in range(size):
                    label = rng.choices(target_labels, weights=weights, k=1)[0]
                    available = [key for key in members[int(label)] if key not in selected]
                    if not available:
                        available = [key for key in full if key not in selected]
                    selected.append(rng.choice(available))
                if len(selected) != size or len(set(selected)) != size:
                    raise ValueError("activity-matched control could not produce five unique strategies")
                rng.shuffle(selected)
                selected = sorted(selected)
            controls.append({"group": group, "replicate": replicate, "seed": seed, "selected": selected})
    return controls


def _portfolio_metrics(frame: pd.DataFrame, cost: str, gross_frame: pd.DataFrame | None = None) -> dict:
    metrics = portfolio_metrics(frame)
    values = frame["result_R"].to_numpy(float) if not frame.empty else np.array([], dtype=float)
    wins = values[values > 0].sum()
    losses = -values[values < 0].sum()
    result = {
        "n_trades": metrics["n_trades"], "return": metrics["return"], "max_drawdown": metrics["max_drawdown"],
        "pnl_net": metrics["pnl"], "expectancy_R": float(values.mean()) if len(values) else 0.0,
        "profit_factor": float(wins / losses) if losses else (math.inf if wins > 0 else 0.0),
        "cost": cost,
    }
    if gross_frame is not None:
        result["pnl_gross"] = float(gross_frame["pnl"].sum()) if not gross_frame.empty else 0.0
        result["return_gross"] = float(gross_frame["equity"].iloc[-1] - 1.0) if not gross_frame.empty else 0.0
        result["expectancy_gross_R"] = float(gross_frame["result_R"].mean()) if not gross_frame.empty else 0.0
        result["cost_absolute"] = result["pnl_gross"] - result["pnl_net"]
    return result


def _evaluate_portfolios(portfolios: list[dict], strategies: dict[str, StrategyDefinition], market, config: dict) -> pd.DataFrame:
    out_rows: list[dict] = []
    window = _window(market, "2017-01-01", "2017-04-01")
    cache: dict[tuple[str, float], pd.DataFrame] = {}
    checkpoint = OUT / "checkpoint.json"
    saved = json.loads(checkpoint.read_text()) if checkpoint.exists() else {"completed": []}
    unique_hashes = sorted({key for row in portfolios for key in row["selected"]})
    for index, key in enumerate(unique_hashes):
        for multiplier in (1.0, 2.0):
            item = f"{key}:{multiplier:g}"
            path = OUT / f"ledger_{key}_{multiplier:g}.parquet"
            if item in saved["completed"] and path.exists():
                cache[(key, multiplier)] = pd.read_parquet(path)
                continue
            rich = evaluate_rich(market, strategies[key], exec_tf="M15", cost_multiplier=multiplier, window=window)
            ledger = _ledger_frame(rich.trades, strategies[key], market)
            if not ledger.empty and ledger["strategy_hash"].nunique() != 1:
                raise ValueError("strategy ledger identity failure")
            ledger.to_parquet(path, index=False)
            cache[(key, multiplier)] = ledger
            saved["completed"].append(item)
            checkpoint.write_text(json.dumps(saved, sort_keys=True, indent=2) + "\n")
        if index and index % 1000 == 0:
            print(f"evaluated {index}/{len(unique_hashes)} unique portfolio strategies", flush=True)

    for row in portfolios:
        for label, multiplier in (("baseline", 1.0), ("costs_x2", 2.0)):
            frames = [cache[(key, multiplier)] for key in row["selected"]]
            ledgers = [(key, frame) for key, frame in zip(row["selected"], frames, strict=True)]
            actual = portfolio_ledger(ledgers, risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"])
            gross = None
            if multiplier == 1.0:
                x2_frames = [cache[(key, 2.0)] for key in row["selected"]]
                derived = []
                for base_frame, x2_frame in zip(frames, x2_frames, strict=True):
                    keys = ["entry_timestamp", "exit_timestamp"]
                    if len(base_frame) != len(x2_frame) or not base_frame[keys].reset_index(drop=True).equals(x2_frame[keys].reset_index(drop=True)):
                        raise ValueError("baseline/x2 operation identity mismatch")
                    derived_frame = base_frame.copy()
                    derived_frame["result_R"] = 2 * base_frame["result_R"].to_numpy(float) - x2_frame["result_R"].to_numpy(float)
                    derived.append((base_frame["strategy_hash"].iloc[0] if not base_frame.empty else "", derived_frame))
                gross = portfolio_ledger(derived, risk_per_trade=config["portfolio"]["risk_per_trade"], max_aggregate_risk=config["portfolio"]["max_aggregate_risk"])
            metrics = _portfolio_metrics(actual, label, gross)
            out_rows.append({"group": row["group"], "replicate": row["replicate"], "seed": row["seed"], "selected": json.dumps(row["selected"]), **metrics})
    results = pd.DataFrame(out_rows)
    gross_by_portfolio = results[results["cost"].eq("baseline")].set_index(["group", "replicate"])[
        ["pnl_gross", "return_gross", "expectancy_gross_R"]
    ]
    x2 = results["cost"].eq("costs_x2")
    keys = pd.MultiIndex.from_frame(results.loc[x2, ["group", "replicate"]])
    gross_values = gross_by_portfolio.reindex(keys).to_numpy()
    results.loc[x2, ["pnl_gross", "return_gross", "expectancy_gross_R"]] = gross_values
    results.loc[x2, "cost_absolute"] = results.loc[x2, "pnl_gross"] - results.loc[x2, "pnl_net"]
    return results


def main() -> None:
    started = time.perf_counter()
    config = yaml.safe_load(CONFIG.read_bytes())
    _assert_sources(config)
    DataAccessPolicy.load().assert_readable(Partition.DEVELOPMENT_WF)
    historical, strategies = _load_population()
    p12d = pd.read_parquet(P12D)
    q1 = p12d[p12d["quarter"].eq("2017Q1")].copy()
    if len(q1) != 100_000 or q1["strategy_hash"].nunique() != 100_000:
        raise ValueError("P12D 2017Q1 is not exactly 100000 unique strategies")
    if not (q1["quarter_start"].eq("2017-01-01") & q1["quarter_end_exclusive"].eq("2017-04-01")).all():
        raise ValueError("P12D quarter bounds do not match P12F")
    if (q1["forward_n_trades"] != q1["forward_x2_n_trades"]).any():
        raise ValueError("baseline/x2 trade counts differ; gross derivation is invalid")
    forward_columns = [
        "strategy_hash", "quarter", "quarter_start", "quarter_end_exclusive", "forward_n_trades",
        "forward_total_R", "forward_expectancy_R", "forward_profit_factor", "forward_return",
        "forward_max_drawdown", "forward_x2_n_trades", "forward_x2_total_R", "forward_x2_expectancy_R",
        "forward_x2_profit_factor", "forward_x2_return", "forward_x2_max_drawdown",
    ]
    frame = historical.merge(q1[forward_columns], on="strategy_hash", how="inner", validate="one_to_one")
    frame["forward_gross_total_R"] = 2 * frame["forward_total_R"] - frame["forward_x2_total_R"]
    frame["forward_gross_expectancy_R"] = np.divide(frame["forward_gross_total_R"], frame["forward_n_trades"], out=np.zeros(len(frame)), where=frame["forward_n_trades"].to_numpy() != 0)
    frame["cost_R_total"] = frame["forward_gross_total_R"] - frame["forward_total_R"]
    frame["cost_R_per_trade"] = np.divide(frame["cost_R_total"], frame["forward_n_trades"], out=np.full(len(frame), np.nan), where=frame["forward_n_trades"].to_numpy() != 0)
    masks = _masks(frame)
    OUT.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(OUT / "individual_population.parquet", index=False)
    pd.DataFrame([_summary(frame.loc[mask], group, "baseline") for group, mask in masks.items()]
                 + [_summary(frame.loc[mask], group, "costs_x2") for group, mask in masks.items()]).to_csv(OUT / "individual_group_summary.csv", index=False)
    eligibility = frame[["strategy_hash", "training_profit_factor", "training_n_trades", "training_expectancy_R", "training_return", "training_max_drawdown", "direction", "complexity", "original_filter_decision"]].copy()
    eligibility["prior_filter"] = masks["prior_filter"]
    eligibility["high_quality"] = masks["high_quality"]
    eligibility.to_parquet(OUT / "eligibility.parquet", index=False)

    portfolios = _sample_portfolios(frame, masks, config)
    controls = _sample_controls(frame, masks["high_quality"], config)
    all_portfolios = portfolios + controls
    pd.DataFrame([{"group": row["group"], "replicate": row["replicate"], "seed": row["seed"], "selected": json.dumps(row["selected"])} for row in all_portfolios]).to_json(OUT / "portfolio_compositions.jsonl", orient="records", lines=True)
    market = _load_market_until("2017-04-01")
    portfolio_results = _evaluate_portfolios(all_portfolios, strategies, market, config)
    portfolio_results.to_csv(OUT / "portfolio_results.csv", index=False)
    manifest = {
        "policy_id": config["policy_id"], "config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "archive_sha256": file_sha256(ARCHIVE), "selection_audit_sha256": file_sha256(AUDIT),
        "p12d_sha256": file_sha256(P12D), "quarter": "2017Q1", "n_strategies": len(frame),
        "high_quality_n": int(masks["high_quality"].sum()), "prior_filter_n": int(masks["prior_filter"].sum()),
        "portfolio_rows": len(portfolio_results), "unique_portfolio_strategies": len({key for row in all_portfolios for key in row["selected"]}),
        "gross_R_reconciled": True, "gross_capitalized_individual_return_available": False,
        "transaction_cost_breakdown": "aggregate_only", "holdout_used": False,
        "elapsed_seconds": time.perf_counter() - started,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
