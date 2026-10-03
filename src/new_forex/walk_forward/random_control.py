"""Deterministic P11 Control A sampling and identity checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class RandomControlPolicy:
    policy_id: str
    sha256: str
    generations: int
    replicates: int
    selection_size: int
    seed_base: int


def load_policy(path: str | Path) -> RandomControlPolicy:
    raw = Path(path).read_bytes()
    data = yaml.safe_load(raw)
    if data["policy_id"] != "p11-random-selection-control-a-v1":
        raise ValueError("unexpected P11 policy")
    if data["sampling"] != "uniform_without_replacement":
        raise ValueError("P11 sampling policy changed")
    return RandomControlPolicy(data["policy_id"], hashlib.sha256(raw).hexdigest(),
                               int(data["generations"]), int(data["replicates_per_generation"]),
                               int(data["selection_size"]), int(data["seed"]["base"]))


def sample_excluding(candidates: list[str], excluded: set[str], *, seed: int, size: int) -> tuple[str, ...]:
    universe = [item for item in candidates if item not in excluded]
    if len(universe) < size:
        raise ValueError("eligible universe is smaller than frozen control selection size")
    indices = np.random.default_rng(seed).choice(len(universe), size, replace=False)
    return tuple(universe[int(i)] for i in indices)


def seed_for(seed_base: int, generation_index: int, replicate_index: int) -> int:
    return int(seed_base + generation_index * 1000 + replicate_index)
