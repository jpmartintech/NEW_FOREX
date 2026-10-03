"""P05 scenario and causal M15-delay contract tests."""
from __future__ import annotations

from conftest import make_config, synthetic_raw_m15
from new_forex.backtest.evaluator import Costs, build_market
from new_forex.data.m15 import canonicalize
from new_forex.strategy.definition import Predicate, StrategyDefinition
from new_forex.stress.evaluator import evaluate_scenario


def _market():
    return build_market("EURUSD", canonicalize(synthetic_raw_m15(n_weeks=60, seed=31), make_config()),
                        Costs(0.0001, 1.0, 0.25))


def _strategy():
    return StrategyDefinition("EURUSD", "LONG", (Predicate("momentum.rsi.14", ">", 50.0),), 1.0, 2.0, 10)


def test_m15_delay_is_execution_delay_and_keeps_signal_indices() -> None:
    market = _market()
    base, base_metrics = evaluate_scenario(market, _strategy(), window=(200, 500))
    delayed, delayed_metrics = evaluate_scenario(market, _strategy(), window=(200, 500), m15_delay_bars=1)
    assert base_metrics["n_trades"] >= delayed_metrics["n_trades"]
    if len(base) and len(delayed):
        assert delayed["signal_idx"].is_monotonic_increasing
        starts = market.execs["M15"].h1_start[delayed["signal_idx"].to_numpy() + 1]
        assert (delayed["entry_exec"].to_numpy() >= starts + 1).all()


def test_variable_slippage_is_finite_and_adverse_relative_to_baseline() -> None:
    market = _market()
    _, baseline = evaluate_scenario(market, _strategy(), window=(200, 500))
    _, stressed = evaluate_scenario(market, _strategy(), window=(200, 500), variable_slippage=True)
    assert stressed["n_trades"] == baseline["n_trades"]
    assert stressed["total_r"] <= baseline["total_r"] + 1e-10
