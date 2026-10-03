"""P09 chronological and portfolio-consolidation tests."""
import pandas as pd
import pytest

from new_forex.walk_forward.rolling_historical import portfolio_ledger, portfolio_metrics, remaining_generations


def test_remaining_generations_are_chronological_and_complete():
    generations = remaining_generations()
    assert len(generations) == 15
    assert generations[0].label == "2019Q2"
    assert generations[-1].label == "2022Q4"
    assert generations[0].birth == "2019-04-01"
    assert generations[-1].forward_end == "2023-01-01"
    assert all(a.forward_end == b.birth for a, b in zip(generations[:-1], generations[1:], strict=True))


def test_portfolio_respects_overlap_and_compounds_exits():
    first = pd.DataFrame({"entry_timestamp": ["2020-01-01"], "exit_timestamp": ["2020-01-03"], "result_R": [1.0]})
    second = pd.DataFrame({"entry_timestamp": ["2020-01-02"], "exit_timestamp": ["2020-01-04"], "result_R": [-1.0]})
    result = portfolio_ledger([("a", first), ("b", second)])
    assert len(result) == 2
    assert result.iloc[-1]["equity"] == pytest.approx(1.0)
    assert portfolio_metrics(result)["active_strategies"] == 2


def test_portfolio_rejects_duplicate_operations():
    frame = pd.DataFrame({"entry_timestamp": ["2020-01-01"], "exit_timestamp": ["2020-01-03"], "result_R": [1.0]})
    with pytest.raises(ValueError, match="duplicate"):
        portfolio_ledger([("a", frame), ("a", frame)])


def test_portfolio_handles_entry_and_exit_on_same_bar():
    frame = pd.DataFrame({"entry_timestamp": ["2020-01-01"], "exit_timestamp": ["2020-01-01"], "result_R": [1.0]})
    result = portfolio_ledger([("a", frame)])
    assert len(result) == 1
    assert result.iloc[0]["equity"] == pytest.approx(1.005)
