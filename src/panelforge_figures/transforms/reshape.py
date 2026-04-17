"""Reshape transforms: long↔wide."""

from __future__ import annotations

from typing import Sequence

import pandas as pd


def melt_long(
    df: pd.DataFrame,
    *,
    id_vars: Sequence[str],
    value_vars: Sequence[str] | None = None,
    var_name: str = "variable",
    value_name: str = "value",
) -> pd.DataFrame:
    return df.melt(id_vars=list(id_vars), value_vars=list(value_vars) if value_vars else None,
                   var_name=var_name, value_name=value_name)


def pivot_wide(
    df: pd.DataFrame,
    *,
    index: str | Sequence[str],
    columns: str,
    values: str,
    aggfunc: str = "first",
) -> pd.DataFrame:
    return df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc).reset_index()
