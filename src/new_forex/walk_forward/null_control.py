"""Frozen P10 null-control policy helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class NullControlPolicy:
    policy_id: str
    sha256: str
    replicates: int
    seed_base: int
    complete_status: str


def load_null_control_policy(path: str | Path) -> NullControlPolicy:
    raw = Path(path).read_bytes()
    data = yaml.safe_load(raw)
    if data["policy_id"] != "p10-null-control-v1":
        raise ValueError("unexpected P10 null-control policy")
    control = data["controls"]["A_random_selection_same_universe"]
    complete = data["controls"]["B_complete_null_world"]
    return NullControlPolicy(
        policy_id=data["policy_id"],
        sha256=hashlib.sha256(raw).hexdigest(),
        replicates=int(control["replicates"]),
        seed_base=int(control["seed_base"]),
        complete_status=str(complete["status"]),
    )


def random_selection_indices(seed: int, n_candidates: int, n_selected: int = 5) -> tuple[int, ...]:
    """Return deterministic selection indices without changing the candidate universe."""
    import numpy as np

    if n_candidates < n_selected:
        raise ValueError("candidate universe smaller than frozen selection size")
    return tuple(sorted(np.random.default_rng(seed).choice(n_candidates, n_selected, replace=False).tolist()))
