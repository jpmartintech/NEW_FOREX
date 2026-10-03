from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import yaml

_SPEC = importlib.util.spec_from_file_location(
    "p12e_runner", Path(__file__).parents[1] / "scripts/run_p12e_loss_decomposition.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)
portfolio_sweep = _MODULE.portfolio_sweep


def _ledger(result_r: float, cost: float = 0.00015, start: str = "2019-01-01") -> pd.DataFrame:
    entry = pd.Timestamp(start, tz="UTC")
    exit_time = entry + pd.Timedelta(hours=1)
    return pd.DataFrame([{
        "entry_timestamp": entry,
        "exit_timestamp": exit_time,
        "signal_timestamp": entry - pd.Timedelta(hours=1),
        "direction": "LONG",
        "result_R": result_r,
        "transaction_cost": cost,
        "risk": 0.001,
    }])


def test_gross_net_cost_identity_and_reconciliation() -> None:
    metrics, trades = portfolio_sweep(["a"], {"a": _ledger(1.0)}, 0.005, 0.025)
    assert len(trades) == 1
    assert metrics["net_return"] == 0.005
    assert metrics["gross_return_at_net_path"] == metrics["net_return"] + metrics["cost_drag_capitalized_at_net_path"]
    assert metrics["gross_return_capitalized"] > metrics["net_return"]


def test_capitalization_is_sequential_not_a_sum() -> None:
    first = _ledger(1.0, start="2019-01-01")
    second = _ledger(-0.5, start="2019-01-02")
    metrics, _ = portfolio_sweep(["a", "b"], {"a": first, "b": second}, 0.005, 0.025)
    expected = (1.0 + 0.005) * (1.0 - 0.0025) - 1.0
    assert abs(metrics["net_return"] - expected) < 1e-12
    assert metrics["net_return"] != 0.005 - 0.0025


def test_p12e_protocol_is_frozen_without_holdout() -> None:
    config = yaml.safe_load(open("configs/p12e_loss_decomposition.yaml"))
    assert config["frozen_rule"] == {"training_profit_factor_gte": 1.05, "training_n_trades_gte": 100}
    assert config["diagnostics"]["holdout_used"] is False
    assert config["evaluation"]["no_resampling"] is True
