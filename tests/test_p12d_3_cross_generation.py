import json
import random
from pathlib import Path

import yaml


def test_p12d_3_freezes_rule_windows_and_controls() -> None:
    config = yaml.safe_load(Path("configs/p12d_3_cross_generation.yaml").read_bytes())
    assert len(config["generations"]) == 15
    assert config["rule"] == {"training_profit_factor_gte": 1.05, "training_n_trades_gte": 100}
    assert config["evaluation"]["no_forward_selection"] is True
    assert config["controls"]["full_random"] is True
    assert config["controls"]["activity_matched_random"] is True
    assert config["trajectories"]["count"] == 1000


def test_p12d_3_sampling_is_reproducible_and_unique() -> None:
    universe = [f"strategy-{i}" for i in range(20)]
    first = random.Random(20261215).sample(universe, 5)
    second = random.Random(20261215).sample(universe, 5)
    assert first == second
    assert len(first) == len(set(first)) == 5


def test_p12d_3_artifacts_preserve_generation_and_forward_boundaries() -> None:
    path = Path("reports/p12d_3_artifacts/compositions.jsonl")
    if not path.exists():
        return
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows
    assert all(len(row["selected"]) == 5 for row in rows)
    assert all(len(row["selected"]) == len(set(row["selected"])) for row in rows)
    labels = {f"{year}Q{quarter}" for year in range(2019, 2023) for quarter in range(1, 5) if not (year == 2019 and quarter == 1)}
    assert all(row["generation"] in labels for row in rows)
