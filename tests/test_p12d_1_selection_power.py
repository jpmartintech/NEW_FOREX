from pathlib import Path

import yaml


def test_p12d_1_protocol_is_temporally_separated() -> None:
    config = yaml.safe_load(Path("configs/p12d_1_selection_power.yaml").read_bytes())
    assert config["discovery_quarters"] == ["2017Q1", "2017Q2", "2017Q3", "2017Q4"]
    assert config["formal_quarters"][0] == "2018Q1"
    assert config["formal_quarters"][-1] == "2019Q1"
    assert config["evaluation"]["no_forward_predictors"] is True
    assert config["evaluation"]["no_reselection"] is True


def test_p12d_1_has_limited_interpretable_rules_and_fixed_portfolio() -> None:
    config = yaml.safe_load(Path("configs/p12d_1_selection_power.yaml").read_bytes())
    assert len(config["rules_tested"]) == 11
    assert len(config["formal_rules"]) == 3
    assert all(item in {rule["id"] for rule in config["rules_tested"]} for item in config["formal_rules"])
    assert config["evaluation"]["selection_size"] == 5
    assert config["control"]["replicates"] == 100
