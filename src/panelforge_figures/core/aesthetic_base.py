"""Abstract contract that every modality's `_aesthetic.py` must satisfy."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnnotationStyle(BaseModel):
    """Per-modality annotation tuning (label fontsizes, halo, callout box)."""

    halo_width: float = 2.8
    label_fontsize: float = 8.0
    label_fontweight: str = "normal"
    callout_pad: float = 0.28
    callout_accent: str = "#333333"


class InsetConvention(BaseModel):
    """Position and size of a conventional inset for the modality."""

    position: str = "upper_right"           # upper_left | upper_right | lower_left | lower_right
    size_frac: tuple[float, float] = (0.25, 0.25)
    pad_frac: float = 0.02


class ModalityAesthetic(BaseModel):
    """The visual DNA of a modality — every recipe in it honors this object.

    Instances live in each modality's `_aesthetic.py` as the module-level name
    `AESTHETIC`. CI's aesthetic-compliance test verifies each recipe imports
    from its modality's `_aesthetic` module.
    """

    modality_name: str
    primary_palette: str
    ratio_cmap: str | None = None
    continuous_cmap: str = "viridis"
    density_cmap: str = "magma"
    annotation_style: AnnotationStyle = Field(default_factory=AnnotationStyle)
    inset_convention: InsetConvention | None = None
    required_scale_bars: bool = False
    label_vocabulary: dict[str, str] = Field(default_factory=dict)
    color_anchor: float | None = None         # e.g. 1.0 for FRET ratio-neutral
    spine_color: str = "#333333"

    def apply_to_ax(self, ax) -> None:
        """Apply modality-level axis tweaks. Recipes call this on every ax."""
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(self.spine_color)
            ax.spines[side].set_linewidth(0.7)
        ax.tick_params(colors=self.spine_color, width=0.7, length=3.0)

    def apply_to_fig(self, fig) -> None:
        """Apply modality-level figure tweaks (background color, etc.)."""
        fig.patch.set_facecolor("white")

    def vocab(self, key: str) -> str:
        """Look up a modality-specific label convention (e.g. sex_f → ♀)."""
        return self.label_vocabulary.get(key, key)

    def ratio_colormap(self) -> str:
        """Return the ratio colormap, raising if the modality doesn't use one."""
        if self.ratio_cmap is None:
            raise ValueError(f"{self.modality_name} has no ratio colormap")
        return self.ratio_cmap

    def dump(self) -> dict[str, Any]:
        return self.model_dump()
