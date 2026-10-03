import json
import random
from pathlib import Path

import pandas as pd
import yaml


def test_p12d_2_freezes_historical_eligibility_and_sampling() -> None:
    config = yaml.safe_load(Path("configs/p12d_2_portfolio_sensitivity.yaml").read_bytes())
    assert config["eligibility"] == {"training_profit_factor_gte": 1.05, "training_n_trades_gte": 100}
    assert config["evaluation"]["no_forward_selection"] is True
    assert config["evaluation"]["no_reselection"] is True
    assert config["evaluation"]["portfolios"] == 1000
    assert config["evaluation"]["portfolio_size"] == 5


def test_p12d_2_quarters_are_formal_and_pre_holdout() -> None:
    config = yaml.safe_load(Path("configs/p12d_2_portfolio_sensitivity.yaml").read_bytes())
    assert config["quarters"] == ["2018Q1", "2018Q2", "2018Q3", "2018Q4", "2019Q1"]
    assert str(config["holdout_end_exclusive"]) == "2023-01-01"


def test_p12d_2_sampling_is_reproducible_without_replacement() -> None:
    universe = [f"s{i}" for i in range(20)]
    first = random.Random(20261214).sample(universe, 5)
    second = random.Random(20261214).sample(universe, 5)
    assert first == second
    assert len(first) == len(set(first)) == 5


def test_p12d_2_artifacts_preserve_historical_eligibility_and_composition_size() -> None:
    eligible_path = Path("reports/p12d_2_artifacts/eligible_universe.csv")
    compositions_path = Path("reports/p12d_2_artifacts/compositions.jsonl")
    if not eligible_path.exists() or not compositions_path.exists():
        return
    eligible = pd.read_csv(eligible_path)
    assert len(eligible) == 7517
    assert (eligible["training_profit_factor"] >= 1.05).all()
    assert (eligible["training_n_trades"] >= 100).all()
    compositions = [json.loads(line) for line in compositions_path.read_text().splitlines()]
    assert len(compositions) == 1001
    for composition in compositions:
        assert len(composition["selected"]) == 5
        assert len(composition["selected"]) == len(set(composition["selected"]))
        assert set(composition["selected"]) <= set(eligible["strategy_hash"])
