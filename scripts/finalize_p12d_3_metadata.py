"""Add source dataset hashes to the completed P12D.3 manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/p12d_3_cross_generation.yaml"
P12C = ROOT / "reports/p12c_artifacts"
OUT = ROOT / "reports/p12d_3_artifacts"


def hash_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    config = yaml.safe_load(CONFIG.read_bytes())
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["p12c_source_sha256"] = {
        label: hash_files(list((P12C / label).glob("part-*.parquet")))
        for label in config["generations"]
    }
    manifest["p12c_part_counts"] = {
        label: len(list((P12C / label).glob("part-*.parquet")))
        for label in config["generations"]
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
