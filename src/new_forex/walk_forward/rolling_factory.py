"""Rolling generation window arithmetic."""
from __future__ import annotations

import pandas as pd


def generation_windows(birth: str) -> dict[str, tuple[str, str]]:
    """Return half-open train, development and next-quarter forward windows."""
    born = pd.Timestamp(birth)
    train_end = born - pd.DateOffset(months=24)
    train_start = train_end - pd.DateOffset(months=96)
    return {"training": (train_start.strftime("%Y-%m-%d"),
                          train_end.strftime("%Y-%m-%d")),
            "development_wf": ((born - pd.DateOffset(months=24)).strftime("%Y-%m-%d"), born.strftime("%Y-%m-%d")),
            "forward": (born.strftime("%Y-%m-%d"), (born + pd.DateOffset(months=3)).strftime("%Y-%m-%d"))}
