"""Versioned, non-retrospective application of the P05 stress policy."""
from __future__ import annotations

from typing import Any


def classify(metrics: dict[str, Any], policy: dict[str, Any], scenario: str) -> dict[str, Any]:
    """Classify one row without treating infinite PF as a valid result."""
    spec = policy["scenarios"][scenario]
    n = int(metrics["n_trades"])
    min_trades = int(policy["metric_definitions"]["minimum_trades_for_formal_classification"])
    adequate_sample = n >= min_trades
    mode = spec["mode"]
    if mode == "diagnostic_only":
        decision = "DIAGNOSTIC_ONLY"
    elif not adequate_sample:
        decision = "REJECT_INSUFFICIENT_TRADES"
    elif spec["criterion"] == "expectancy_net_R > 0":
        decision = "PASS" if float(metrics["mean_r"]) > 0.0 else "REJECT_EXPECTANCY"
    elif spec["criterion"] == "finite_profit_factor > 1":
        pf = float(metrics["profit_factor"])
        decision = "PASS" if pf == pf and pf != float("inf") and pf > 1.0 else "REJECT_FINITE_PF"
    else:
        raise ValueError(f"unsupported P05 acceptance criterion for {scenario}: {spec['criterion']}")
    return {"mode": mode, "criterion": spec["criterion"], "minimum_trades": min_trades,
            "adequate_sample": adequate_sample, "decision": decision}
