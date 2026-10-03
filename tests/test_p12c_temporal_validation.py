from pathlib import Path

import yaml

from new_forex.walk_forward.random_control import seed_for


def test_p12c_protocol_has_no_forward_predictors_and_is_temporal() -> None:
    config = yaml.safe_load(Path("configs/p12c_temporal_validation.yaml").read_bytes())
    assert config["ga_rerun"] is False
    assert config["integrity"]["no_forward_predictors"] is True
    assert config["integrity"]["no_holdout"] is True
    assert len(config["generations"]) == 15


def test_hypotheses_use_historical_fields() -> None:
    config = yaml.safe_load(Path("configs/p12c_temporal_validation.yaml").read_bytes())
    fields = {item["historical_variable"] for item in config["hypotheses"].values()}
    assert "development_n_trades" in fields
    assert "development_expectancy_R" in fields
    assert "development_x2_expectancy_R" in fields
    assert "original_filter_decision" in fields


def test_seed_derivation_is_reproducible_and_forward_boundary_is_exclusive() -> None:
    config = yaml.safe_load(Path("configs/p12c_temporal_validation.yaml").read_bytes())
    assert seed_for(config["control"]["seed_base"], 3, 11) == 20264223
    assert config["forward_end_exclusive"].isoformat() == "2023-01-01"
    assert all(not label.startswith("2023") for label in config["generations"])
