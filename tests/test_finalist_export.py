"""P03.1 export contract tests; all markets are synthetic and no artefact is treated as a finalist run."""
from __future__ import annotations

import pandas as pd
import pytest

from new_forex.data.splits import FinalHoldoutSealed
from new_forex.selection.export import ExportConfig, validate_ledger
from new_forex.strategy.definition import Predicate, StrategyDefinition


def strategy() -> StrategyDefinition:
    return StrategyDefinition("EURUSD", "LONG", (Predicate("momentum.rsi.14", ">", 50),), 1.0, 2.0, 10)


def test_export_config_rejects_holdout_before_any_backtest() -> None:
    with pytest.raises(FinalHoldoutSealed):
        ExportConfig("p03.1-test", start="2023-01-01", end="2023-02-01").validate()


def test_export_config_rejects_non_selection_partition() -> None:
    with pytest.raises(ValueError, match="restricted to dev_train"):
        ExportConfig("p03.1-test", start="2015-01-01", end="2015-02-01", partition="development_wf").validate()


def test_validate_ledger_rejects_duplicate_and_metric_mismatch() -> None:
    s = strategy()
    frame = pd.DataFrame({
        "strategy_hash": [s.canonical_hash], "symbol": ["EURUSD"], "direction": ["LONG"],
        "entry_timestamp": ["2010-01-01T00:00:00Z"], "exit_timestamp": ["2010-01-01T01:00:00Z"],
        "entry_price": [1.0], "exit_price": [1.01], "pnl_net": [0.01], "result_R": [0.5],
        "transaction_cost": [0.0],
    })
    with pytest.raises(ValueError, match="trade count"):
        validate_ledger(frame, s, {"n_trades": 2, "total_r": 1.0})


def test_validate_ledger_accepts_backtester_shaped_row() -> None:
    s = strategy()
    frame = pd.DataFrame({
        "strategy_hash": [s.canonical_hash], "symbol": ["EURUSD"], "direction": ["LONG"],
        "entry_timestamp": ["2010-01-01T00:00:00Z"], "exit_timestamp": ["2010-01-01T01:00:00Z"],
        "entry_price": [1.0], "exit_price": [1.01], "pnl_net": [0.005], "result_R": [0.5],
        "transaction_cost": [0.005],
    })
    validate_ledger(frame, s, {"n_trades": 1, "total_r": 0.5})
