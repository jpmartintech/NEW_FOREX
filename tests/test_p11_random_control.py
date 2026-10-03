from pathlib import Path

import pytest

from new_forex.walk_forward.random_control import load_policy, sample_excluding, seed_for


def test_p11_policy_and_seed_are_frozen() -> None:
    policy = load_policy(Path("configs/random_selection_control.yaml"))
    assert policy.policy_id == "p11-random-selection-control-a-v1"
    assert policy.generations == 16
    assert policy.replicates == 100
    assert policy.selection_size == 5
    assert seed_for(policy.seed_base, 2, 7) == 20263017
    assert len(policy.sha256) == 64


def test_sampling_is_reproducible_excludes_selected_and_has_no_duplicates() -> None:
    candidates = [f"h{i}" for i in range(20)]
    selection = sample_excluding(candidates, {"h0", "h1", "h2", "h3", "h4"}, seed=42, size=5)
    assert selection == sample_excluding(candidates, {"h0", "h1", "h2", "h3", "h4"}, seed=42, size=5)
    assert len(selection) == len(set(selection)) == 5
    assert not set(selection) & {"h0", "h1", "h2", "h3", "h4"}


def test_sampling_rejects_insufficient_universe() -> None:
    with pytest.raises(ValueError):
        sample_excluding(["a", "b", "c", "d", "e"], {"a"}, seed=1, size=5)
