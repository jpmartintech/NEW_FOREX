import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_p13b_x_y_dictionary_is_disjoint_and_input_is_frozen() -> None:
    config = yaml.safe_load((ROOT / "configs/p13b_predictability_mapping.yaml").read_bytes())
    x = set(config["variables"]["historical_x"])
    y = set(config["variables"]["forward_y"])
    assert x.isdisjoint(y)
    assert config["source"]["invalid_run_excluded"] is True
    assert config["reproducibility"]["holdout_used"] is False
    source = ROOT / config["source"]["classified_census"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["source"]["classified_census_sha256"]


def test_p13b_maps_have_complete_denominators_and_reproduce_e_classes() -> None:
    source = pd.read_parquet(ROOT / "reports/p13a_artifacts/classified_census.parquet")
    maps = pd.read_csv(ROOT / "reports/p13b_artifacts/univariate_maps.csv")
    assert len(source) == 2_400_000
    assert maps["condition"].isin({"all", "active_ge_1", "active_ge_3", "active_ge_5"}).all()
    baseline = maps[maps["interval"] == "__BASELINE__"]
    assert len(baseline) > 0
    assert (baseline["pct_population"] == 1.0).all()
    expected = source.groupby(["generation", "generator"], as_index=False).agg(
        pct_e=("economic_class", lambda x: (x == "E").mean())
    )
    actual = baseline[baseline["condition"] == "all"].merge(expected, on=["generation", "generator"])
    assert (actual["pct_E"].sub(actual["pct_e"]).abs() < 1e-12).all()


def test_p13b_bins_do_not_overlap_and_inactive_is_retained() -> None:
    config = yaml.safe_load((ROOT / "configs/p13b_predictability_mapping.yaml").read_bytes())
    assert config["binning"]["profit_factor"] == [1.0, 1.1, 1.2, 1.3, 1.5]
    assert config["binning"]["training_n_trades"] == [25, 50, 75, 100, 150, 200, 250]
    source = pd.read_parquet(ROOT / "reports/p13a_artifacts/classified_census.parquet")
    assert (source.loc[source["economic_class"] == "A", "forward_n_trades"] == 0).all()
    assert source["economic_class"].isin({"A", "B", "C", "D", "E"}).all()


def test_p13b_portfolio_control_is_not_fabricated() -> None:
    status = json.loads((ROOT / "reports/p13b_artifacts/portfolio_control_status.json").read_text())
    assert status["executed"] is False
    assert "cannot be reconstructed" in status["reason"]
