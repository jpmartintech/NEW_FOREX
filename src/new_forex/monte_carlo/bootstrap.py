"""Trade and block bootstrap risk simulation."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MonteCarloConfig:
    iterations: int = 5_000
    seed: int = 0
    block_length: int = 20
    method: str = "moving"
    ruin_floor: float = 0.5

    def __post_init__(self) -> None:
        if self.iterations < 5_000:
            raise ValueError("iterations must be at least 5000")
        if self.block_length < 1:
            raise ValueError("block_length must be positive")
        if self.method not in {"moving", "stationary"}:
            raise ValueError("method must be moving or stationary")
        if not 0 < self.ruin_floor <= 1:
            raise ValueError("ruin_floor must be in (0, 1]")


@dataclass(frozen=True)
class MonteCarloResult:
    final_equity: np.ndarray
    max_drawdown: np.ndarray
    longest_loss_streak: np.ndarray
    ruin_probability: float
    quantiles: dict[str, float]


def run_monte_carlo(returns: np.ndarray, config: MonteCarloConfig) -> MonteCarloResult:
    """Resample a time-ordered trade return series with moving/stationary blocks."""
    source = np.asarray(returns, dtype=float)
    if source.ndim != 1 or len(source) < 2 or not np.isfinite(source).all():
        raise ValueError("returns must be a finite one-dimensional series with at least two values")
    if (source <= -1).any():
        raise ValueError("returns must be greater than -1")
    rng = np.random.default_rng(config.seed)
    final = np.empty(config.iterations)
    drawdown = np.empty(config.iterations)
    streak = np.empty(config.iterations, dtype=np.int64)
    for i in range(config.iterations):
        idx = _block_indices(rng, len(source), config.block_length, config.method)
        equity = np.cumprod(1.0 + source[idx])
        peaks = np.maximum.accumulate(np.r_[1.0, equity])[1:]
        final[i] = equity[-1]
        drawdown[i] = np.max(1.0 - equity / peaks)
        streak[i] = _longest_loss_streak(source[idx])
    ruin = (final <= config.ruin_floor) | (drawdown >= 1.0)
    quantiles = {
        "dd_p50": float(np.quantile(drawdown, 0.50)),
        "dd_p95": float(np.quantile(drawdown, 0.95)),
        "dd_p99": float(np.quantile(drawdown, 0.99)),
        "final_equity_p50": float(np.quantile(final, 0.50)),
        "final_equity_p05": float(np.quantile(final, 0.05)),
        "longest_loss_streak_p95": float(np.quantile(streak, 0.95)),
    }
    return MonteCarloResult(final, drawdown, streak, float(np.mean(ruin)), quantiles)


def run_period_block_monte_carlo(returns: np.ndarray, period_ids: np.ndarray, config: MonteCarloConfig) -> MonteCarloResult:
    """Resample complete ordered periods (e.g. months or years) with replacement."""
    source = np.asarray(returns, dtype=float)
    periods = np.asarray(period_ids)
    if source.ndim != 1 or len(source) < 2 or len(source) != len(periods) or not np.isfinite(source).all():
        raise ValueError("returns and period_ids must be aligned finite one-dimensional arrays")
    groups = [np.flatnonzero(periods == period) for period in dict.fromkeys(periods)]
    rng = np.random.default_rng(config.seed)
    final = np.empty(config.iterations)
    drawdown = np.empty(config.iterations)
    streak = np.empty(config.iterations, dtype=np.int64)
    for i in range(config.iterations):
        chosen = rng.integers(len(groups), size=len(groups))
        indices = np.concatenate([groups[index] for index in chosen])
        equity = np.cumprod(1.0 + source[indices])
        peaks = np.maximum.accumulate(np.r_[1.0, equity])[1:]
        final[i] = equity[-1]
        drawdown[i] = np.max(1.0 - equity / peaks)
        streak[i] = _longest_loss_streak(source[indices])
    ruin = (final <= config.ruin_floor) | (drawdown >= 1.0)
    return MonteCarloResult(
        final, drawdown, streak, float(np.mean(ruin)),
        {"dd_p50": float(np.quantile(drawdown, 0.50)), "dd_p95": float(np.quantile(drawdown, 0.95)),
         "dd_p99": float(np.quantile(drawdown, 0.99)), "final_equity_p50": float(np.quantile(final, 0.50)),
         "final_equity_p05": float(np.quantile(final, 0.05)),
         "longest_loss_streak_p95": float(np.quantile(streak, 0.95))},
    )


def _block_indices(rng: np.random.Generator, n: int, block: int, method: str) -> np.ndarray:
    out = np.empty(n, dtype=np.int64)
    pos = 0
    start = int(rng.integers(n))
    while pos < n:
        if pos == 0 or method == "moving" or rng.random() < 1.0 / block:
            start = int(rng.integers(n))
        length = min(block if method == "moving" else int(rng.geometric(1.0 / block)), n - pos)
        out[pos:pos + length] = (start + np.arange(length)) % n
        pos += length
        start = (start + length) % n
    return out


def _longest_loss_streak(returns: np.ndarray) -> int:
    current = 0
    longest = 0
    for value in returns:
        current = current + 1 if value < 0 else 0
        longest = max(longest, current)
    return longest
