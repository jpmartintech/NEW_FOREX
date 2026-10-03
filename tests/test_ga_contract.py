"""P02 acceptance tests for the bounded, deterministic GA contract."""
from __future__ import annotations

import numpy as np
import pytest

from new_forex.generators.genetic import GAConfig, run_genetic, write_archive


def test_ga_config_declares_the_100k_unique_evaluation_cap() -> None:
    assert GAConfig.from_dict({"max_unique_evaluations": 100_000}).max_unique_evaluations == 100_000
    with pytest.raises(ValueError, match="100000"):
        GAConfig(max_unique_evaluations=100_001)


def test_ga_archive_is_unique_bounded_and_seed_reproducible() -> None:
    cfg = GAConfig(population=40, generations=8, max_unique_evaluations=125, elite=5, tournament=3)

    def fitness(batch):
        return np.asarray([len(strategy.predicates) + strategy.sl_atr for strategy in batch])

    first = run_genetic("EURUSD", fitness, cfg, seed=20261002)
    second = run_genetic("EURUSD", fitness, cfg, seed=20261002)

    assert first.n_evaluated == 125
    assert len(first.archive) == len(set(first.archive)) == first.n_evaluated
    assert list(first.archive) == list(second.archive)
    assert [value for _, value in first.archive.values()] == [value for _, value in second.archive.values()]


def test_ga_archive_persistence_has_manifest_and_canonical_records(tmp_path) -> None:
    cfg = GAConfig(population=12, generations=2, max_unique_evaluations=20, elite=2, tournament=2)
    result = run_genetic("EURUSD", lambda batch: np.ones(len(batch)), cfg, seed=4)
    path = tmp_path / "archive.jsonl"

    manifest = write_archive(result, path, run_id="test-p02", seed=4, config=cfg)

    assert manifest["n_evaluated"] == result.n_evaluated
    assert manifest["archive_sha256"]
    assert path.read_text().count("\n") == result.n_evaluated
    assert path.with_suffix(".jsonl.manifest.json").is_file()
