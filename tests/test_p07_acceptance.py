"""P07 policy tests use only synthetic metric fixtures."""
from pathlib import Path

import pytest

from new_forex.walk_forward.acceptance import classify, load_policy

ROOT = Path(__file__).parents[1]


def _policy(tmp_path: Path):
    target = tmp_path / "procedure_validation.yaml"
    target.write_text((ROOT / "configs" / "procedure_validation.yaml").read_text())
    return load_policy(target)


def _classify(policy, *, n=40, pf=1.10, expectancy=0.01, x2=0.01, years=3, dd_limit=0.10):
    yearly = [{"n_trades": 10, "expectancy_R": 0.01 if i < years else -0.01} for i in range(4)]
    return classify(policy, strategy_hash=policy.raw["strategy_hash"],
                    aggregate={"n_trades": n, "profit_factor": pf, "expectancy_R": expectancy,
                               "max_drawdown": 0.05}, yearly=yearly,
                    costs_x2={"expectancy_R": x2}, identity_ok=True,
                    max_drawdown_limit=dd_limit)


def test_p07_policy_passes_only_complete_synthetic_control(tmp_path):
    assert _classify(_policy(tmp_path))["decision"] == "PASS"


@pytest.mark.parametrize("kwargs", [{"n": 39}, {"pf": 1.05}, {"expectancy": 0.0}, {"x2": 0.0}, {"years": 2}])
def test_p07_criteria_are_strict_and_simultaneous(tmp_path, kwargs):
    assert _classify(_policy(tmp_path), **kwargs)["decision"] == "FAIL"


def test_p07_infinite_pf_is_not_accepted(tmp_path):
    result = _classify(_policy(tmp_path), pf=float("inf"))
    assert result["decision"] == "FAIL"
    assert result["checks"]["require_finite_profit_factor"]["status"] == "FAIL"
