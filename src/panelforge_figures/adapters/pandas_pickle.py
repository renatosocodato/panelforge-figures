"""Pandas pickle adapter — read a `.pkl` produced by `DataFrame.to_pickle`.

Pickle is unsafe in general; this adapter only accepts files whose suffix is
`.pkl` or `.pickle`, uses `pandas.read_pickle`, and refuses to follow symlinks
outside the current working directory when `restrict_to_cwd=True`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)


def load_pandas_pickle(
    source: str | Path,
    *,
    restrict_to_cwd: bool = True,
    columns: dict[str, str] | None = None,
    **_: Any,
) -> pd.DataFrame | dict:
    path = Path(source).resolve()
    if path.suffix.lower() not in {".pkl", ".pickle"}:
        raise ValueError(f"not a pickle suffix: {path}")
    if restrict_to_cwd:
        cwd = Path.cwd().resolve()
        try:
            path.relative_to(cwd)
        except ValueError as exc:
            raise PermissionError(
                f"pickle adapter refuses to load from outside cwd: {path}"
            ) from exc
    obj = pd.read_pickle(path)
    if isinstance(obj, pd.DataFrame) and columns:
        obj = obj.rename(columns=columns)
    log.debug("loaded pickle %s (%s)", path, type(obj).__name__)
    return obj
