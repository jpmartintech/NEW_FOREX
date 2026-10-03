from pathlib import Path

import pytest

from new_forex.walk_forward.null_control import (
    load_null_control_policy,
    random_selection_indices,
)


def test_p10_null_policy_is_frozen_and_distinguishes_controls() -> None:
    policy = load_null_control_policy(Path("configs/p10_null_control.yaml"))
    assert policy.policy_id == "p10-null-control-v1"
    assert policy.replicates == 100
    assert policy.complete_status == "proposed_not_executed"
    assert len(policy.sha256) == 64


def test_random_selection_is_reproducible_and_without_replacement() -> None:
    a = random_selection_indices(20261010, 1000, 5)
    assert a == random_selection_indices(20261010, 1000, 5)
    assert len(a) == len(set(a)) == 5


def test_random_selection_rejects_small_universe() -> None:
    with pytest.raises(ValueError):
        random_selection_indices(1, 4, 5)
