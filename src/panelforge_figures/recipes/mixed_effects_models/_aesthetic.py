"""Visual DNA for `mixed_effects_models` recipes.

Conventions:
  - `sex_x_genotype` categorical palette so sex × genotype panels are
    immediately legible; fall back to `okabe_ito` for generic term forests.
  - No scale bars, no ratio cmap; `viridis` for continuous densities.
  - Annotations: small, regular-weight labels; CIs end with right-side
    numeric labels via primitives.right_of_ci_label.
  - No inset convention — these figures read left-to-right.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="mixed_effects_models",
    primary_palette="sex_x_genotype",
    continuous_cmap="viridis",
    density_cmap="magma",
    ratio_cmap=None,
    annotation_style=AnnotationStyle(
        halo_width=0.0,
        label_fontsize=7.4,
        label_fontweight="normal",
        callout_pad=0.28,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={"interaction": "×", "fixed": "fixed", "random": "random"},
    spine_color="#333333",
)
