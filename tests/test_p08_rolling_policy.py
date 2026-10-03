"""P08 rolling-policy tests with synthetic metric fixtures only."""
from pathlib import Path

import pytest

from new_forex.walk_forward.rolling import classify_candidate, load_policy, rank_and_select
from new_forex.walk_forward.rolling_factory import generation_windows

ROOT = Path(__file__).parents[1]


def _policy(tmp_path):
    path = tmp_path / "rolling.yaml"
    path.write_text((ROOT / "configs/rolling_factory.yaml").read_text())
    return load_policy(path)


def _row(policy, key="a", *, n=20, pf=1.1, exp=0.01, x2=0.01, positive=1):
    years = [{"n_trades": 10, "expectancy_R": 0.01 if i < positive else -0.01} for i in range(2)]
    a = {"n_trades": n, "profit_factor": pf, "expectancy_R": exp, "max_drawdown": 0.1}
    return {"strategy_hash": key, "aggregate": a, "costs_x2": {"expectancy_R": x2},
            "acceptance": classify_candidate(policy, strategy_hash=key, aggregate=a, years=years, costs_x2={"expectancy_R": x2})}


def test_first_generation_windows_are_exact():
    assert generation_windows("2019-01-01") == {"training": ("2009-01-01", "2017-01-01"),
                                                   "development_wf": ("2017-01-01", "2019-01-01"),
                                                   "forward": ("2019-01-01", "2019-04-01")}


def test_candidate_requires_all_criteria(tmp_path):
    policy = _policy(tmp_path)
    assert _row(policy)["acceptance"]["decision"] == "PASS"
    assert _row(policy, n=19)["acceptance"]["decision"] == "FAIL"
    assert _row(policy, pf=1.05)["acceptance"]["decision"] == "FAIL"
    assert _row(policy, x2=0.0)["acceptance"]["decision"] == "FAIL"
    assert _row(policy, positive=0)["acceptance"]["decision"] == "FAIL"
    assert _row(policy, pf=float("inf"))["acceptance"]["decision"] == "FAIL"


def test_cap_and_hash_tiebreak_are_deterministic(tmp_path):
    policy = _policy(tmp_path)
    rows = [_row(policy, key=f"{chr(122-i)}") for i in range(7)]
    selected, audit = rank_and_select(policy, rows)
    assert audit["selected"] == 5
    assert [x["strategy_hash"] for x in selected] == ["t", "u", "v", "w", "x"]


def test_zero_survivors_are_explicit(tmp_path):
    policy = _policy(tmp_path)
    selected, audit = rank_and_select(policy, [_row(policy, n=19)])
    assert selected == []
    assert audit["selected"] == 0


def test_policy_is_immutable(tmp_path):
    policy = _policy(tmp_path)
    policy.path.write_text(policy.path.read_text() + "\n# mutation\n")
    with pytest.raises(RuntimeError):
        rank_and_select(policy, [])
