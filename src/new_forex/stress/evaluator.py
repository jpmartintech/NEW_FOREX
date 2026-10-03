"""Causal P05 stress evaluation on frozen strategies and original candles."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

from new_forex.backtest.evaluator import ExecData, Market, derive_metrics, evaluate_oracle, evaluate_rich, trades_frame
from new_forex.backtest.semantics import TRADE_FIELDS
from new_forex.strategy.definition import StrategyDefinition


def evaluate_scenario(market: Market, strategy: StrategyDefinition, *, window: tuple[int, int],
                      cost_multiplier: float = 1.0, m15_delay_bars: int = 0,
                      variable_slippage: bool = False, price_perturbation: bool = False,
                      slippage_min_pips: float = 0.25, slippage_max_pips: float = 1.0,
                      range_cap_pips: float = 20.0, perturbation_amplitude: float = 0.0002,
                      perturbation_period_m15: int = 96) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run one stress scenario through the existing backtester/oracle.

    The signal/features arrays remain those of ``market``. Only execution
    candles, execution timing and declared costs are changed. M15 delay is
    applied to the first execution bar inside the next H1 bar, not as an H1
    delay and not by shifting an existing ledger.
    """
    if m15_delay_bars < 0 or m15_delay_bars > 2:
        raise ValueError("P05 M15 delay must be 0, 1 or 2 bars")
    exec_data = market.execs["M15"]
    stressed_exec = exec_data
    if price_perturbation:
        stressed_exec = _perturb_execution(exec_data, perturbation_amplitude, perturbation_period_m15)
    if m15_delay_bars:
        shifted = stressed_exec.h1_start + int(m15_delay_bars)
        valid = shifted < stressed_exec.h1_end
        shifted = np.where(valid, shifted, stressed_exec.h1_start)
        stressed_exec = replace(stressed_exec, h1_start=shifted)
    rel = _variable_slippage(market, slippage_min_pips, slippage_max_pips, range_cap_pips) if variable_slippage else None
    tradable = market.tradable.copy()
    if m15_delay_bars:
        valid_signal = np.ones(market.n_h1, dtype=bool)
        entry_h1 = np.arange(market.n_h1, dtype=np.int64) + 1
        valid_signal[:-1] = (stressed_exec.h1_start[entry_h1[:-1]] < stressed_exec.h1_end[entry_h1[:-1]])
        valid_signal[-1] = False
        tradable &= valid_signal
    stressed = replace(market, tradable=tradable, execs={**market.execs, "M15": stressed_exec}, cost_rel=rel)
    if not m15_delay_bars and not price_perturbation and not variable_slippage:
        rich = evaluate_rich(stressed, strategy, exec_tf="M15", cost_multiplier=cost_multiplier, window=window)
        return rich.trades, rich.metrics
    raw, agg = evaluate_oracle(stressed, strategy, exec_tf="M15", cost_multiplier=cost_multiplier, window=window)
    rec = np.asarray([[trade[field] for field in TRADE_FIELDS] for trade in raw], dtype=float)
    trades = trades_frame(stressed, rec) if len(rec) else trades_frame(stressed, np.empty((0, len(TRADE_FIELDS))))
    return trades, derive_metrics(agg, stressed.days_per_year)


def _variable_slippage(market: Market, minimum: float, maximum: float, cap: float) -> np.ndarray:
    if minimum < 0 or maximum < minimum or cap <= 0:
        raise ValueError("invalid variable slippage policy")
    h1 = market.h1
    pip = market.costs.pip
    range_pips = (h1["high"].to_numpy(float) - h1["low"].to_numpy(float)) / pip
    fraction = np.clip(range_pips / cap, 0.0, 1.0)
    extra_round_trip = 2.0 * (minimum + (maximum - minimum) * fraction) * pip
    close = h1["close"].to_numpy(float)
    return extra_round_trip / close


def _perturb_execution(ex: ExecData, amplitude: float, period: int) -> ExecData:
    if amplitude < 0 or period < 1:
        raise ValueError("invalid price perturbation policy")
    phase = amplitude * np.sin(2.0 * np.pi * np.arange(len(ex.o), dtype=float) / period)
    factor = 1.0 + phase
    return replace(ex, o=ex.o * factor, h=ex.h * factor, l=ex.l * factor, c=ex.c * factor)
