"""P03 acceptance tests for predeclared net-cost selection."""
from __future__ import annotations

import pytest

from new_forex.selection.ranking import SelectionConfig, metrics_from_returns, select_candidates, write_selection_audit


def test_metrics_are_net_of_declared_costs() -> None:
    metrics = metrics_from_returns([0.10, -0.04, 0.02], cost_per_trade=0.01)

    assert metrics.n_trades == 3
    assert metrics.total_r == pytest.approx(0.05)
    assert metrics.mean_r == pytest.approx(0.05 / 3)
    assert metrics.profit_factor == pytest.approx((0.09 + 0.01) / 0.05)


def test_selection_deduplicates_applies_gates_and_records_attrition() -> None:
    candidates = [
        {"canonical_hash": "a", "metrics": metrics_from_returns([0.1] * 10, 0.01)},
        {"canonical_hash": "a", "metrics": metrics_from_returns([0.2] * 10, 0.01)},
        {"canonical_hash": "b", "metrics": metrics_from_returns([0.01] * 3, 0.0)},
        {"canonical_hash": "c", "metrics": metrics_from_returns([0.03, -0.02] * 5, 0.0)},
    ]
    result = select_candidates(candidates, SelectionConfig(top_k=1, min_trades=5, min_mean_r=0.0, min_profit_factor=1.0))

    assert result.selected == ("a",)
    assert result.audit == {"input": 4, "unique": 3, "rejected_duplicate": 1, "eligible": 2, "selected": 1,
                            "rejected_concentration": 0}


def test_selection_enforces_declared_pair_concentration_cap() -> None:
    good = metrics_from_returns([0.05] * 10, 0.0)
    candidates = [{"canonical_hash": f"a{i}", "pair": "EURUSD", "metrics": good} for i in range(3)]
    candidates += [{"canonical_hash": "b0", "pair": "GBPUSD", "metrics": good}]

    result = select_candidates(candidates, SelectionConfig(top_k=4, min_trades=5, max_pair_fraction=0.5))

    assert len(result.selected) == 3
    assert sum(key.startswith("a") for key in result.selected) == 2
    assert result.audit["rejected_concentration"] == 1


def test_selection_audit_persists_run_and_data_provenance(tmp_path) -> None:
    config = SelectionConfig(top_k=1, min_trades=1, min_mean_r=-1.0, min_profit_factor=0.0)
    result = select_candidates([{"canonical_hash": "a", "metrics": metrics_from_returns([0.1], 0.0)}], config)
    path = tmp_path / "selection.json"

    write_selection_audit(result, path, run_id="test-p03", config=config, data_hashes={"EURUSD": "abc"}, split_hash="def")

    text = path.read_text()
    assert '"run_id": "test-p03"' in text
    assert '"split_hash": "def"' in text
    assert '"selected": [' in text
