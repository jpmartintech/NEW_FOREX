"""Deterministic, auditable historical ranking net of declared costs."""
from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from math import inf
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SelectionConfig:
    top_k: int = 50
    min_trades: int = 100
    min_mean_r: float = 0.0
    min_profit_factor: float = 1.0
    max_pair_fraction: float = 1.0

    def __post_init__(self) -> None:
        if self.top_k < 1 or self.min_trades < 1:
            raise ValueError("top_k and min_trades must be positive")
        if not 0 < self.max_pair_fraction <= 1:
            raise ValueError("max_pair_fraction must be in (0, 1]")


@dataclass(frozen=True)
class CandidateMetrics:
    n_trades: int
    total_r: float
    mean_r: float
    profit_factor: float
    max_dd: float


@dataclass(frozen=True)
class SelectionResult:
    selected: tuple[str, ...]
    metrics: dict[str, CandidateMetrics]
    audit: dict[str, int]


def write_selection_audit(result: SelectionResult, path: Path, *, run_id: str, config: SelectionConfig,
                          data_hashes: dict[str, str], split_hash: str) -> None:
    """Write a small immutable selection audit; candidate ledgers stay outside Git."""
    payload = {"run_id": run_id, "config": config.__dict__, "data_hashes": data_hashes, "split_hash": split_hash,
               "audit": result.audit, "selected": list(result.selected)}
    Path(path).write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")


def metrics_from_returns(returns: Iterable[float], cost_per_trade: float) -> CandidateMetrics:
    net = np.asarray(tuple(returns), dtype=float) - float(cost_per_trade)
    if net.ndim != 1 or not len(net):
        raise ValueError("returns must contain at least one trade")
    wins = net[net > 0].sum()
    losses = -net[net < 0].sum()
    equity = np.cumprod(1.0 + net)
    peaks = np.maximum.accumulate(np.r_[1.0, equity])[1:]
    max_dd = float(np.max(1.0 - equity / peaks)) if len(equity) else 0.0
    return CandidateMetrics(len(net), float(net.sum()), float(net.mean()), float(wins / losses) if losses else inf, max_dd)


def select_candidates(candidates: Iterable[dict], config: SelectionConfig) -> SelectionResult:
    """Deduplicate by canonical hash, gate, sort, and return an attrition audit."""
    rows = tuple(candidates)
    unique: dict[str, CandidateMetrics] = {}
    duplicates = 0
    for candidate in rows:
        key = str(candidate["canonical_hash"])
        metrics = candidate["metrics"]
        if key in unique:
            duplicates += 1
            if _rank_key(metrics, key) > _rank_key(unique[key], key):
                unique[key] = metrics
        else:
            unique[key] = metrics
    eligible = {key: metrics for key, metrics in unique.items()
                if metrics.n_trades >= config.min_trades and metrics.mean_r > config.min_mean_r
                and metrics.profit_factor >= config.min_profit_factor}
    ordered = sorted(eligible, key=lambda key: _rank_key(eligible[key], key), reverse=True)
    pair_by_key = {str(c["canonical_hash"]): str(c.get("pair", "unknown")) for c in rows}
    pair_cap = max(1, int(np.floor(config.top_k * config.max_pair_fraction)))
    selected_list: list[str] = []
    pair_counts: dict[str, int] = {}
    rejected_concentration = 0
    for key in ordered:
        if len(selected_list) >= config.top_k:
            break
        pair = pair_by_key[key]
        if pair_counts.get(pair, 0) >= pair_cap:
            rejected_concentration += 1
            continue
        selected_list.append(key)
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    selected = tuple(selected_list)
    return SelectionResult(selected, unique, {"input": len(rows), "unique": len(unique), "rejected_duplicate": duplicates,
                                               "eligible": len(eligible), "selected": len(selected),
                                               "rejected_concentration": rejected_concentration})


def _rank_key(metrics: CandidateMetrics, key: str) -> tuple[float, float, float, float, str]:
    return metrics.mean_r, metrics.profit_factor, -metrics.max_dd, float(metrics.n_trades), key
