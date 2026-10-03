import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    return yaml.safe_load((ROOT / "configs/p12f_high_quality.yaml").read_bytes())


def test_p12f_rule_and_temporal_isolation_are_frozen() -> None:
    config = _config()
    assert config["policy_id"] == "p12f-high-quality-v1"
    assert config["rule"] == {
        "training_profit_factor": {"operator": ">", "value": 1.30},
        "training_n_trades": {"operator": ">", "value": 250},
        "historical_only": True,
    }
    assert config["source"]["forward_window"] == ["2017-01-01", "2017-04-01"]
    assert config["evaluation"]["no_forward_selection"] is True
    assert config["evaluation"]["no_later_quarters"] is True
    assert config["evaluation"]["holdout_used"] is False


def test_p12f_portfolios_use_frozen_five_strategy_engine() -> None:
    portfolio = _config()["portfolio"]
    assert portfolio["size"] == 5
    assert portfolio["replicates"] == 1000
    assert portfolio["sampling"] == "uniform_without_replacement"
    assert portfolio["risk_per_trade"] == 0.005
    assert portfolio["max_aggregate_risk"] == 0.025


def test_p12f_controls_are_deterministic_and_activity_matched() -> None:
    controls = _config()["controls"]
    assert controls["full_population"]["seed_base"] != controls["activity_matched"]["seed_base"]
    assert controls["activity_matched"]["matching_variable"] == "training_n_trades"
    assert controls["activity_matched"]["matching_bins"] == 20


def test_p12f_artifacts_reconcile_population_and_portfolio_compositions() -> None:
    population = pd.read_parquet(ROOT / "reports/p12f_artifacts/individual_population.parquet")
    assert len(population) == 100_000
    assert population["strategy_hash"].is_unique
    assert (population["forward_n_trades"] == population["forward_x2_n_trades"]).all()
    gross_error = population["forward_gross_total_R"] - (2 * population["forward_total_R"] - population["forward_x2_total_R"])
    assert gross_error.abs().max() < 1e-12

    portfolios = pd.read_csv(ROOT / "reports/p12f_artifacts/portfolio_results.csv")
    assert len(portfolios) == 10_000
    for selected in portfolios["selected"].drop_duplicates():
        assert len(json.loads(selected)) == 5
        assert len(set(json.loads(selected))) == 5
    base = portfolios[portfolios["cost"].eq("baseline")].set_index(["group", "replicate"])
    x2 = portfolios[portfolios["cost"].eq("costs_x2")].set_index(["group", "replicate"])
    assert (base["return_gross"] == x2["return_gross"]).all()
    assert (x2["cost_absolute"] - x2["pnl_gross"] + x2["pnl_net"]).abs().max() < 1e-12
