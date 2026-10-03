import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_p13a_protocol_excludes_invalid_run_and_seals_holdout() -> None:
    config = yaml.safe_load((ROOT / "configs/p13a_census_anatomy.yaml").read_bytes())
    assert config["source"]["invalid_run_excluded"] is True
    assert config["evaluation"]["holdout_used"] is False
    assert config["classification"]["equality_policy"] == "exact_zero_is_non_positive"


def test_p13a_census_integrity_and_generation_identity() -> None:
    frame = pd.read_parquet(ROOT / "reports/p13a_artifacts/classified_census.parquet")
    assert len(frame) == 2_400_000
    assert frame.groupby(["generation", "generator"]).size().eq(100_000).all()
    assert not frame.duplicated(["generation", "generator", "strategy_hash"]).any()
    assert set(frame["forward_month"]) == {f"2017-{m:02d}" for m in range(7, 13)} | {f"2018-{m:02d}" for m in range(1, 7)}
    assert frame["forward_month"].astype(str).max() < "2018-07"


def test_p13a_classes_are_exhaustive_and_inactive_is_distinct() -> None:
    frame = pd.read_parquet(ROOT / "reports/p13a_artifacts/classified_census.parquet")
    assert set(frame["economic_class"]) == {"A", "B", "C", "D", "E"}
    assert (frame.loc[frame["economic_class"] == "A", "forward_n_trades"] == 0).all()
    assert (frame.loc[frame["economic_class"] != "A", "forward_n_trades"] > 0).all()
    # Inactivity is classified from n_trades, never inferred from expectancy.
    membership = frame.groupby(["generation", "generator", "strategy_hash"]).size()
    assert membership.eq(1).all()


def test_p13a_cost_reconciliation_and_no_forward_selection() -> None:
    frame = pd.read_parquet(ROOT / "reports/p13a_artifacts/classified_census.parquet")
    assert np.allclose(frame["forward_gross_total_R"], 2 * frame["forward_total_R"] - frame["forward_x2_total_R"], atol=1e-10)
    expected_filter = (frame["training_profit_factor"] > 1.30) & (frame["training_n_trades"] > 250)
    assert (frame["historical_filter_pass"] == expected_filter).all()
    manifest = json.loads((ROOT / "reports/p13a_artifacts/manifest.json").read_text())
    assert manifest["invalid_run_excluded"] is True
    assert manifest["holdout_used"] is False
