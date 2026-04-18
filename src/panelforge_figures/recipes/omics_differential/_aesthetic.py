"""Visual DNA for `omics_differential` recipes.

Conventions:
  - Volcano / MA grammar: alpha-by-local-density scatter, threshold lines.
  - Top-N labels placed by simple repulsion; bold never; crisp dark text.
  - Divergent `RdBu_r` for log2FC-centered heatmaps; `viridis` for density.
  - Neutral `journal_neutral` categorical palette for condition accents.
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="omics_differential",
    primary_palette="journal_neutral",
    continuous_cmap="viridis",
    density_cmap="magma",
    ratio_cmap="RdBu_r",
    annotation_style=AnnotationStyle(
        halo_width=0.0,
        label_fontsize=7.0,
        label_fontweight="normal",
        callout_pad=0.28,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={
        "log2fc": r"$\log_2$FC",
        "padj": r"$-\log_{10}$ p$_{adj}$",
        "nes": "NES",
    },
    spine_color="#333333",
)
