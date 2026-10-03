"""Chronological partition policy for NEW_FOREX data access.

All windows are half-open, ``[start, end)``, and timestamps are interpreted in
the configured source timezone as naive local timestamps. The final holdout is
metadata-only until a later release gate supplies a verified unlock manifest;
``release_unlocked`` is intentionally not sufficient on its own.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from new_forex.provenance import load_config


class Partition(StrEnum):
    DEV_TRAIN = "dev_train"
    DEVELOPMENT_WF = "development_wf"
    PROCEDURE_VALIDATION = "procedure_validation"
    FINAL_HOLDOUT = "final_holdout"


class FinalHoldoutSealed(PermissionError):
    """Raised whenever a normal pipeline read would expose final holdout rows."""


@dataclass(frozen=True)
class PartitionWindow:
    partition: Partition
    start: pd.Timestamp
    end: pd.Timestamp | None

    def contains(self, timestamp: pd.Timestamp) -> bool:
        timestamp = _timestamp(timestamp)
        return timestamp >= self.start and (self.end is None or timestamp < self.end)


@dataclass(frozen=True)
class DataAccessPolicy:
    timezone: str
    windows: tuple[PartitionWindow, ...]

    @classmethod
    def load(cls) -> DataAccessPolicy:
        config = load_config("splits")
        windows = tuple(
            PartitionWindow(
                partition=Partition(name),
                start=_timestamp(bounds[0]),
                end=None if bounds[1] is None else _timestamp(bounds[1]),
            )
            for name, bounds in config["partitions"].items()
        )
        policy = cls(timezone=str(config["timezone"]), windows=windows)
        policy._validate()
        return policy

    def _validate(self) -> None:
        expected = tuple(Partition)
        actual = tuple(window.partition for window in self.windows)
        if actual != expected:
            raise ValueError(f"partitions must be ordered as {[p.value for p in expected]}")
        for previous, current in zip(self.windows[:-1], self.windows[1:], strict=True):
            if previous.end is None or previous.end != current.start:
                raise ValueError("partitions must be contiguous half-open intervals")
        if self.windows[-1].end is not None:
            raise ValueError("final_holdout must be open-ended")

    def window(self, partition: Partition) -> PartitionWindow:
        return next(item for item in self.windows if item.partition is partition)

    def partition_for(self, timestamp: pd.Timestamp) -> Partition:
        timestamp = _timestamp(timestamp)
        for window in self.windows:
            if window.contains(timestamp):
                return window.partition
        raise ValueError(f"timestamp {timestamp} precedes configured data range")

    def assert_readable(self, partition: Partition, *, release_unlocked: bool = False) -> None:
        if partition is Partition.FINAL_HOLDOUT:
            raise FinalHoldoutSealed("final holdout is sealed until the explicit P09 release gate")

    def assert_range(self, start: str | pd.Timestamp, end: str | pd.Timestamp) -> Partition:
        start_ts, end_ts = _timestamp(start), _timestamp(end)
        if end_ts <= start_ts:
            raise ValueError("end must be after start")
        start_partition = self.partition_for(start_ts)
        end_partition = self.partition_for(end_ts - pd.Timedelta(nanoseconds=1))
        if start_partition is not end_partition:
            raise ValueError("requested range must stay within a single partition")
        self.assert_readable(start_partition)
        return start_partition


def _timestamp(value: str | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tz is not None:
        raise ValueError("partition timestamps must be timezone-naive local timestamps")
    return timestamp
