"""Reconcile and decompose the frozen P12D.3 portfolio ledgers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/p12e_loss_decomposition.yaml"
P12D = ROOT / "reports/p12d_3_artifacts"
OUT = ROOT / "reports/p12e_artifacts"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portfolio_sweep(selected: list[str], ledgers: dict[str, pd.DataFrame], risk: float, cap: float) -> tuple[dict, list[dict]]:
    """Replay the P12D.3 event sweep, retaining gross/net accounting and diagnostics."""
    events = []
    for strategy_hash in selected:
        frame = ledgers.get(strategy_hash, pd.DataFrame())
        for row_id, row in enumerate(frame.itertuples(index=False)):
            cost_r = float(row.transaction_cost) / float(row.risk) if float(row.risk) else 0.0
            gross_r = float(row.result_R) + cost_r
            entry = pd.Timestamp(row.entry_timestamp)
            exit_time = pd.Timestamp(row.exit_timestamp)
            uid = f"{strategy_hash}:{row_id}"
            same_bar = entry == exit_time
            payload = {"uid": uid, "strategy_hash": strategy_hash, "direction": row.direction,
                       "entry_timestamp": entry, "exit_timestamp": exit_time, "result_R": float(row.result_R),
                       "gross_R": gross_r, "transaction_cost": float(row.transaction_cost),
                       "signal_timestamp": pd.Timestamp(row.signal_timestamp), "risk": float(row.risk)}
            events.append((entry, 0 if same_bar else 1, strategy_hash, 1, payload))
            events.append((exit_time, 1 if same_bar else 0, strategy_hash, 0, payload))
    events.sort(key=lambda item: (item[0], item[1], item[2], item[4]["uid"]))
    equity = 1.0
    gross_equity = 1.0
    active: dict[str, tuple[dict, float, float]] = {}
    blocked: set[str] = set()
    trades: list[dict] = []
    gross_pnl = net_pnl = cost_drag = 0.0
    blocked_count = 0
    simultaneous_loss_exits = 0
    max_concurrent = 0
    for timestamp, _priority, _strategy_hash, kind, payload in events:
        uid = payload["uid"]
        if kind == 1:
            if uid in blocked:
                continue
            if (len(active) + 1) * risk > cap + 1e-12:
                blocked.add(uid)
                blocked_count += 1
                continue
            active[uid] = (payload, equity, gross_equity)
            max_concurrent = max(max_concurrent, len(active))
            continue
        if uid in blocked:
            continue
        opened = active.pop(uid, None)
        if opened is None:
            raise ValueError("exit without active portfolio position")
        trade, entry_equity, gross_entry_equity = opened
        net_trade_pnl = entry_equity * risk * trade["result_R"]
        gross_trade_pnl_at_net_path = entry_equity * risk * trade["gross_R"]
        gross_trade_pnl = gross_entry_equity * risk * trade["gross_R"]
        cost_trade_pnl = gross_trade_pnl_at_net_path - net_trade_pnl
        simultaneous_loss_exits += int(trade["result_R"] < 0 and any(item[0]["result_R"] < 0 for item in active.values()))
        net_pnl += net_trade_pnl
        gross_pnl += gross_trade_pnl
        cost_drag += cost_trade_pnl
        equity += net_trade_pnl
        gross_equity += gross_trade_pnl
        trades.append({**trade, "exit_timestamp": timestamp, "entry_equity": entry_equity,
                       "gross_entry_equity": gross_entry_equity, "net_pnl": net_trade_pnl,
                       "gross_pnl": gross_trade_pnl, "gross_pnl_at_net_path": gross_trade_pnl_at_net_path,
                       "cost_drag_pnl": cost_trade_pnl, "portfolio_equity": equity,
                       "other_open_positions_at_exit": len(active),
                       "other_open_losses_at_exit": sum(item[0]["result_R"] < 0 for item in active.values())})
    if active:
        raise ValueError("portfolio contains open positions after forward window")
    net_returns = [row["portfolio_equity"] for row in trades]
    peaks = np.maximum.accumulate(net_returns) if net_returns else np.asarray([1.0])
    net_dd = float((1.0 - np.asarray(net_returns) / peaks).max()) if net_returns else 0.0
    result_array = np.asarray([row["result_R"] for row in trades], dtype=float)
    gross_array = np.asarray([row["gross_R"] for row in trades], dtype=float)
    wins = result_array[result_array > 0].sum()
    losses = -result_array[result_array < 0].sum()
    return ({"n_trades": len(trades), "gross_return_at_net_path": float(net_pnl + cost_drag),
             "net_return": float(net_pnl), "gross_return_capitalized": float(gross_equity - 1.0),
             "cost_drag_capitalized_at_net_path": float(cost_drag), "cost_price_total": float(sum(row["transaction_cost"] for row in trades)),
             "cost_per_operation_price": float(np.mean([row["transaction_cost"] for row in trades])) if trades else 0.0,
             "cost_per_operation_R": float(np.mean([row["transaction_cost"] / row["risk"] for row in trades])) if trades else 0.0,
             "gross_expectancy_R": float(gross_array.mean()) if trades else 0.0, "net_expectancy_R": float(result_array.mean()) if trades else 0.0,
             "gross_positive_fraction": float((gross_array > 0).mean()) if trades else 0.0,
             "net_positive_fraction": float((result_array > 0).mean()) if trades else 0.0,
             "profit_factor_net": float(wins / losses) if losses else (float("inf") if wins > 0 else 0.0),
             "max_drawdown_net": net_dd, "max_concurrent_positions": max_concurrent,
             "blocked_signals": blocked_count, "simultaneous_loss_exits": simultaneous_loss_exits,
             "active_strategies": len({row["strategy_hash"] for row in trades}),
             "gross_positive_net_negative": bool(gross_array.sum() > 0 and result_array.sum() < 0) if trades else False}, trades)


def load_ledgers(label: str, cost: str) -> dict[str, pd.DataFrame]:
    frame = pd.read_parquet(P12D / f"ledgers_{label}_{cost}.parquet")
    return {key: part.drop(columns=["strategy_hash"]).reset_index(drop=True) for key, part in frame.groupby("strategy_hash", sort=False)}


def drawdown(values: pd.Series) -> float:
    if values.empty:
        return 0.0
    curve = np.cumprod(1.0 + values.to_numpy(float))
    return float((1.0 - curve / np.maximum.accumulate(curve)).max())


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_bytes())
    OUT.mkdir(parents=True, exist_ok=True)
    chunks = OUT / "chunks"
    chunks.mkdir(parents=True, exist_ok=True)
    compositions = pd.DataFrame(json.loads(line) for line in (P12D / "compositions.jsonl").read_text().splitlines())
    p12d_portfolios = pd.read_csv(P12D / "portfolio_results.csv")
    results: list[dict] = []
    for label in config["evaluation"]["generations"]:
        generation_compositions = compositions[compositions.generation == label]
        for cost in config["evaluation"]["costs"]:
            ledgers = load_ledgers(label, cost)
            trade_rows: list[dict] = []
            period_rows: list[dict] = []
            strategy_rows: list[dict] = []
            for row in generation_compositions.itertuples(index=False):
                metrics, trades = portfolio_sweep(row.selected, ledgers, config["evaluation"]["risk_per_trade"], config["evaluation"]["max_aggregate_risk"])
                identity = {"generation": label, "group": row.group, "replicate": row.replicate, "cost": cost}
                original = p12d_portfolios[(p12d_portfolios.generation == label) & (p12d_portfolios.group == row.group) & (p12d_portfolios.replicate == row.replicate) & (p12d_portfolios.cost == cost)]
                if len(original) != 1 or not np.isclose(metrics["net_return"], float(original.iloc[0]["return"]), atol=1e-10):
                    raise ValueError(f"{label}/{row.group}/{row.replicate}/{cost}: P12D.3 return mismatch")
                results.append({**identity, **metrics, "p12d3_return": float(original.iloc[0]["return"]), "p12d3_max_drawdown": float(original.iloc[0]["max_drawdown"])})
                for trade in trades:
                    trade_rows.append({**identity, **trade})
                if trades:
                    trade_frame = pd.DataFrame(trades)
                    exit_local = trade_frame.exit_timestamp.dt.tz_localize(None)
                    for period_name, period in (("quarter", exit_local.dt.to_period("Q")), ("month", exit_local.dt.to_period("M")), ("week", exit_local.dt.to_period("W"))):
                        grouped = trade_frame.assign(period=period).groupby("period", observed=True)
                        for period_value, part in grouped:
                            period_rows.append({**identity, "period_type": period_name, "period": str(period_value), "n_trades": len(part), "net_pnl": part.net_pnl.sum(), "gross_pnl_at_net_path": part.gross_pnl_at_net_path.sum(), "cost_drag_pnl": part.cost_drag_pnl.sum(), "loss_pnl": part.loc[part.net_pnl < 0, "net_pnl"].sum()})
                    for strategy_hash, part in trade_frame.groupby("strategy_hash"):
                        strategy_rows.append({**identity, "strategy_hash": strategy_hash, "n_trades": len(part), "net_pnl": part.net_pnl.sum(), "gross_pnl_at_net_path": part.gross_pnl_at_net_path.sum(), "cost_drag_pnl": part.cost_drag_pnl.sum(), "long_fraction": (part.direction == "LONG").mean(), "loss_fraction": (part.net_pnl < 0).mean()})
            pd.DataFrame(trade_rows).to_parquet(chunks / f"trades_{label}_{cost}.parquet", index=False)
            pd.DataFrame(period_rows).to_parquet(chunks / f"periods_{label}_{cost}.parquet", index=False)
            pd.DataFrame(strategy_rows).to_parquet(chunks / f"strategies_{label}_{cost}.parquet", index=False)
    result_frame = pd.DataFrame(results)
    trade_frame = pd.concat([pd.read_parquet(path) for path in sorted(chunks.glob("trades_*.parquet"))], ignore_index=True)
    period_frame = pd.concat([pd.read_parquet(path) for path in sorted(chunks.glob("periods_*.parquet"))], ignore_index=True)
    strategy_frame = pd.concat([pd.read_parquet(path) for path in sorted(chunks.glob("strategies_*.parquet"))], ignore_index=True)
    period_frame.to_csv(OUT / "period_decomposition.csv", index=False)
    strategy_frame.to_csv(OUT / "strategy_decomposition.csv", index=False)
    trade_frame.to_parquet(OUT / "executed_trades.parquet", index=False)
    result_frame.to_csv(OUT / "portfolio_decomposition.csv", index=False)
    rolling_rows = []
    for (group, cost, replicate), part in result_frame.groupby(["group", "cost", "replicate"]):
        part = part.sort_values("generation")
        curve_net = np.cumprod(1.0 + part.net_return.to_numpy(float))
        curve_gross = np.cumprod(1.0 + part.gross_return_capitalized.to_numpy(float))
        rolling_rows.append({"group": group, "cost": cost, "replicate": replicate, "gross_return": curve_gross[-1] - 1.0, "net_return": curve_net[-1] - 1.0, "cost_drag": (curve_gross[-1] - curve_net[-1]), "max_drawdown": float((1.0 - curve_net / np.maximum.accumulate(curve_net)).max()), "positive": bool(curve_net[-1] > 1.0), "n_trades": int(part.n_trades.sum()), "generations_positive": int((part.net_return > 0).sum())})
    pd.DataFrame(rolling_rows).to_csv(OUT / "rolling_decomposition.csv", index=False)
    manifest = {"policy_id": config["policy_id"], "config_sha256": sha256(CONFIG_PATH), "source_artifacts": config["source_artifacts"], "portfolio_rows": len(result_frame), "trade_rows": len(trade_frame), "period_rows": len(period_frame), "strategy_rows": len(strategy_frame), "rolling_rows": len(rolling_rows), "holdout_used": False, "components_separately_identified": False}
    (OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
