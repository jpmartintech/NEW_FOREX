"""P05.1 acceptance-policy contract tests."""
from __future__ import annotations

import yaml

from new_forex.provenance import PROJECT_ROOT
from new_forex.stress.acceptance import classify


def policy() -> dict:
    return yaml.safe_load((PROJECT_ROOT / "configs" / "stress_acceptance.yaml").read_text())


def test_expectancy_policy_requires_positive_net_r_and_sample() -> None:
    cfg = policy()
    assert classify({"mean_r": 0.1, "profit_factor": 1.0, "n_trades": 100}, cfg, "cost_x2")["decision"] == "PASS"
    assert classify({"mean_r": 0.0, "profit_factor": 1.0, "n_trades": 100}, cfg, "cost_x2")["decision"] == "REJECT_EXPECTANCY"
    assert classify({"mean_r": 0.1, "profit_factor": 1.0, "n_trades": 99}, cfg, "cost_x2")["decision"] \
        == "REJECT_INSUFFICIENT_TRADES"


def test_infinite_profit_factor_is_not_a_delay_pass() -> None:
    cfg = policy()
    result = classify({"mean_r": 1.0, "profit_factor": float("inf"), "n_trades": 100}, cfg, "delay_m15_1")
    assert result["decision"] == "REJECT_FINITE_PF"
    assert classify({"mean_r": -1.0, "profit_factor": 0.1, "n_trades": 100}, cfg, "delay_m15_2")["decision"] == "DIAGNOSTIC_ONLY"
