"""Visual DNA for `single_cell_embeddings` recipes.

Conventions:
  - `microglia_states` palette for categorical cluster coloring.
  - `viridis` for pseudotime / continuous expression.
  - Axis spines off for UMAP / embeddings (no ticks).
  - Alpha-by-density scatter for large cell counts.
  - No strokes, no bold.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="single_cell_embeddings",
    primary_palette="microglia_states",
    continuous_cmap="viridis",
    density_cmap="magma",
    ratio_cmap=None,
    annotation_style=AnnotationStyle(
        halo_width=0.0,
        label_fontsize=7.0,
        label_fontweight="normal",
        callout_pad=0.28,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={"umap1": "UMAP1", "umap2": "UMAP2", "pseudotime": "pseudotime"},
    spine_color="#BBBBBB",
)
