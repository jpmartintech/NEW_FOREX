"""Chronological P09 orchestration and portfolio consolidation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Generation:
    label: str
    birth: str
    forward_end: str
    index: int


def remaining_generations() -> tuple[Generation, ...]:
    quarters = pd.period_range("2019Q2", "2022Q4", freq="Q")
    return tuple(Generation(str(q), q.start_time.strftime("%Y-%m-%d"),
                            (q.start_time + pd.DateOffset(months=3)).strftime("%Y-%m-%d"), i)
                 for i, q in enumerate(quarters, start=1))


def portfolio_ledger(ledgers: list[tuple[str, pd.DataFrame]], *, risk_per_trade: float = 0.005,
                     max_aggregate_risk: float = 0.025) -> pd.DataFrame:
    """Simulate exits on one equity curve while accounting for overlapping entries."""
    rows: list[dict[str, Any]] = []
    for strategy_hash, frame in ledgers:
        for row in frame.to_dict(orient="records"):
            rows.append({"strategy_hash": strategy_hash, "entry_timestamp": pd.Timestamp(row["entry_timestamp"]),
                         "exit_timestamp": pd.Timestamp(row["exit_timestamp"]), "result_R": float(row["result_R"])})
    if not rows:
        return pd.DataFrame(columns=["strategy_hash", "entry_timestamp", "exit_timestamp", "result_R", "pnl", "equity"])
    frame = pd.DataFrame(rows).sort_values(["entry_timestamp", "exit_timestamp", "strategy_hash"], kind="stable")
    keys = ["strategy_hash", "entry_timestamp", "exit_timestamp"]
    if frame.duplicated(keys).any():
        raise ValueError("duplicate forward operation in portfolio consolidation")
    active: dict[int, float] = {}
    equity = 1.0
    output: list[dict[str, Any]] = []
    events = []
    for i, row in frame.iterrows():
        same_bar = row.entry_timestamp == row.exit_timestamp
        events.append((row.entry_timestamp, 0 if same_bar else 1, i, 1))
        events.append((row.exit_timestamp, 1 if same_bar else 0, i, 0))
    events.sort()
    for timestamp, _priority, index, kind in events:
        row = frame.loc[index]
        if kind == 1:
            if (len(active) + 1) * risk_per_trade > max_aggregate_risk + 1e-12:
                raise ValueError("portfolio aggregate risk cap exceeded")
            active[index] = equity
        else:
            entry_equity = active.pop(index, None)
            if entry_equity is None:
                raise ValueError("exit without active portfolio position")
            pnl = entry_equity * risk_per_trade * float(row.result_R)
            equity += pnl
            output.append({"strategy_hash": row.strategy_hash, "entry_timestamp": row.entry_timestamp,
                           "exit_timestamp": row.exit_timestamp, "result_R": row.result_R,
                           "pnl": pnl, "equity": equity, "timestamp": timestamp})
    if active:
        raise ValueError("portfolio contains open positions after forward window")
    return pd.DataFrame(output).sort_values("timestamp", kind="stable").reset_index(drop=True)


def portfolio_metrics(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"n_trades": 0, "pnl": 0.0, "return": 0.0, "max_drawdown": 0.0, "active_strategies": 0}
    equity = frame["equity"].to_numpy(float)
    peaks = np.maximum.accumulate(equity)
    return {"n_trades": int(len(frame)), "pnl": float(frame["pnl"].sum()), "return": float(equity[-1] - 1.0),
            "max_drawdown": float((1.0 - equity / peaks).max()),
            "active_strategies": int(frame["strategy_hash"].nunique())}


def checkpoint_path(root: Path) -> Path:
    return Path(root) / "checkpoint.json"
