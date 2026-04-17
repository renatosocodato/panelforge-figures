"""Tabular adapter: CSV / TSV / Parquet / Feather / JSON-lines into a DataFrame."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

_READERS = {
    ".csv": lambda p, opts: pd.read_csv(p, **opts),
    ".tsv": lambda p, opts: pd.read_csv(p, sep="\t", **opts),
    ".txt": lambda p, opts: pd.read_csv(p, sep=None, engine="python", **opts),
    ".parquet": lambda p, opts: pd.read_parquet(p, **opts),
    ".pq": lambda p, opts: pd.read_parquet(p, **opts),
    ".feather": lambda p, opts: pd.read_feather(p, **opts),
    ".jsonl": lambda p, opts: pd.read_json(p, lines=True, **opts),
}


def load_tabular(
    source: str | Path,
    *,
    columns: dict[str, str] | None = None,
    select: list[str] | None = None,
    **reader_kwargs: Any,
) -> pd.DataFrame:
    """Read a tabular source, optionally rename columns / select a subset.

    Returns a DataFrame. `columns` is a rename map (`{source_col: new_name}`).
    `select` is a post-rename keep list.
    """
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    reader = _READERS.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"unsupported tabular format: {path.suffix}")
    df = reader(path, reader_kwargs)
    if columns:
        df = df.rename(columns=columns)
    if select:
        missing = [c for c in select if c not in df.columns]
        if missing:
            raise KeyError(f"select columns missing from {path}: {missing}")
        df = df[select]
    log.debug("tabular adapter loaded %s shape=%s", path, df.shape)
    return df
