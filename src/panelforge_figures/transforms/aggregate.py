"""Aggregation transforms."""

from __future__ import annotations

from typing import Sequence

import pandas as pd


def aggregate_group(
    df: pd.DataFrame,
    *,
    group_cols: Sequence[str],
    value_col: str,
    how: str = "mean",
    rename: str | None = None,
) -> pd.DataFrame:
    """Group by `group_cols`, aggregate `value_col` with `how`.

    `how` is any pandas aggregation name (`mean`, `median`, `sum`, `std`,
    `count`, `first`, etc.).
    """
    out = df.groupby(list(group_cols), dropna=False)[value_col].agg(how).reset_index()
    if rename:
        out = out.rename(columns={value_col: rename})
    return out
