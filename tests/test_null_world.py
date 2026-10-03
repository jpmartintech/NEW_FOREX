"""P04 null-world control for GA plus selection false-discovery accounting."""
from __future__ import annotations

from new_forex.monte_carlo.null_world import run_null_worlds


def test_null_world_control_is_seed_reproducible_and_records_selection_bias() -> None:
    first = run_null_worlds(worlds=8, candidates_per_world=80, top_k=10, seed=20261002)
    second = run_null_worlds(worlds=8, candidates_per_world=80, top_k=10, seed=20261002)

    assert first == second
    assert first["worlds"] == 8
    assert first["selected_candidates"] == 80
    assert 0.0 <= first["positive_selected_fraction"] <= 1.0
