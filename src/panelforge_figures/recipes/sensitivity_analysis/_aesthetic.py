"""Visual DNA for `sensitivity_analysis` recipes.

Conventions:
  - `viridis` as the monotonic color-gradient for indices (S1, ST, μ*, etc.).
  - Okabe-Ito for categorical overlays (groups of parameters, confidence bands).
  - Numeric labels: smart_fmt (3dp below 0.01, 2dp otherwise), right-of-bar.
  - Callout boxes for top-driver summaries (white, round, thin accent).
  - Horizontal bars with a colorbar-style gradient, reflecting index value.
  - No scale bars, no insets.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="sensitivity_analysis",
    primary_palette="okabe_ito",
    continuous_cmap="viridis",
    density_cmap="magma",
    ratio_cmap="RdBu_r",
    annotation_style=AnnotationStyle(
        halo_width=2.6,
        label_fontsize=7.6,
        label_fontweight="normal",
        callout_pad=0.30,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={"S1": r"$S_1$", "ST": r"$S_T$", "mu_star": r"$\mu^*$"},
    color_anchor=None,
    spine_color="#333333",
)
