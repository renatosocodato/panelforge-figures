"""Visual DNA for `biophysics_scaling` recipes.

Conventions:
  - `okabe_ito` categorical for multi-regime / multi-condition overlays.
  - Continuous cividis for heat-map style densities.
  - Dashed reference slopes in grey, data in accent color.
  - Slope box: compact pill annotating the fitted exponent.
  - No strokes, no bold.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="biophysics_scaling",
    primary_palette="okabe_ito",
    continuous_cmap="cividis",
    density_cmap="magma",
    ratio_cmap="RdBu_r",
    annotation_style=AnnotationStyle(
        halo_width=0.0,
        label_fontsize=7.2,
        label_fontweight="normal",
        callout_pad=0.28,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={"slope": r"$\alpha$", "exponent": r"$\beta$"},
    spine_color="#333333",
)
