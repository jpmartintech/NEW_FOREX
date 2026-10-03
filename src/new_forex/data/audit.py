"""Streaming audit of raw M15 files without materialising the final holdout."""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from new_forex.data.m15 import RAW_COLUMNS
from new_forex.data.splits import DataAccessPolicy, Partition


@dataclass(frozen=True)
class AuditResult:
    symbol: str
    rows_by_partition: dict[Partition, int | None]
    sha256_by_partition: dict[Partition, str | None]
    first_pre_holdout: str | None
    last_pre_holdout: str | None
    final_holdout_sealed: bool
    gap_count: int
    max_gap_minutes: int
    weekend_gap_count: int
    unexpected_gap_count: int


def discover_symbols(raw_dir: Path) -> tuple[str, ...]:
    """Discover only direct child ``*_15M.csv`` files, never nested datasets."""
    return tuple(sorted(path.name.removesuffix("_15M.csv") for path in Path(raw_dir).glob("*_15M.csv")))


def audit_raw_csv(path: Path, symbol: str, policy: DataAccessPolicy) -> AuditResult:
    """Audit accessible rows and stop before parsing the first final-holdout payload.

    The raw line is hashed only for accessible partitions. Once a timestamp is
    classified as ``FINAL_HOLDOUT``, the function stops immediately; this keeps
    malformed or otherwise sensitive payloads beyond the sealed boundary out of
    the audit process.
    """
    rows: dict[Partition, int | None] = {partition: 0 for partition in Partition}
    hashes: dict[Partition, hashlib._Hash | None] = {
        partition: hashlib.sha256() if partition is not Partition.FINAL_HOLDOUT else None for partition in Partition
    }
    first_pre_holdout: pd.Timestamp | None = None
    last_pre_holdout: pd.Timestamp | None = None
    previous: pd.Timestamp | None = None
    gap_count = 0
    max_gap_minutes = 0
    weekend_gap_count = 0

    with Path(path).open("rb") as fh:
        header = fh.readline().decode("utf-8-sig").rstrip("\r\n")
        if header.split(",") != RAW_COLUMNS:
            raise ValueError(f"{path.name}: unexpected columns {header!r}")
        for raw_line in fh:
            if not raw_line.strip():
                continue
            text = raw_line.decode("utf-8").rstrip("\r\n")
            fields = next(csv.reader([text]))
            if len(fields) < 2:
                raise ValueError(f"{path.name}: malformed timestamp row")
            try:
                timestamp = pd.Timestamp(datetime.strptime(f"{fields[0]} {fields[1]}", "%Y%m%d %H:%M:%S"))
            except ValueError as exc:
                raise ValueError(f"{path.name}: unparseable timestamp before holdout") from exc
            partition = policy.partition_for(timestamp)
            if partition is Partition.FINAL_HOLDOUT:
                break
            _validate_accessible_row(path, fields, timestamp, previous)
            if previous is not None:
                gap_minutes = int((timestamp - previous).total_seconds() // 60)
                if gap_minutes > 15:
                    gap_count += 1
                    max_gap_minutes = max(max_gap_minutes, gap_minutes)
                    if previous.weekday() == 4 and timestamp.weekday() == 0:
                        weekend_gap_count += 1
            previous = timestamp
            first_pre_holdout = first_pre_holdout or timestamp
            last_pre_holdout = timestamp
            rows[partition] = int(rows[partition]) + 1
            assert hashes[partition] is not None
            hashes[partition].update(raw_line)

    rows[Partition.FINAL_HOLDOUT] = None
    hashes[Partition.FINAL_HOLDOUT] = None
    return AuditResult(
        symbol=symbol,
        rows_by_partition=rows,
        sha256_by_partition={
            partition: digest.hexdigest() if digest is not None else None for partition, digest in hashes.items()
        },
        first_pre_holdout=None if first_pre_holdout is None else first_pre_holdout.isoformat(),
        last_pre_holdout=None if last_pre_holdout is None else last_pre_holdout.isoformat(),
        final_holdout_sealed=True,
        gap_count=gap_count,
        max_gap_minutes=max_gap_minutes,
        weekend_gap_count=weekend_gap_count,
        unexpected_gap_count=gap_count - weekend_gap_count,
    )


def _validate_accessible_row(path: Path, fields: list[str], timestamp: pd.Timestamp, previous: pd.Timestamp | None) -> None:
    if len(fields) != len(RAW_COLUMNS):
        raise ValueError(f"{path.name}: expected {len(RAW_COLUMNS)} fields")
    if previous is not None and timestamp <= previous:
        kind = "duplicate" if timestamp == previous else "backward timestamp"
        raise ValueError(f"{path.name}: {kind} timestamp {timestamp}")
    if timestamp.minute % 15 != 0 or timestamp.second != 0:
        raise ValueError(f"{path.name}: timestamp off M15 grid {timestamp}")
    try:
        open_, high, low, close = (float(fields[index]) for index in range(2, 6))
    except ValueError as exc:
        raise ValueError(f"{path.name}: unparseable OHLC before holdout") from exc
    if min(open_, high, low, close) <= 0 or high < max(open_, close) or low > min(open_, close):
        raise ValueError(f"{path.name}: inconsistent OHLC before holdout")
