"""P06 acceptance policy boundary and immutability tests."""
from pathlib import Path

import pytest

from new_forex.walk_forward.acceptance import classify, load_policy

ROOT = Path(__file__).parents[1]


def _policy(tmp_path: Path):
    target = tmp_path / "wf_acceptance.yaml"
    target.write_text((ROOT / "configs" / "wf_acceptance.yaml").read_text())
    return load_policy(target)


def _result(policy, *, n=40, pf=1.10, exp=0.01, x2=0.01, positive=3, dd=0.05, identity=True):
    years = [{"n_trades": 10, "expectancy_R": 0.01 if i < positive else -0.01} for i in range(4)]
    return classify(policy, strategy_hash="abc", aggregate={"n_trades": n, "profit_factor": pf,
                    "expectancy_R": exp, "max_drawdown": dd}, yearly=years,
                    costs_x2={"expectancy_R": x2}, identity_ok=identity, max_drawdown_limit=0.10)


def test_all_criteria_must_pass(tmp_path):
    assert _result(_policy(tmp_path))["decision"] == "PASS"


@pytest.mark.parametrize("kwargs", [
    {"n": 39}, {"pf": 1.05}, {"positive": 2}, {"exp": 0.0}, {"x2": 0.0}, {"identity": False},
])
def test_strict_and_count_boundaries_fail(tmp_path, kwargs):
    assert _result(_policy(tmp_path), **kwargs)["decision"] == "FAIL"


@pytest.mark.parametrize("pf", [float("nan"), float("inf")])
def test_nonfinite_profit_factor_fails(tmp_path, pf):
    result = _result(_policy(tmp_path), pf=pf)
    assert result["decision"] == "FAIL"
    assert result["checks"]["require_finite_profit_factor"]["status"] == "FAIL"


def test_year_without_trades_is_not_positive(tmp_path):
    policy = _policy(tmp_path)
    years = [{"n_trades": 10, "expectancy_R": 0.1}, {"n_trades": 0, "expectancy_R": 1.0},
             {"n_trades": 10, "expectancy_R": 0.1}, {"n_trades": 10, "expectancy_R": -0.1}]
    result = classify(policy, strategy_hash="abc", aggregate={"n_trades": 40, "profit_factor": 1.1,
                    "expectancy_R": 0.1, "max_drawdown": 0.05}, yearly=years,
                    costs_x2={"expectancy_R": 0.1}, identity_ok=True, max_drawdown_limit=0.1)
    assert result["positive_years"] == 2
    assert result["decision"] == "FAIL"


def test_missing_comparable_p04_drawdown_blocks_only_certification(tmp_path):
    result = _result(_policy(tmp_path), dd=0.01)
    result = classify(_policy(tmp_path), strategy_hash="abc", aggregate={"n_trades": 40, "profit_factor": 1.1,
                    "expectancy_R": 0.1, "max_drawdown": 0.01}, yearly=[{"n_trades": 10, "expectancy_R": 0.1}] * 4,
                    costs_x2={"expectancy_R": 0.1}, identity_ok=True, max_drawdown_limit=None)
    assert result["decision"] == "BLOCKED"
    assert result["checks"]["max_drawdown"]["status"].startswith("BLOCKED")


def test_policy_cannot_change_silently(tmp_path):
    path = tmp_path / "wf_acceptance.yaml"
    path.write_text((ROOT / "configs" / "wf_acceptance.yaml").read_text())
    policy = load_policy(path)
    path.write_text(path.read_text() + "\n# mutation\n")
    with pytest.raises(RuntimeError, match="changed"):
        classify(policy, strategy_hash="abc", aggregate={"n_trades": 40, "profit_factor": 1.1,
                 "expectancy_R": 0.1, "max_drawdown": 0.01}, yearly=[{"n_trades": 10, "expectancy_R": 0.1}] * 4,
                 costs_x2={"expectancy_R": 0.1}, identity_ok=True, max_drawdown_limit=0.1)
