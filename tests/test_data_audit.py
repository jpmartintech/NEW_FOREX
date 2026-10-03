"""Acceptance tests for a streaming, pre-holdout data audit."""
from __future__ import annotations

from pathlib import Path

import pytest

from conftest import make_config
from new_forex.data.audit import audit_raw_csv, discover_symbols
from new_forex.data.m15 import load_m15
from new_forex.data.splits import DataAccessPolicy, Partition


def _write_csv(path: Path) -> None:
    path.write_text(
        "Date,Time,Open,High,Low,Close,Volume\n"
        "20221230,23:45:00,1,1.1,0.9,1.05,10\n"
        "20230101,00:00:00,not-a-number,broken,broken,broken,broken\n"
    )


def test_audit_stops_before_final_holdout_payload(tmp_path: Path) -> None:
    raw = tmp_path / "EURUSD_15M.csv"
    _write_csv(raw)

    result = audit_raw_csv(raw, "EURUSD", DataAccessPolicy.load())

    assert result.symbol == "EURUSD"
    assert result.rows_by_partition[Partition.DEV_TRAIN] == 0
    assert result.rows_by_partition[Partition.PROCEDURE_VALIDATION] == 1
    assert result.rows_by_partition[Partition.FINAL_HOLDOUT] is None
    assert result.final_holdout_sealed is True
    assert result.last_pre_holdout == "2022-12-30T23:45:00"
    assert result.gap_count == 0


def test_audit_reports_gaps_without_fabricating_bars(tmp_path: Path) -> None:
    raw = tmp_path / "EURUSD_15M.csv"
    raw.write_text(
        "Date,Time,Open,High,Low,Close,Volume\n"
        "20221230,23:15:00,1,1.1,0.9,1.05,10\n"
        "20221230,23:45:00,1,1.1,0.9,1.05,10\n"
    )

    result = audit_raw_csv(raw, "EURUSD", DataAccessPolicy.load())

    assert result.rows_by_partition[Partition.PROCEDURE_VALIDATION] == 2
    assert result.gap_count == 1
    assert result.max_gap_minutes == 30
    assert result.weekend_gap_count == 0
    assert result.unexpected_gap_count == 1


def test_discovery_is_local_and_excludes_nested_or_non_m15_files(tmp_path: Path) -> None:
    (tmp_path / "EURUSD_15M.csv").touch()
    (tmp_path / "GBPUSD_15M.csv").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "crypto").mkdir()
    (tmp_path / "crypto" / "BTCUSDT_15M.csv").touch()

    assert discover_symbols(tmp_path) == ("EURUSD", "GBPUSD")


def test_audit_rejects_duplicate_pre_holdout_timestamp(tmp_path: Path) -> None:
    raw = tmp_path / "EURUSD_15M.csv"
    raw.write_text(
        "Date,Time,Open,High,Low,Close,Volume\n"
        "20221230,23:45:00,1,1.1,0.9,1.05,10\n"
        "20221230,23:45:00,1,1.1,0.9,1.05,10\n"
    )

    with pytest.raises(ValueError, match="duplicate"):
        audit_raw_csv(raw, "EURUSD", DataAccessPolicy.load())


def test_canonical_cache_is_pre_holdout_and_provenanced(tmp_path: Path) -> None:
    cfg = make_config(tmp_path, holdout="2023-01-01 00:00:00")
    cfg.raw_dir.mkdir(parents=True)
    raw = cfg.raw_dir / "EURUSD_15M.csv"
    raw.write_text(
        "Date,Time,Open,High,Low,Close,Volume\n"
        "20221230,23:45:00,1,1.1,0.9,1.05,10\n"
        "20230101,00:00:00,1.05,1.1,1.0,1.08,11\n"
    )

    canonical = load_m15("EURUSD", cfg)

    assert len(canonical) == 1
    assert canonical["ts_local"].max() < cfg.holdout_start_local
    assert canonical.attrs["source_sha256"]
    assert (cfg.derived_dir / "m15" / "EURUSD.parquet").is_file()
