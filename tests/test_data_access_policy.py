"""Acceptance tests for the P01 chronological data-access policy."""
from __future__ import annotations

import pandas as pd
import pytest

from new_forex.data.splits import DataAccessPolicy, FinalHoldoutSealed, Partition


def test_policy_has_binding_half_open_partitions() -> None:
    policy = DataAccessPolicy.load()

    assert policy.partition_for(pd.Timestamp("2003-01-01")) is Partition.DEV_TRAIN
    assert policy.partition_for(pd.Timestamp("2014-12-31 23:45")) is Partition.DEV_TRAIN
    assert policy.partition_for(pd.Timestamp("2015-01-01")) is Partition.DEVELOPMENT_WF
    assert policy.partition_for(pd.Timestamp("2019-01-01")) is Partition.PROCEDURE_VALIDATION
    assert policy.partition_for(pd.Timestamp("2023-01-01")) is Partition.FINAL_HOLDOUT


def test_train_and_procedure_reads_cannot_cross_or_enter_holdout() -> None:
    policy = DataAccessPolicy.load()

    policy.assert_readable(Partition.DEV_TRAIN)
    policy.assert_readable(Partition.DEVELOPMENT_WF)
    policy.assert_readable(Partition.PROCEDURE_VALIDATION)
    with pytest.raises(FinalHoldoutSealed):
        policy.assert_readable(Partition.FINAL_HOLDOUT)
    with pytest.raises(ValueError, match="single partition"):
        policy.assert_range("2014-12-31", "2015-01-01 00:15")


def test_final_holdout_cannot_be_enabled_by_an_ordinary_policy_flag() -> None:
    policy = DataAccessPolicy.load()

    with pytest.raises(FinalHoldoutSealed):
        policy.assert_readable(Partition.FINAL_HOLDOUT, release_unlocked=True)
