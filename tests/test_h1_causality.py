"""P01 acceptance tests for causal M15-to-H1 derivation."""
from __future__ import annotations

import numpy as np

from new_forex.data.h1 import build_h1


def test_missing_m15_bars_make_incomplete_h1_without_fabrication(m15_synth) -> None:
    h1 = build_h1(m15_synth)

    assert (h1["n_m15"] >= 1).all()
    assert (h1["n_m15"] <= 4).all()
    assert (~h1["complete"]).any()
    assert (h1["m15_end"] - h1["m15_start"] == h1["n_m15"]).all()


def test_closed_h1_prefix_is_invariant_to_future_m15_changes(m15_synth) -> None:
    cut = len(m15_synth) // 2
    full = build_h1(m15_synth)
    changed = m15_synth.copy()
    changed.loc[cut:, "close"] *= 1.25
    changed.loc[cut:, "high"] *= 1.25
    changed.loc[cut:, "low"] *= 1.25
    altered = build_h1(changed)

    closed = full["close_ts_utc"] <= m15_synth["ts_utc"].iloc[cut - 1]
    for column in ("open", "high", "low", "close", "volume", "n_m15"):
        np.testing.assert_array_equal(full.loc[closed, column], altered.loc[closed, column])
