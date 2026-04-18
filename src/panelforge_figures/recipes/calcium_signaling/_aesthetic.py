"""Visual DNA for `calcium_signaling` recipes.

Conventions:
  - Population raster below, mean-rate curve above.
  - GCaMP traces stacked vertically with a shared time axis.
  - Accent green for activity (GCaMP-evocative); warm red for stim markers.
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="calcium_signaling",
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
    label_vocabulary={"event": "event", "rate": "rate"},
    spine_color="#333333",
)
