"""Visual DNA for `redox_imaging` recipes.

Conventions:
  - `redox_bistable` palette for reduced/oxidized/intermediate state colors.
  - Diverging `RdBu_r` colormap for ratios anchored at redox-neutral (= 1).
  - Bistability emphasis with vertical / shaded regions between stable branches.
  - Paracrine-length labeled with μm in callouts.
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="redox_imaging",
    primary_palette="redox_bistable",
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
    required_scale_bars=True,
    label_vocabulary={
        "reduced": "reduced",
        "oxidized": "oxidized",
        "intermediate": "intermediate",
    },
    color_anchor=1.0,                 # ratio neutral
    spine_color="#333333",
)
