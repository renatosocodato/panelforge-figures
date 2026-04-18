"""Visual DNA for `gillespie_stochastic` recipes.

Conventions:
  - Stepwise traces for discrete-event trajectories (drawstyle="steps-post").
  - State-shaded timelines using home_gate_trap or microglia_states palette.
  - First-passage-time markers as red stars; mean-ensemble curve as bold line.
  - Log-x for waiting-time ECDFs / dwell violins.
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="gillespie_stochastic",
    primary_palette="home_gate_trap",
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
    label_vocabulary={"fpt": "first passage", "state": "state"},
    spine_color="#333333",
)
