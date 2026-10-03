from pathlib import Path

import pandas as pd
import yaml


def test_p12d_protocol_is_nine_quarters_and_has_no_selection() -> None:
    config = yaml.safe_load(Path("configs/p12d_population_lifecycle.yaml").read_bytes())
    assert len(config["quarters"]) == 9
    assert config["execution"]["ga_rerun"] is False
    assert config["execution"]["no_forward_selection"] is True
    assert str(config["execution"]["source_end_exclusive"]) == "2019-04-01"


def test_p12d_longitudinal_contract_has_unique_keys_when_artifacts_exist() -> None:
    path = Path("reports/p12d_artifacts/population_lifecycle.parquet")
    if not path.exists():
        return
    frame = pd.read_parquet(path, columns=["strategy_hash", "quarter"])
    assert len(frame) == 900_000
    assert frame["strategy_hash"].nunique() == 100_000
    assert frame["quarter"].nunique() == 9
    assert not frame.duplicated(["strategy_hash", "quarter"]).any()


def test_p12d_p12a_equivalence_is_recorded_when_artifacts_exist() -> None:
    path = Path("reports/p12d_artifacts/equivalence_p12a.json")
    if not path.exists():
        return
    assert bool(pd.read_json(path, typ="series")["matched"])
