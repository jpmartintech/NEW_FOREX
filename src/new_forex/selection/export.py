"""Auditable handoff from P03 selection to P04 trade ledgers.

This module deliberately accepts prepared ``Market`` objects and calls
``evaluate_rich`` for every finalist. It never reconstructs trades from
aggregate metrics and never loads data itself, so the caller remains
responsible for using the authorised pre-holdout data loader.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from new_forex.backtest.evaluator import Market, evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import code_version, file_sha256
from new_forex.selection.ranking import SelectionConfig, SelectionResult
from new_forex.strategy.definition import StrategyDefinition

REQUIRED_TRADE_COLUMNS = (
    "strategy_hash", "symbol", "direction", "entry_timestamp", "exit_timestamp", "entry_price", "exit_price",
    "pnl_net", "result_R", "transaction_cost",
)


@dataclass(frozen=True)
class ExportConfig:
    """Immutable execution and provenance settings for one P03.1 export."""

    run_id: str
    partition: str = "dev_train"
    start: str = "2003-01-01 00:00:00"
    end: str = "2015-01-01 00:00:00"
    exec_timeframe: str = "M15"
    delay: int = 0
    cost_multiplier: float = 1.0
    funding_multiplier: float = 1.0

    def validate(self) -> Partition:
        policy = DataAccessPolicy.load()
        partition = policy.assert_range(self.start, self.end)
        if partition.value != self.partition:
            raise ValueError(f"export range belongs to {partition.value}, not {self.partition}")
        if partition is not Partition.DEV_TRAIN:
            raise ValueError("P03.1 finalist export is restricted to dev_train")
        if self.exec_timeframe not in {"H1", "M15"}:
            raise ValueError("exec_timeframe must be H1 or M15")
        if self.delay < 0:
            raise ValueError("delay must be non-negative")
        return partition


def export_finalists(
    result: SelectionResult,
    candidates: list[dict[str, Any]],
    strategies: dict[str, StrategyDefinition],
    markets: dict[str, Market],
    output_dir: Path,
    *,
    config: ExportConfig,
    selection_config: SelectionConfig,
    dataset_hashes: dict[str, str],
    split_hash: str,
    source_archive: Path | None = None,
) -> dict[str, Any]:
    """Export finalist manifest, candidate audit JSONL and real rich ledgers.

    ``markets`` must have been created from the canonical pre-holdout loader.
    The evaluation window is converted to H1 indices from each market, then
    the existing rich backtester produces every exported operation.
    """
    partition = config.validate()
    if not candidates:
        raise ValueError("P03 candidate rows are required; no synthetic candidates are allowed")
    selected = set(result.selected)
    if not selected:
        raise ValueError("P03 selected zero finalists; P04 remains blocked")
    missing = selected - strategies.keys()
    if missing:
        raise ValueError(f"missing strategy definitions for finalist hashes: {sorted(missing)}")

    root = Path(output_dir)
    trades_dir = root / "trades"
    trades_dir.mkdir(parents=True, exist_ok=True)
    audit_path = root / "selection_audit.jsonl"
    _write_selection_audit(audit_path, candidates, result, selection_config)

    manifest_finalists: list[dict[str, Any]] = []
    for strategy_hash in result.selected:
        strategy = strategies[strategy_hash]
        if strategy.canonical_hash != strategy_hash:
            raise ValueError(f"strategy hash mismatch for {strategy_hash}")
        market = markets.get(strategy.pair)
        if market is None:
            raise ValueError(f"missing prepared market for {strategy.pair}")
        window = _market_window(market, config.start, config.end)
        rich = evaluate_rich(market, strategy, exec_tf=config.exec_timeframe, delay=config.delay,
                             cost_multiplier=config.cost_multiplier, funding_multiplier=config.funding_multiplier,
                             window=window)
        ledger = _ledger_frame(rich.trades, strategy, market)
        validate_ledger(ledger, strategy, rich.metrics)
        path = trades_dir / f"{strategy_hash}.parquet"
        ledger.to_parquet(path, index=False)
        manifest_finalists.append({
            "strategy_hash": strategy_hash,
            "strategy": strategy.payload(),
            "pair": strategy.pair,
            "metrics": rich.metrics,
            "ledger": str(path.relative_to(root)),
            "ledger_sha256": file_sha256(path),
        })

    manifest = {
        "contract_version": "p03.1-v1",
        "run_id": config.run_id,
        "code_version": code_version(),
        "partition": partition.value,
        "period": {"start": config.start, "end": config.end},
        "dataset_hashes": dict(sorted(dataset_hashes.items())),
        "split_hash": split_hash,
        "config": asdict(config),
        "selection_config": asdict(selection_config),
        "source_archive": None if source_archive is None else str(source_archive),
        "finalists": manifest_finalists,
    }
    manifest["manifest_sha256"] = _json_digest(manifest)
    (root / "finalist_manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2, default=_json_default) + "\n")
    return manifest


def validate_ledger(ledger: pd.DataFrame, strategy: StrategyDefinition, metrics: dict[str, Any]) -> None:
    """Validate identity, causal ordering, uniqueness and aggregate consistency."""
    missing = set(REQUIRED_TRADE_COLUMNS) - set(ledger.columns)
    if missing:
        raise ValueError(f"ledger missing columns: {sorted(missing)}")
    if not (ledger["strategy_hash"] == strategy.canonical_hash).all():
        raise ValueError("ledger contains a strategy hash mismatch")
    if not (ledger["symbol"] == strategy.pair).all() or not (ledger["direction"] == strategy.direction).all():
        raise ValueError("ledger contains symbol or direction mismatch")
    entries = pd.to_datetime(ledger["entry_timestamp"], utc=True)
    exits = pd.to_datetime(ledger["exit_timestamp"], utc=True)
    if (exits < entries).any():
        raise ValueError("ledger contains an exit before entry")
    duplicate_keys = ["strategy_hash", "entry_timestamp", "exit_timestamp"]
    if not entries.is_monotonic_increasing or ledger.duplicated(subset=duplicate_keys).any():
        raise ValueError("ledger is not ordered or contains duplicate operations")
    if "signal_timestamp" in ledger and (pd.to_datetime(ledger["signal_timestamp"], utc=True) >= entries).any():
        raise ValueError("ledger contains a lookahead entry at or before its signal")
    if "entry_idx" in ledger and "signal_idx" in ledger and (ledger["entry_idx"] <= ledger["signal_idx"]).any():
        raise ValueError("ledger contains an entry at or before its signal index")
    if len(ledger) != int(metrics["n_trades"]):
        raise ValueError("ledger trade count disagrees with backtester metrics")
    if abs(float(ledger["result_R"].sum()) - float(metrics["total_r"])) > 1e-10:
        raise ValueError("ledger result_R sum disagrees with backtester metrics")


def _ledger_frame(trades: pd.DataFrame, strategy: StrategyDefinition, market: Market) -> pd.DataFrame:
    out = trades.copy()
    sign = strategy.sign
    # From the evaluator contract: R = (direction * price move - cost + funding) / risk.
    out["strategy_hash"] = strategy.canonical_hash
    out["symbol"] = strategy.pair
    out["direction"] = strategy.direction
    out["entry_timestamp"] = pd.to_datetime(out["entry_time"], utc=True)
    out["exit_timestamp"] = pd.to_datetime(out["exit_bar_time"], utc=True)
    out["pnl_net"] = sign * (out["exit_price"] - out["entry_price"]) + out["funding"] - out["r"] * out["risk"]
    out["result_R"] = out["r"]
    out["transaction_cost"] = sign * (out["exit_price"] - out["entry_price"]) + out["funding"] - out["r"] * out["risk"]
    # Keep provenance useful for audits without changing the required P04 input.
    out["signal_timestamp"] = pd.to_datetime(market.ts_utc[out["signal_idx"].to_numpy()], utc=True)
    columns = [*REQUIRED_TRADE_COLUMNS, "signal_timestamp", "entry_idx", "exit_idx", "reason", "risk", "funding"]
    return out.sort_values(["entry_timestamp", "exit_timestamp"], kind="stable")[columns].reset_index(drop=True)


def _market_window(market: Market, start: str, end: str) -> tuple[int, int]:
    local = market.h1["ts_local"].to_numpy()
    t0 = int(pd.Series(local).searchsorted(pd.Timestamp(start)))
    t1 = int(pd.Series(local).searchsorted(pd.Timestamp(end)))
    if t1 <= t0:
        raise ValueError(f"market has no bars in export period {start}..{end}")
    return t0, t1


def _write_selection_audit(path: Path, candidates: list[dict[str, Any]], result: SelectionResult,
                           config: SelectionConfig) -> None:
    selected = set(result.selected)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate["canonical_hash"])
        metrics = candidate["metrics"]
        if key in seen:
            decision, reason = "rejected", "duplicate_canonical_hash"
        elif metrics.n_trades < config.min_trades:
            decision, reason = "rejected", "min_trades"
        elif metrics.mean_r <= config.min_mean_r:
            decision, reason = "rejected", "min_mean_r"
        elif metrics.profit_factor < config.min_profit_factor:
            decision, reason = "rejected", "min_profit_factor"
        elif key in selected:
            decision, reason = "accepted", "selected"
        else:
            decision, reason = "rejected", "rank_or_pair_concentration"
        rows.append({"canonical_hash": key, "pair": candidate.get("pair", "unknown"), "metrics": asdict(metrics),
                     "decision": decision, "reason": reason})
        seen.add(key)
    with Path(path).open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True, default=_json_default, separators=(",", ":")) + "\n")


def _json_digest(value: dict[str, Any]) -> str:
    payload = {key: value[key] for key in value if key != "manifest_sha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=_json_default, separators=(",", ":")).encode()).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")
