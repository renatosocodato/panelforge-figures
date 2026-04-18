"""Visual DNA for `meta_and_diagnostic` recipes.

Conventions:
  - Journal-neutral palette — these are interpretive figures meant to be read
    plainly.
  - Low-saturation continuous cmap (`cividis`) for radars and pattern matrices.
  - Annotation style: small, un-bold labels; the messaging is in axis titles.
  - No scale bars. No insets.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="meta_and_diagnostic",
    primary_palette="journal_neutral",
    continuous_cmap="cividis",
    density_cmap="magma",
    ratio_cmap=None,
    annotation_style=AnnotationStyle(
        halo_width=2.4,
        label_fontsize=7.6,
        label_fontweight="normal",
        callout_pad=0.26,
        callout_accent="#555555",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={"adequate": "adequate", "inadequate": "inadequate"},
    spine_color="#333333",
)
