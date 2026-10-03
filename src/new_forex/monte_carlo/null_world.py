"""Matched null-world GA+selection control for winner's-curse accounting."""
from __future__ import annotations

from math import ceil

import numpy as np

from new_forex.generators.genetic import GAConfig, run_genetic
from new_forex.selection.ranking import SelectionConfig, metrics_from_returns, select_candidates


def run_null_worlds(*, worlds: int, candidates_per_world: int, top_k: int, seed: int) -> dict[str, float | int]:
    if worlds < 1 or candidates_per_world < top_k or top_k < 1:
        raise ValueError("worlds, candidates_per_world and top_k are inconsistent")
    root = np.random.default_rng(seed)
    selected_positive = 0
    selected_total = 0
    for _world in range(worlds):
        world_rng = np.random.default_rng(int(root.integers(2**63)))

        def fitness(batch, rng=world_rng):
            return rng.normal(0.0, 1.0, len(batch))

        population = min(100, candidates_per_world)
        elite = min(5, population - 1)
        per_generation = population - elite
        generations = max(1, ceil((candidates_per_world - population) / per_generation) + 1)
        cfg = GAConfig(population=population, generations=generations,
                       max_unique_evaluations=candidates_per_world, elite=elite, tournament=3)
        ga = run_genetic("NULL", fitness, cfg, seed=int(world_rng.integers(2**63)))
        candidates = [{"canonical_hash": key, "metrics": metrics_from_returns([score], 0.0)}
                      for key, (_, score) in ga.archive.items()]
        selected = select_candidates(candidates, SelectionConfig(top_k=top_k, min_trades=1, min_mean_r=-np.inf,
                                                                   min_profit_factor=0.0))
        selected_total += len(selected.selected)
        selected_positive += sum(selected.metrics[key].mean_r > 0 for key in selected.selected)
    return {"worlds": worlds, "selected_candidates": selected_total,
            "positive_selected_fraction": selected_positive / selected_total if selected_total else 0.0}
