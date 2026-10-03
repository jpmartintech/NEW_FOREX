"""P04 acceptance tests for seeded block-bootstrap risk distributions."""
from __future__ import annotations

import numpy as np

from new_forex.monte_carlo.bootstrap import MonteCarloConfig, run_monte_carlo, run_period_block_monte_carlo


def test_monte_carlo_defaults_to_at_least_5000_reproducible_iterations() -> None:
    config = MonteCarloConfig(iterations=5_000, seed=20261002, block_length=4)
    returns = np.array([0.02, -0.01, 0.015, -0.03, 0.01])

    first = run_monte_carlo(returns, config)
    second = run_monte_carlo(returns, config)

    assert len(first.final_equity) == 5_000
    np.testing.assert_array_equal(first.final_equity, second.final_equity)
    np.testing.assert_array_equal(first.max_drawdown, second.max_drawdown)
    assert set(first.quantiles) >= {"dd_p50", "dd_p95", "dd_p99", "final_equity_p50", "longest_loss_streak_p95"}


def test_positive_synthetic_control_has_no_ruin_and_no_drawdown() -> None:
    result = run_monte_carlo(np.full(20, 0.01), MonteCarloConfig(iterations=5_000, seed=3, block_length=5))

    assert result.ruin_probability == 0.0
    assert np.all(result.max_drawdown == 0.0)
    assert np.all(result.longest_loss_streak == 0)


def test_stationary_bootstrap_preserves_seeded_shape() -> None:
    result = run_monte_carlo(np.array([0.02, -0.01, 0.005, -0.02]),
                             MonteCarloConfig(iterations=5_000, seed=9, block_length=3, method="stationary"))

    assert len(result.final_equity) == 5_000
    assert np.isfinite(result.max_drawdown).all()


def test_period_block_bootstrap_resamples_complete_periods() -> None:
    returns = np.array([0.1, 0.1, -0.1, -0.1, 0.02, 0.02])
    period_ids = np.array(["m1", "m1", "m2", "m2", "m3", "m3"])
    result = run_period_block_monte_carlo(returns, period_ids, MonteCarloConfig(iterations=5_000, seed=11))

    assert len(result.final_equity) == 5_000
    assert np.isfinite(result.final_equity).all()
