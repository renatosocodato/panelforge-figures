"""NumPy .npz adapter — returns a dict of {key: ndarray}."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def load_numpy_npz(source: str | Path, *, select: list[str] | None = None, **_: Any) -> dict:
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    data = np.load(path, allow_pickle=False)
    keys = list(data.files) if select is None else select
    missing = [k for k in keys if k not in data.files]
    if missing:
        raise KeyError(f"npz {path} missing keys: {missing}")
    return {k: data[k] for k in keys}
