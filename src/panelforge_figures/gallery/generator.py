"""Regenerate + diff the committed gallery under docs/gallery/.

Each recipe's `.demo_contract()` drives a small 2.5×2.5 inch, 200-dpi render.
The output path is `docs/gallery/<modality>/<recipe>.png`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np

from ..core import apply_base_style
from ..core.contract import ensure_all_imported, list_recipes

log = logging.getLogger(__name__)

GALLERY_DPI: int = 200
GALLERY_SIZE_IN: tuple[float, float] = (2.5, 2.5)


def regenerate_gallery(out_root: str | Path = "docs/gallery") -> list[Path]:
    """Render each registered recipe to docs/gallery/<modality>/<name>.png."""
    ensure_all_imported()
    apply_base_style()
    out_root = Path(out_root)
    paths: list[Path] = []
    for entry in list_recipes():
        modality = entry.metadata.modality
        name = entry.metadata.name
        target_dir = out_root / modality
        target_dir.mkdir(parents=True, exist_ok=True)
        out = target_dir / f"{name}.png"
        fig, ax = plt.subplots(figsize=GALLERY_SIZE_IN, dpi=GALLERY_DPI)
        try:
            contract = entry.demo_contract()
            entry.render(contract, ax=ax)
        except Exception:
            log.exception("gallery render failed for %s.%s", modality, name)
            plt.close(fig)
            continue
        fig.tight_layout(pad=0.4)
        fig.savefig(out, dpi=GALLERY_DPI, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        paths.append(out)
    return paths


def _load_image(path: Path) -> np.ndarray | None:
    if not path.is_file():
        return None
    import matplotlib.image as mpimg
    return mpimg.imread(path)


def diff_gallery(
    root: str | Path = "docs/gallery", *, threshold: float = 0.02
) -> list[tuple[str, float]]:
    """Compare committed gallery PNGs to freshly rendered ones via L1 distance."""
    ensure_all_imported()
    apply_base_style()
    root = Path(root)
    diffs: list[tuple[str, float]] = []
    for entry in list_recipes():
        committed = root / entry.metadata.modality / f"{entry.metadata.name}.png"
        committed_img = _load_image(committed)
        if committed_img is None:
            diffs.append((entry.full_name, 1.0))
            continue
        fig, ax = plt.subplots(figsize=GALLERY_SIZE_IN, dpi=GALLERY_DPI)
        try:
            entry.render(entry.demo_contract(), ax=ax)
        except Exception:
            plt.close(fig)
            diffs.append((entry.full_name, 1.0))
            continue
        fig.tight_layout(pad=0.4)
        tmp = Path(".pf_gallery_tmp.png")
        fig.savefig(tmp, dpi=GALLERY_DPI, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        fresh = _load_image(tmp)
        tmp.unlink(missing_ok=True)
        if fresh is None or fresh.shape != committed_img.shape:
            diffs.append((entry.full_name, 1.0))
            continue
        l1 = float(np.abs(fresh.astype(float) - committed_img.astype(float)).mean()) / 255.0
        if l1 > threshold:
            diffs.append((entry.full_name, l1))
    return diffs


def iter_recipe_paths(out_root: str | Path = "docs/gallery") -> Iterable[Path]:
    for entry in list_recipes():
        yield Path(out_root) / entry.metadata.modality / f"{entry.metadata.name}.png"
