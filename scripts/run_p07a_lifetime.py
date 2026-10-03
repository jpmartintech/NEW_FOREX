"""Descriptive lifetime analysis for the frozen P07 strategy."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

from new_forex.backtest.evaluator import Costs, build_market, evaluate_rich
from new_forex.data.splits import DataAccessPolicy, Partition
from new_forex.provenance import PROJECT_ROOT, code_version, file_sha256
from new_forex.strategy.definition import StrategyDefinition

STRATEGY_HASH = "237d10ee505b9bf528a2036d30babb26db137e9de3852a8bb116f73799798ebd"
EXPECTED_DATA_SHA256 = "29e4b0148de66dae4a23dabb9464365ce68bfcf0901de9cf4037b33ad731adf4"
MANIFEST = PROJECT_ROOT / "runs" / "p02-p04-eurusd-real-100k-clean-final" / "p03.1_export" / "finalist_manifest.json"
P04_REPORT = PROJECT_ROOT / "runs" / "p02-p04-eurusd-real-100k-clean-final" / "p04_report.json"
P07_REPORT = PROJECT_ROOT / "runs" / "p07-eurusd-procedure-validation-v1" / "p07_report.json"
HORIZONS = (3, 6, 9, 12, 18, 24, 36, 48)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    access = DataAccessPolicy.load()
    if access.assert_range("2019-01-01", "2023-01-01") is not Partition.PROCEDURE_VALIDATION:
        raise ValueError("P07A range is not procedure_validation")
    strategy = _load_strategy()
    market = _load_market_before_holdout()
    window = _window(market, "2019-01-01", "2023-01-01")
    baseline = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=1.0, window=window)
    costs_x2 = evaluate_rich(market, strategy, exec_tf="M15", cost_multiplier=2.0, window=window)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    base_trades = _trade_frame(baseline.trades, costs_x2.trades)
    horizons = _horizon_rows(base_trades)
    quarters = _quarter_rows(base_trades)
    curve = _curve(base_trades)
    _write_csv(output / "horizons.csv", horizons)
    _write_csv(output / "quarters.csv", quarters)
    _write_csv(output / "operations.csv", curve)
    _plot_equity(output / "equity.svg", curve)
    _plot_metrics(output / "rolling_expectancy.svg", curve)
    summary = {
        "contract_version": "p07a-lifetime-v1", "run_id": output.name, "code_version": code_version(),
        "strategy_hash": STRATEGY_HASH, "birth_date": "2019-01-01", "partition": "procedure_validation",
        "period": {"start": "2019-01-01", "end": "2023-01-01"}, "horizons_months": list(HORIZONS),
        "dataset_sha256": EXPECTED_DATA_SHA256, "manifest_sha256": file_sha256(MANIFEST),
        "p04_report_sha256": file_sha256(P04_REPORT), "p07_report_sha256": file_sha256(P07_REPORT),
        "rows_at_or_after_2023_loaded": 0, "holdout_used": False,
        "p04_comparison": {"status": "NOT_STATISTICALLY_COMPARABLE",
                            "reason": "P04 bootstrap distributions use a different multi-year selected-trade horizon and are selection-conditioned"},
        "first_cumulative_expectancy_negative": _first_negative(curve),
        "formal_p07_failure": {"applicable_after": "2023-01-01", "decision": "FAIL",
                                "reason": "P07 uses the complete four-year aggregate; see P07 report"},
        "degradation_interpretation": _interpret(curve),
    }
    (output / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2, default=_json_default) + "\n")
    print(json.dumps({"run_id": output.name, "operations": len(curve),
                      "first_cumulative_expectancy_negative": summary["first_cumulative_expectancy_negative"]}, indent=2))
    return 0


def _load_strategy() -> StrategyDefinition:
    manifest = json.loads(MANIFEST.read_text())
    found = [x for x in manifest["finalists"] if x["strategy_hash"] == STRATEGY_HASH]
    if len(found) != 1:
        raise ValueError("frozen P07 strategy is absent or duplicated")
    strategy = StrategyDefinition.from_json(json.dumps(found[0]["strategy"]))
    if strategy.canonical_hash != STRATEGY_HASH:
        raise ValueError("frozen strategy hash mismatch")
    return strategy


def _load_market_before_holdout():
    cfg = yaml.safe_load((PROJECT_ROOT / "configs" / "data.yaml").read_text())
    cache = PROJECT_ROOT / cfg["derived_dir"] / "m15" / "EURUSD.parquet"
    frame = pd.read_parquet(cache, filters=[("ts_local", "<", datetime(2023, 1, 1))])
    metadata = pq.read_schema(cache).metadata or {}
    frame.attrs.update({key.decode(): value.decode() for key, value in metadata.items()})
    if frame.attrs.get("source_sha256") != EXPECTED_DATA_SHA256:
        raise ValueError("canonical cache source hash mismatch")
    if pd.Timestamp(frame["ts_local"].max()) >= pd.Timestamp("2023-01-01"):
        raise ValueError("P07A market contains holdout rows")
    return build_market("EURUSD", frame, Costs.for_pair("EURUSD"), dev_start_local=pd.Timestamp(cfg["dev_start_local"]))


def _window(market, start: str, end: str) -> tuple[int, int]:
    ts = market.h1["ts_local"].to_numpy()
    return int(ts.searchsorted(pd.Timestamp(start).to_datetime64())), int(ts.searchsorted(pd.Timestamp(end).to_datetime64()))


def _trade_frame(base: pd.DataFrame, x2: pd.DataFrame) -> pd.DataFrame:
    if len(base) != len(x2):
        raise ValueError("baseline and cost-x2 operation counts differ")
    frame = pd.DataFrame({"operation": np.arange(1, len(base) + 1),
                          "entry_timestamp": pd.to_datetime(base["entry_time"], utc=True),
                          "exit_timestamp": pd.to_datetime(base["exit_bar_time"], utc=True),
                          "result_R": base["r"].to_numpy(float), "result_R_costs_x2": x2["r"].to_numpy(float)})
    return frame.sort_values("exit_timestamp", kind="stable").reset_index(drop=True)


def _horizon_rows(frame: pd.DataFrame) -> pd.DataFrame:
    birth = pd.Timestamp("2019-01-01", tz="UTC")
    rows = []
    for months in HORIZONS:
        end = birth + pd.DateOffset(months=months)
        rows.append({"horizon_months": months, "end_timestamp": end.isoformat(), **_metrics(frame[frame["exit_timestamp"] < end])})
    return pd.DataFrame(rows)


def _quarter_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    work = frame.copy()
    work["quarter"] = work["exit_timestamp"].dt.tz_localize(None).dt.to_period("Q").astype(str)
    return pd.DataFrame([{"quarter": quarter, **_metrics(group)} for quarter, group in work.groupby("quarter", sort=True)])


def _metrics(frame: pd.DataFrame) -> dict:
    r = frame["result_R"].to_numpy(float)
    x2 = frame["result_R_costs_x2"].to_numpy(float)
    return {"n_trades": int(len(r)), "expectancy_R": float(r.mean()) if len(r) else 0.0,
            "profit_factor": _pf(r), "return": _return(r), "max_drawdown": _dd(r),
            "max_loss_streak": _loss_streak(r), "costs_x2_expectancy_R": float(x2.mean()) if len(x2) else 0.0,
            "costs_x2_profit_factor": _pf(x2), "costs_x2_return": _return(x2), "costs_x2_max_drawdown": _dd(x2),
            "costs_x2_max_loss_streak": _loss_streak(x2)}


def _curve(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for source, suffix in (("result_R", ""), ("result_R_costs_x2", "_costs_x2")):
        r = out[source].to_numpy(float)
        out[f"equity{suffix}"] = np.cumprod(1.0 + 0.005 * r)
        peak = np.maximum.accumulate(out[f"equity{suffix}"].to_numpy(float))
        out[f"drawdown{suffix}"] = 1.0 - out[f"equity{suffix}"] / peak
        out[f"cumulative_expectancy{suffix}"] = np.cumsum(r) / np.arange(1, len(r) + 1)
        out[f"rolling_expectancy_10{suffix}"] = pd.Series(r).rolling(10, min_periods=10).mean().to_numpy()
        out[f"rolling_expectancy_20{suffix}"] = pd.Series(r).rolling(20, min_periods=20).mean().to_numpy()
    return out


def _pf(r: np.ndarray) -> float:
    loss = -r[r < 0].sum()
    return float(r[r > 0].sum() / loss) if loss else (float("inf") if len(r) else 0.0)


def _return(r: np.ndarray) -> float:
    return float(np.prod(1.0 + 0.005 * r) - 1.0) if len(r) else 0.0


def _dd(r: np.ndarray) -> float:
    if not len(r):
        return 0.0
    equity = np.cumprod(1.0 + 0.005 * r)
    return float(np.max(1.0 - equity / np.maximum.accumulate(equity)))


def _loss_streak(r: np.ndarray) -> int:
    best = current = 0
    for value in r:
        current = current + 1 if value < 0 else 0
        best = max(best, current)
    return int(best)


def _first_negative(curve: pd.DataFrame) -> str | None:
    hits = curve.loc[curve["cumulative_expectancy"] < 0, "exit_timestamp"]
    return None if hits.empty else pd.Timestamp(hits.iloc[0]).isoformat()


def _interpret(curve: pd.DataFrame) -> dict:
    if curve.empty:
        return {"status": "NO_TRADES"}
    tail = curve.tail(10)
    persistent_negative = bool((tail["rolling_expectancy_10"] < 0).all())
    return {"status": "DESCRIPTIVE_ONLY", "final_cumulative_expectancy_R": float(curve["cumulative_expectancy"].iloc[-1]),
            "final_rolling_10_expectancy_R": None if pd.isna(tail["rolling_expectancy_10"].iloc[-1]) else float(tail["rolling_expectancy_10"].iloc[-1]),
            "last_10_rolling_windows_all_negative": persistent_negative,
            "warning": "A temporary crossing or a short positive/negative run is not evidence of a statistical edge or its disappearance."}


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    frame.to_csv(path, index=False)


def _plot_equity(path: Path, curve: pd.DataFrame) -> None:
    _svg_plot(path, "P07A equity by closed operation", [("baseline", curve["equity"], "#1769aa"),
                                                        ("costes x2", curve["equity_costs_x2"], "#c62828")])


def _plot_metrics(path: Path, curve: pd.DataFrame) -> None:
    _svg_plot(path, "P07A causal rolling expectancy and drawdown", [
        ("rolling E, 10", curve["rolling_expectancy_10"], "#1769aa"),
        ("rolling E, 20", curve["rolling_expectancy_20"], "#2e7d32"),
        ("drawdown", curve["drawdown"], "#c62828"),
    ])


def _svg_plot(path: Path, title: str, series: list[tuple[str, pd.Series, str]]) -> None:
    width, height, left, right, top, bottom = 1000, 460, 65, 25, 45, 45
    values = np.concatenate([item[1].to_numpy(float)[np.isfinite(item[1].to_numpy(float))] for item in series])
    lo, hi = float(values.min()), float(values.max())
    if hi == lo:
        hi = lo + 1.0
    n = max(len(series[0][1]), 1)
    def point(i: int, value: float) -> str:
        x = left + (width - left - right) * i / max(n - 1, 1)
        y = top + (height - top - bottom) * (hi - value) / (hi - lo)
        return f"{x:.2f},{y:.2f}"
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<rect width="100%" height="100%" fill="white"/><text x="{left}" y="25" font-family="sans-serif" font-size="16">{title}</text>',
             f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
             f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>']
    for _label, values_series, colour in series:
        coords = [point(i, float(value)) for i, value in enumerate(values_series) if np.isfinite(value)]
        if coords:
            lines.append(f'<polyline fill="none" stroke="{colour}" stroke-width="2" points="{" ".join(coords)}"/>')
    for j, (label, _, colour) in enumerate(series):
        x = left + j * 155
        lines.append(f'<line x1="{x}" y1="{height-20}" x2="{x+20}" y2="{height-20}" stroke="{colour}" stroke-width="3"/>')
        lines.append(f'<text x="{x+25}" y="{height-15}" font-family="sans-serif" font-size="12">{label}</text>')
    lines.append(f'<text x="5" y="{top+5}" font-family="sans-serif" font-size="11">{hi:.3f}</text>')
    lines.append(f'<text x="5" y="{height-bottom}" font-family="sans-serif" font-size="11">{lo:.3f}</text></svg>')
    path.write_text("\n".join(lines) + "\n")


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    raise TypeError(type(value).__name__)


if __name__ == "__main__":
    raise SystemExit(main())
