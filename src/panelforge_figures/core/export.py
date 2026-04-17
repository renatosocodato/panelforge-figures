"""Figure export — PDF/PNG/SVG at publication dpi with font preservation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)

DEFAULT_FORMATS: tuple[str, ...] = ("pdf", "png", "svg")
DEFAULT_DPI: int = 600


def export_figure(
    fig,
    stem: str | Path,
    *,
    formats: Iterable[str] = DEFAULT_FORMATS,
    dpi: int = DEFAULT_DPI,
    outdir: str | Path | None = None,
    transparent: bool = False,
) -> list[Path]:
    """Save `fig` to `stem.<fmt>` for each requested format. Returns paths.

    - PDF/SVG keep fonts as text (via rcParams configured in style.py).
    - PNG uses `dpi`; vector formats ignore dpi but use bbox='tight'.
    - If `outdir` is provided, files land there with `stem` as basename.
    """
    stem = Path(stem)
    base = Path(outdir) / stem.name if outdir is not None else stem
    base.parent.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for fmt in formats:
        out = base.with_suffix(f".{fmt}")
        fig.savefig(out, dpi=dpi, bbox_inches="tight", transparent=transparent)
        saved.append(out)
        log.debug("saved %s", out)
    return saved


def multi_format_export(
    fig, stem: str | Path, outdir: str | Path, formats: Iterable[str] = DEFAULT_FORMATS
) -> list[Path]:
    """Alias preserving semantics for manifests — enforces outdir."""
    return export_figure(fig, stem, outdir=outdir, formats=formats)
