"""Local adapter skeleton — rename, edit, drop into figures/adapters/local/.

See skill/references/adapter_guide.md for a worked SALib example.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def load(source: str | Path, **options: Any):
    """Load `source` and return a recipe-appropriate payload.

    Keep this under ~80 lines. Push heavy computation upstream into
    your analysis pipeline.
    """
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"no such file: {path}")

    df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_parquet(path)

    if options.get("rename"):
        df = df.rename(columns=options["rename"])
    if options.get("select"):
        df = df[options["select"]]

    return df
