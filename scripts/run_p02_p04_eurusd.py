"""Reproducible real-data P02 -> P03 -> P03.1 -> P04 runner.

The runner is intentionally limited to the declared DEV/TRAIN window. It does
not call the historical funnel because that funnel measures later walk-forward
and procedure-validation periods. Real run outputs stay under ``runs/``.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from new_forex.backtest.evaluator import Costs, build_market, evaluate_light
from new_forex.backtest.semantics import AGG
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.generators.genetic import GAConfig, run_genetic, write_archive
from new_forex.monte_carlo.bootstrap import MonteCarloConfig, run_monte_carlo, run_period_block_monte_carlo
from new_forex.monte_carlo.null_world import run_null_worlds
from new_forex.provenance import PROJECT_ROOT, code_version, file_sha256, load_config
from new_forex.selection.export import ExportConfig, export_finalists
from new_forex.selection.ranking import CandidateMetrics, SelectionConfig, select_candidates, write_selection_audit

DEV_START = "2003-01-01"
DEV_END = "2015-01-01"


def window(market, start: str = DEV_START, end: str = DEV_END) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(np.searchsorted(ts, np.datetime64(start))), int(np.searchsorted(ts, np.datetime64(end)))


def metrics_from_agg(agg: np.ndarray) -> CandidateMetrics:
    n = int(agg[AGG["n_trades"]])
    total = float(agg[AGG["sum_r"]])
    mean = total / n if n else 0.0
    losses = float(agg[AGG["gross_loss_r"]])
    wins = float(agg[AGG["gross_win_r"]])
    pf = wins / losses if losses else (math.inf if wins > 0 else 0.0)
    return CandidateMetrics(n, total, mean, pf, float(agg[AGG["max_dd"]]))


def _cfg_hash(name: str) -> str:
    return file_sha256(PROJECT_ROOT / "configs" / f"{name}.yaml")


def _load_market_from_canonical_cache(pair: str):
    """Build a market from the validated canonical cache, never from holdout rows."""
    cfg = load_config("data")
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / f"{pair}.parquet"
    if not cache.exists():
        raise FileNotFoundError(f"canonical cache missing: {cache}; run `python -m new_forex.cli build-data {pair} --rebuild`")
    m15 = pd.read_parquet(cache)
    metadata = m15.attrs.copy()
    market = build_market(pair, m15, Costs.for_pair(pair), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))
    market.meta.update(metadata)
    return market


def run_pipeline(*, output: Path, ga_cfg: GAConfig, seed: int, mc_iterations: int,
                 null_worlds: int, null_candidates: int, null_top_k: int) -> dict:
    policy = DataAccessPolicy.load()
    if policy.assert_range(DEV_START, DEV_END) is not Partition.DEV_TRAIN:
        raise RuntimeError("P02-P04 window is not dev_train")
    market = _load_market_from_canonical_cache("EURUSD")
    w = window(market)
    if w[1] <= w[0]:
        raise RuntimeError("dev_train has no EURUSD H1 bars")
    seed = int(seed)
    metrics: dict[str, CandidateMetrics] = {}

    def fitness(batch):
        agg = evaluate_light(market, batch, exec_tf="M15", window=w)
        values = []
        for strategy, row in zip(batch, agg, strict=True):
            metrics[strategy.canonical_hash] = metrics_from_agg(row)
            values.append(metrics[strategy.canonical_hash].mean_r)
        return np.asarray(values, dtype=float)

    output.mkdir(parents=True, exist_ok=True)
    ga = run_genetic("EURUSD", fitness, ga_cfg, seed=seed)
    archive_path = output / "p02_archive.jsonl"
    archive_manifest = write_archive(ga, archive_path, run_id=output.name, seed=seed, config=ga_cfg)

    candidates = [{"canonical_hash": key, "pair": "EURUSD", "metrics": metrics[key]}
                  for key in sorted(ga.archive)]
    selection_config = SelectionConfig(**{k: load_config("selection")[k] for k in SelectionConfig.__dataclass_fields__})
    selection = select_candidates(candidates, selection_config)
    strategies = {key: strategy for key, (strategy, _fitness) in ga.archive.items()}
    selection_path = output / "selection_audit.json"
    write_selection_audit(selection, selection_path, run_id=output.name, config=selection_config,
                          data_hashes={"EURUSD": str(market.meta.get("source_sha256", "unknown"))},
                          split_hash=file_sha256(PROJECT_ROOT / "configs" / "splits.yaml"))
    (output / "selection_candidates.jsonl").write_text("".join(
        json.dumps({"canonical_hash": row["canonical_hash"], "pair": row["pair"], "metrics": row["metrics"].__dict__},
                   sort_keys=True, separators=(",", ":"), default=str) + "\n" for row in candidates))

    export_config = ExportConfig(run_id=output.name, start=DEV_START, end=DEV_END)
    export_manifest = export_finalists(
        selection, candidates, strategies, {"EURUSD": market}, output / "p03.1_export",
        config=export_config, selection_config=selection_config,
        dataset_hashes={"EURUSD": str(market.meta.get("source_sha256", "unknown"))},
        split_hash=file_sha256(PROJECT_ROOT / "configs" / "splits.yaml"), source_archive=archive_path,
    )

    mc_cfg = MonteCarloConfig(iterations=mc_iterations, seed=20261002, block_length=20, method="moving", ruin_floor=0.5)
    mc_results = {}
    for finalist in export_manifest["finalists"]:
        ledger = pd.read_parquet(output / "p03.1_export" / finalist["ledger"])
        returns = ledger["result_R"].to_numpy(dtype=float) * float(market.risk_per_trade)
        period_ids = (pd.to_datetime(ledger["entry_timestamp"], utc=True).dt.tz_localize(None)
                      .dt.to_period("M").astype(str).to_numpy())
        mc_results[finalist["strategy_hash"]] = {
            "moving": _mc_json(run_monte_carlo(returns, mc_cfg)),
            "stationary": _mc_json(run_monte_carlo(returns, MonteCarloConfig(**{**mc_cfg.__dict__, "method": "stationary", "seed": 20261003}))),
            "period_block": _mc_json(run_period_block_monte_carlo(returns, period_ids, mc_cfg)),
        }
    null_result = run_null_worlds(worlds=null_worlds, candidates_per_world=null_candidates, top_k=null_top_k, seed=20261004)
    report = {"run_id": output.name, "code_version": code_version(), "partition": "dev_train",
              "period": {"start": DEV_START, "end": DEV_END}, "ga": archive_manifest,
              "selection": {"selected": list(selection.selected), "audit": selection.audit},
              "p03_1": {"finalists": len(export_manifest["finalists"])},
              "risk_policy": {"version": "p04-fixed-fractional-r-v1", "risk_per_trade": market.risk_per_trade,
                              "returns_input": "result_R * risk_per_trade", "ruin_floor": mc_cfg.ruin_floor},
              "monte_carlo_config": {"iterations": mc_cfg.iterations, "block_length": mc_cfg.block_length,
                                     "moving_seed": mc_cfg.seed, "stationary_seed": 20261003,
                                     "period_block_seed": mc_cfg.seed},
              "monte_carlo": mc_results,
              "null_world": {**null_result, "seed": 20261004, "candidates_per_world": null_candidates,
                             "top_k": null_top_k},
              "config_hashes": {n: _cfg_hash(n) for n in ("data", "ga", "selection", "mc", "splits")}}
    (output / "p04_report.json").write_text(json.dumps(report, sort_keys=True, indent=2, default=str) + "\n")
    return report


def _mc_json(result) -> dict:
    return {"ruin_probability": result.ruin_probability, "quantiles": result.quantiles,
            "iterations": len(result.final_equity)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261002)
    parser.add_argument("--max-evals", type=int, default=100_000)
    parser.add_argument("--population", type=int, default=1_000)
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--mc-iterations", type=int, default=5_000)
    parser.add_argument("--null-worlds", type=int, default=100)
    parser.add_argument("--null-candidates", type=int, default=1_000)
    parser.add_argument("--null-top-k", type=int, default=50)
    args = parser.parse_args()
    cfg = GAConfig(population=args.population, generations=args.generations, max_unique_evaluations=args.max_evals,
                   elite=min(20, max(1, args.population - 1)), tournament=min(4, args.population), crossover_rate=0.7,
                   mutation_rate=0.4, immigrant_rate=0.1, max_predicates=4)
    report = run_pipeline(output=args.output, ga_cfg=cfg, seed=args.seed, mc_iterations=args.mc_iterations,
                          null_worlds=args.null_worlds, null_candidates=args.null_candidates, null_top_k=args.null_top_k)
    print(json.dumps({"run_id": report["run_id"], "evaluated": report["ga"]["n_evaluated"],
                      "selected": report["selection"]["audit"], "finalists": report["p03_1"]["finalists"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
