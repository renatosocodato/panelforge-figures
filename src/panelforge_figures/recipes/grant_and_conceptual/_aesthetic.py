"""Visual DNA for `grant_and_conceptual` recipes.

Conventions:
  - Primary palette is `mechanism_class` (signaling / metabolic / cytoskeletal /
    other). Conceptual triptychs may also call `journal_neutral` for muted
    accents.
  - Annotation style uses a slightly thicker halo (3.0) to keep labels legible
    on dense block diagrams.
  - No scale bars, no ratio colormap, no insets (most panels are block art).
  - Continuous colormap is `cividis` (safer for color-vision and for the
    muted venues that tend to accompany grant figures).
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="grant_and_conceptual",
    primary_palette="mechanism_class",
    continuous_cmap="cividis",
    density_cmap="magma",
    ratio_cmap=None,
    annotation_style=AnnotationStyle(
        halo_width=3.0,
        label_fontsize=8.2,
        label_fontweight="normal",
        callout_pad=0.32,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={
        "aim_1": "Aim 1",
        "aim_2": "Aim 2",
        "aim_3": "Aim 3",
        "wp_1": "WP 1",
        "wp_2": "WP 2",
        "wp_3": "WP 3",
        "wp_4": "WP 4",
        "wp_5": "WP 5",
    },
    spine_color="#333333",
)
