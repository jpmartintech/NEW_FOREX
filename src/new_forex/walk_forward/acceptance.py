"""Frozen P06 acceptance policy and immutable execution snapshot."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AcceptancePolicy:
    raw: dict[str, Any]
    path: Path
    sha256: str

    @property
    def policy_id(self) -> str:
        return str(self.raw["policy_id"])

    def assert_unchanged(self) -> None:
        current = _sha256(self.path)
        if current != self.sha256:
            raise RuntimeError(f"P06 acceptance policy changed during execution: {self.path}")


def load_policy(path: Path) -> AcceptancePolicy:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    _validate_schema(raw)
    policy = AcceptancePolicy(raw=raw, path=path, sha256=_sha256(path))
    policy.assert_unchanged()
    return policy


def classify(
    policy: AcceptancePolicy,
    *,
    strategy_hash: str,
    aggregate: dict[str, Any],
    yearly: list[dict[str, Any]],
    costs_x2: dict[str, Any],
    identity_ok: bool,
    max_drawdown_limit: float | None,
) -> dict[str, Any]:
    """Apply all P06 criteria simultaneously; no compensating score exists."""
    policy.assert_unchanged()
    criteria = policy.raw["criteria"]
    positive_years = sum(1 for row in yearly if int(row["n_trades"]) > 0 and float(row["expectancy_R"]) > 0.0)
    pf = float(aggregate["profit_factor"])
    expectancy = float(aggregate["expectancy_R"])
    x2_expectancy = float(costs_x2["expectancy_R"])
    checks: dict[str, dict[str, Any]] = {
        "min_total_oos_trades": _check(int(aggregate["n_trades"]) >= int(criteria["min_total_oos_trades"]),
                                        aggregate["n_trades"], criteria["min_total_oos_trades"]),
        "min_aggregate_expectancy_R": _check(_strict_gt(expectancy, criteria["min_aggregate_expectancy_R"]),
                                              expectancy, criteria["min_aggregate_expectancy_R"]),
        "min_aggregate_profit_factor": _check(_strict_gt(pf, criteria["min_aggregate_profit_factor"]),
                                               pf, criteria["min_aggregate_profit_factor"]),
        "require_finite_profit_factor": _check(
            bool(criteria["require_finite_profit_factor"]) and pf == pf and pf not in (float("inf"), -float("inf")),
            pf, "finite"),
        "min_positive_years": _check(positive_years >= int(criteria["min_positive_years"]),
                                      positive_years, criteria["min_positive_years"]),
        "costs_x2_expectancy_R": _check(_strict_gt(x2_expectancy, criteria["costs_x2_expectancy_R"]),
                                         x2_expectancy, criteria["costs_x2_expectancy_R"]),
        "frozen_identity_required": _check(identity_ok, identity_ok, True),
    }
    if max_drawdown_limit is None:
        checks["max_drawdown"] = {"status": "BLOCKED_INCOMPARABLE_P04_LIMIT", "observed": aggregate.get("max_drawdown")}
    else:
        checks["max_drawdown"] = _check(float(aggregate["max_drawdown"]) <= max_drawdown_limit,
                                         aggregate["max_drawdown"], max_drawdown_limit)
    failed = [name for name, item in checks.items() if item["status"] == "FAIL"]
    blocked = [name for name, item in checks.items() if item["status"].startswith("BLOCKED")]
    decision = "FAIL" if failed else ("BLOCKED" if blocked else "PASS")
    return {"policy_id": policy.policy_id, "policy_sha256": policy.sha256, "strategy_hash": strategy_hash,
            "positive_years": positive_years, "checks": checks, "decision": decision}


def _strict_gt(observed: float, threshold: float) -> bool:
    return observed == observed and observed > float(threshold)


def _check(ok: bool, observed: Any, threshold: Any) -> dict[str, Any]:
    return {"status": "PASS" if ok else "FAIL", "observed": observed, "threshold": threshold}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_schema(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict) or raw.get("policy_id") not in {"p06-frozen-wf-v1", "p07-procedure-validation-v1"}:
        raise ValueError("unexpected P06 policy id")
    criteria = raw.get("criteria", {})
    required = {"min_total_oos_trades", "min_aggregate_expectancy_R", "min_aggregate_profit_factor",
                "require_finite_profit_factor", "min_positive_years", "total_years", "costs_x2_expectancy_R",
                "frozen_identity_required", "max_drawdown"}
    if not required <= criteria.keys():
        raise ValueError("P06 policy is missing required criteria")
    if criteria["total_years"] != 4 or criteria["min_positive_years"] != 3:
        raise ValueError("P06 annual criteria do not match the frozen contract")
