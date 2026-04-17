"""Derived-column transforms: simple expressions and unit conversions.

Expressions are restricted to `pandas.DataFrame.eval`-compatible strings, which
evaluate against existing columns. No arbitrary-code execution.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def derive_columns(
    df: pd.DataFrame,
    *,
    expressions: dict[str, str],
    **_: Any,
) -> pd.DataFrame:
    """Add new columns via `DataFrame.eval`.

    `expressions` is a mapping `{new_col: pandas-eval expression}`, e.g.
        {"log10_dwell_s": "log10(dwell_s)"}
    """
    out = df.copy()
    for new_col, expr in expressions.items():
        out[new_col] = out.eval(expr)
    return out
