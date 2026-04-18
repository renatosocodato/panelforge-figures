"""Local adapter skeleton — copy to figures/adapters/local/<name>.py.

The adapter MUST define a callable named `load` with signature:
    load(source, **options) -> DataFrame | dict | np.ndarray

It MUST NOT:
  - open network connections
  - execute shell commands
  - modify the installed panelforge_figures package
  - return data with a shape different from the recipe's RecipeContract

Referenced in manifest as `adapter: local.<name>` where `<name>` is this
module's filename without `.py`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)


def load(source: str | Path, **options: Any):
    """Load `source` and return a recipe-appropriate payload.

    Parameters
    ----------
    source:
        Path to the data file, relative to the manuscript repo root.
    options:
        Keyword options forwarded from the manifest's `data.options`.

    Returns
    -------
    DataFrame | dict | np.ndarray
        Whatever the targeted recipe's contract expects.
    """
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"local adapter: no such file {path}")

    # ─── Example 1: load a bespoke pickle and reshape ──────────────────
    if path.suffix == ".pkl":
        obj = pd.read_pickle(path)
        # ...reshape obj into the contract's expected dict...
        return obj

    # ─── Example 2: load a CSV with a known mapping ───────────────────
    if path.suffix == ".csv":
        df = pd.read_csv(path)
        if options.get("rename"):
            df = df.rename(columns=options["rename"])
        return df

    raise ValueError(f"local adapter does not know how to load {path}")
