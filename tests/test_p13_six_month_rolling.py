import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    return yaml.safe_load((ROOT / "configs/p13_six_month_rolling.yaml").read_bytes())


def test_p13_freezes_monthly_windows_and_h1_execution() -> None:
    config = _config()
    assert config["policy_id"] == "p13-six-month-rolling-v1.1"
    assert config["timeframe"] == "H1"
    assert config["windows"]["training_months"] == 6
    assert config["windows"]["forward_months"] == 1
    assert config["execution"]["training_timeframe"] == "H1"
    assert config["execution"]["forward_timeframe"] == "H1"
    assert config["execution"]["holdout_used"] is False


def test_p13_budget_and_frozen_selection_rule() -> None:
    config = _config()
    assert config["generation"]["unique_evaluations"] == 100_000
    assert config["generation"]["generations"] == 102
    assert config["selection"]["training_profit_factor"] == {"operator": ">", "value": 1.30}
    assert config["selection"]["training_n_trades"] == {"operator": ">", "value": 250}
    assert config["selection"]["no_forward_selection"] is True
    assert config["selection"]["insufficient_policy"]["zero"] == "cash_no_active_strategies"


def test_p13_rollover_and_cost_policy_are_frozen() -> None:
    config = _config()
    assert config["portfolio"]["costs"] == [1.0, 2.0]
    assert config["portfolio"]["rollover"] == "force_close_at_month_end_before_replacement"
    assert config["portfolio"]["risk_per_trade"] == 0.005
    assert config["portfolio"]["max_aggregate_risk"] == 0.025


def test_p13_results_have_exact_budgets_and_temporal_census() -> None:
    manifest = json.loads((ROOT / "reports/p13_artifacts/manifest.json").read_text())
    assert manifest["generations"] == 12
    assert manifest["census_rows"] == 2_400_000
    assert manifest["ga_evaluations"] == 1_200_000
    assert manifest["random_evaluations"] == 1_200_000
    assert manifest["budget_exact"] is True
    census = pd.read_parquet(ROOT / "reports/p13_artifacts/forward_census_all.parquet")
    assert len(census) == 2_400_000
    assert census.groupby(["generation", "generator"]).size().eq(100_000).all()
    expected_months = {f"2017-{month:02d}" for month in range(7, 13)} | {
        "2018-01", "2018-02", "2018-03", "2018-04", "2018-05", "2018-06"
    }
    assert set(census["forward_month"]) == expected_months


def test_p13_selections_and_rolling_results_are_reproducible() -> None:
    selections = [json.loads(line) for line in (ROOT / "reports/p13_artifacts/selections_all.jsonl").read_text().splitlines()]
    assert len(selections) == 24
    for row in selections:
        assert len(row["selected"]) <= 5
        assert len(row["selected"]) == len(set(row["selected"]))
        if row["eligible_n"] >= 5:
            assert len(row["selected"]) == 5
    trajectories = pd.read_csv(ROOT / "reports/p13_artifacts/rolling_trajectories.csv")
    assert len(trajectories) == 4
    assert set(trajectories["cost"]) == {"baseline", "costs_x2"}
