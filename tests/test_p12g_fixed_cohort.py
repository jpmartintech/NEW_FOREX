import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict:
    return yaml.safe_load((ROOT / "configs/p12g_fixed_cohort.yaml").read_bytes())


def test_p12g_freezes_p12f_cohort_and_quarters() -> None:
    config = _config()
    assert config["policy_id"] == "p12g-fixed-cohort-v1"
    assert config["rule"] == {
        "training_profit_factor": {"operator": ">", "value": 1.30},
        "training_n_trades": {"operator": ">", "value": 250},
        "no_new_strategies": True,
        "no_forward_reselection": True,
    }
    assert config["cohort"]["expected_strategies"] == 47
    assert config["cohort"]["expected_compositions"] == 1000
    assert config["source"]["forward_quarters"][-1] == "2019Q1"
    assert config["evaluation"]["no_holdout"] is True


def test_p12g_reuses_compositions_and_frozen_risk() -> None:
    config = _config()
    assert config["cohort"]["reuse_exact_compositions"] is True
    assert config["cohort"]["composition_size"] == 5
    assert config["evaluation"]["risk_per_trade"] == 0.005
    assert config["evaluation"]["max_aggregate_risk"] == 0.025


def test_p12g_artifacts_preserve_identity_composition_and_temporal_separation() -> None:
    individual = pd.read_parquet(ROOT / "reports/p12g_artifacts/individual_quarterly.parquet")
    assert len(individual) == 47 * 9
    assert individual.duplicated(["strategy_hash", "quarter"]).sum() == 0
    assert set(individual["quarter"]) == set(_config()["source"]["forward_quarters"])
    assert individual["strategy_hash"].nunique() == 47

    compositions = pd.read_csv(ROOT / "reports/p12g_artifacts/portfolio_quarterly.csv")
    assert len(compositions) == 1000 * 9 * 2
    assert compositions["composition_id"].nunique() == 1000
    baseline = compositions[compositions["cost"].eq("baseline")].set_index(["composition_id", "quarter"])
    x2 = compositions[compositions["cost"].eq("costs_x2")].set_index(["composition_id", "quarter"])
    assert (baseline["return_gross"] == x2["return_gross"]).all()
    assert (x2["cost_absolute"] - x2["pnl_gross"] + x2["pnl_net"]).abs().max() < 1e-12

    composition_path = ROOT / "reports/p12f_artifacts/portfolio_compositions.jsonl"
    frozen = [json.loads(line) for line in composition_path.read_text().splitlines()]
    assert sum(row["group"] == "high_quality" for row in frozen) == 1000
