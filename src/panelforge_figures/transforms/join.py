"""Join / merge transforms."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


def left_join(left: pd.DataFrame, right: pd.DataFrame, *, on: str | Sequence[str]) -> pd.DataFrame:
    return left.merge(right, on=list(on) if isinstance(on, (list, tuple)) else on, how="left")


def merge_on(left: pd.DataFrame, right: pd.DataFrame, *, on: str | Sequence[str], how: str = "inner") -> pd.DataFrame:
    return left.merge(right, on=list(on) if isinstance(on, (list, tuple)) else on, how=how)
