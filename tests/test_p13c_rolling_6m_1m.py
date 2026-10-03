from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_p13c_calendar_and_budget_are_frozen() -> None:
    config = yaml.safe_load((ROOT / "configs/p13c_rolling_6m_1m.yaml").read_bytes())
    assert config["calendar"]["generation_count"] == 54
    assert config["calendar"]["training_months"] == 6
    assert config["generation"]["unique_evaluations"] == 100_000
    assert config["generation"]["generations"] == 102
    assert config["execution"]["holdout_used"] is False


def test_p13c_strict_filter_and_control_policy() -> None:
    config = yaml.safe_load((ROOT / "configs/p13c_rolling_6m_1m.yaml").read_bytes())
    assert config["selection"]["training_profit_factor"] == {"operator": ">", "value": 1.30}
    assert config["selection"]["training_n_trades"] == {"operator": ">", "value": 30}
    assert config["selection"]["composition_replicates"] == 1000
    assert config["controls"]["A"] == "random_five_from_historical_eligible_same_generation"
    assert config["controls"]["B"] == "random_five_from_full_100k_same_generation"


def test_p13c_month_schedule_is_contiguous_and_semi_open() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from run_p13c_rolling_6m_1m import months

    config = yaml.safe_load((ROOT / "configs/p13c_rolling_6m_1m.yaml").read_bytes())
    schedule = months(config)
    assert len(schedule) == 54
    assert schedule[0] == {
        "generation": "G001", "index": 0, "training_start": "2016-01-01", "training_end": "2016-07-01",
        "forward_start": "2016-07-01", "forward_end": "2016-08-01", "forward_month": "2016-07"
    }
    assert schedule[-1]["generation"] == "G054"
    assert schedule[-1]["training_start"] == "2020-06-01"
    assert schedule[-1]["forward_end"] == "2021-01-01"
    for previous, current in zip(schedule[:-1], schedule[1:], strict=True):
        assert previous["forward_end"] == current["forward_start"]
        assert previous["training_end"] == previous["forward_start"]


def test_p13c_costs_and_rollover_are_frozen() -> None:
    config = yaml.safe_load((ROOT / "configs/p13c_rolling_6m_1m.yaml").read_bytes())
    assert config["portfolio"]["costs"] == [1.0, 2.0]
    assert config["portfolio"]["capital_continuity"] is True
    assert config["portfolio"]["rollover"] == "force_close_at_month_end_before_replacement"
