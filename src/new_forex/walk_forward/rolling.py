"""Versioned selection contract for the quarterly rolling factory."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RollingPolicy:
    raw: dict[str, Any]
    path: Path
    sha256: str

    def assert_unchanged(self) -> None:
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        if digest != self.sha256:
            raise RuntimeError("rolling factory policy changed during execution")


def load_policy(path: Path) -> RollingPolicy:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if raw.get("policy_id") != "p08-rolling-factory-v1":
        raise ValueError("unexpected rolling factory policy")
    if raw["ga"]["max_unique_evaluations"] != 100_000 or raw["selection"]["max_active_strategies"] != 5:
        raise ValueError("rolling factory budget or active-strategy cap changed")
    policy = RollingPolicy(raw, path, hashlib.sha256(path.read_bytes()).hexdigest())
    policy.assert_unchanged()
    return policy


def classify_candidate(policy: RollingPolicy, *, strategy_hash: str, aggregate: dict[str, Any], years: list[dict[str, Any]],
                       costs_x2: dict[str, Any]) -> dict[str, Any]:
    policy.assert_unchanged()
    cfg = policy.raw["selection"]
    pf = float(aggregate["profit_factor"])
    positive_years = sum(int(y["n_trades"]) > 0 and float(y["expectancy_R"]) > 0 for y in years)
    checks = {
        "min_dev_wf_trades": _check(int(aggregate["n_trades"]) >= cfg["min_dev_wf_trades"],
                                      aggregate["n_trades"], cfg["min_dev_wf_trades"]),
        "min_aggregate_expectancy_R": _check(float(aggregate["expectancy_R"]) > cfg["min_aggregate_expectancy_R"],
                                              aggregate["expectancy_R"], cfg["min_aggregate_expectancy_R"]),
        "min_profit_factor": _check(pf > cfg["min_profit_factor"], pf, cfg["min_profit_factor"]),
        "require_finite_profit_factor": _check(npfinite(pf), pf, "finite"),
        "min_positive_years": _check(positive_years >= cfg["min_positive_years"], positive_years, cfg["min_positive_years"]),
        "costs_x2_expectancy_R": _check(float(costs_x2["expectancy_R"]) > cfg["costs_x2_expectancy_R"],
                                         costs_x2["expectancy_R"], cfg["costs_x2_expectancy_R"]),
    }
    return {"strategy_hash": strategy_hash, "positive_years": positive_years, "checks": checks,
            "decision": "PASS" if all(x["status"] == "PASS" for x in checks.values()) else "FAIL"}


def rank_and_select(policy: RollingPolicy, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Select at most the frozen cap; sorting makes equal metrics hash-deterministic."""
    policy.assert_unchanged()
    passed = [row for row in rows if row["acceptance"]["decision"] == "PASS"]
    passed.sort(key=lambda row: (-float(row["aggregate"]["expectancy_R"]), -float(row["aggregate"]["profit_factor"]),
                                float(row["aggregate"].get("max_drawdown", 0.0)),
                                -int(row["aggregate"]["n_trades"]), row["strategy_hash"]))
    selected = passed[: int(policy.raw["selection"]["max_active_strategies"])]
    return selected, {"input": len(rows), "eligible": len(passed), "selected": len(selected),
                      "rejected_cap": max(0, len(passed) - len(selected))}


def _check(ok: bool, observed: Any, threshold: Any) -> dict[str, Any]:
    return {"status": "PASS" if ok else "FAIL", "observed": observed, "threshold": threshold}


def npfinite(value: float) -> bool:
    return value == value and value not in (float("inf"), -float("inf"))
