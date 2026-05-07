"""Pydantic schema for the multi-panel composition layer (Sprint 1C / v1.7.0).

This is a separate, lighter-weight schema than ``manifest.schema``.  Where
``manifest.schema`` describes a *project* (many figures, many bindings,
data-discovery flow), this module describes a single multi-panel
**figure** — its grid layout, the recipe to render in each cell, optional
freeform bboxes, and cross-panel axis linking.

The companion engine in ``figure_composition.py`` consumes a
:class:`FigureSpec` and produces one PDF per figure via matplotlib
``GridSpec``.

See ``docs/spec_composition_layer.md`` (v1.7.0 target) for the grammar
rationale.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# ─────────────────────────── layouts ────────────────────────────────────


class GridLayout(BaseModel):
    """Regular row-major grid: `rows × cols` cells, each panel in one cell.

    Panels declared in :class:`FigureSpec.panels` are placed in row-major
    order (i.e. ``(panels[0] → row=0,col=0)``, ``(panels[1] → row=0,col=1)``,
    …).  Use :class:`GridspecLayout` if you need per-panel row/col spans.
    """

    type: Literal["grid"] = "grid"
    rows: int = Field(..., ge=1, le=10)
    cols: int = Field(..., ge=1, le=10)
    height_ratios: tuple[float, ...] | None = None
    width_ratios: tuple[float, ...] | None = None
    hspace: float = 0.30
    wspace: float = 0.25


class GridspecLayout(BaseModel):
    """Custom gridspec — each panel declares its own (row, col, span)."""

    type: Literal["gridspec"] = "gridspec"
    rows: int = Field(..., ge=1, le=10)
    cols: int = Field(..., ge=1, le=10)
    hspace: float = 0.30
    wspace: float = 0.25


class FreeformLayout(BaseModel):
    """Absolute placement: each panel declares an [x, y, w, h] bbox in figure coords."""

    type: Literal["freeform"] = "freeform"


Layout = Annotated[
    GridLayout | GridspecLayout | FreeformLayout,
    Field(discriminator="type"),
]


# ─────────────────────────── panels ─────────────────────────────────────


class PanelSpec(BaseModel):
    """One node in the figure graph — a single recipe rendered into a single axes."""

    id: str = Field(..., min_length=1, max_length=4)         # "A", "B", "F-CKO" …
    recipe: str = Field(..., min_length=1)                   # full_name e.g. "modality.recipe"
    data: Path | None = None                                 # CSV/parquet/etc; None → demo
    caption: str = ""

    # Position (mutually exclusive depending on layout kind):
    # GridspecLayout requires (row, col, row_span, col_span).
    grid_position: tuple[int, int, int, int] | None = None
    # FreeformLayout requires (x, y, w, h) in figure-relative coords [0..1].
    freeform_bbox: tuple[float, float, float, float] | None = None

    # Cross-panel linking — references another panel's ``id`` in the same figure.
    shared_axis_with: str | None = None

    # A/B/C marker placement, in axes-fraction coords.
    label_position: tuple[float, float] = (0.02, 0.95)

    # Per-panel aesthetic overrides; merged on top of figure-level ``shared_aesthetic``.
    aesthetic_overrides: dict[str, Any] = Field(default_factory=dict)


class PartitionedPanelSpec(BaseModel):
    """Auto-tile a single recipe across distinct values of a tag.

    ``base_id`` is a hint for the synthesised ids — e.g. ``base_id="C-F"``
    paired with a tag that has values ``["CTL", "CKO"]`` produces panels
    ``C-CTL`` and ``C-CKO``.  Engine-side expansion is intentionally
    deferred to a follow-up patch (Sprint 1C-bis); this class is the
    forward-compat anchor so YAML files written today survive.
    """

    base_id: str = Field(..., min_length=1, max_length=4)
    recipe: str = Field(..., min_length=1)
    data: Path | None = None
    partition_by: str = Field(..., min_length=1)             # e.g. "tags.genotype"
    caption_template: str = "{partition_value}"


# ─────────────────────────── figure spec ────────────────────────────────


class FigureSpec(BaseModel):
    """Top-level spec for a single multi-panel figure."""

    figure_id: str = Field(..., min_length=1)
    title: str = ""
    caption: str = ""
    output_path: Path = Path("figures/figure_unnamed.pdf")

    layout: Layout = Field(...)
    panels: list[PanelSpec | PartitionedPanelSpec] = Field(..., min_length=1)

    # Modality name; recipes inside the figure inherit this aesthetic
    # unless they override it locally via ``PanelSpec.aesthetic_overrides``.
    shared_aesthetic: str | None = None

    # Style hint for the A/B/C overlay; the engine maps named styles to
    # concrete (fontsize, fontweight, position) tuples.
    panel_label_style: str = "upper_left_bold"

    figsize: tuple[float, float] = (8.5, 5.5)               # inches
    dpi: int = 200


__all__ = [
    "FigureSpec",
    "FreeformLayout",
    "GridLayout",
    "GridspecLayout",
    "Layout",
    "PanelSpec",
    "PartitionedPanelSpec",
]
