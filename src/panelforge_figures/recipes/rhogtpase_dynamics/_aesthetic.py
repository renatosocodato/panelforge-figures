"""Visual DNA for `rhogtpase_dynamics` recipes.

Conventions (Tyson/Novák-inflected):
  - `home_gate_trap` palette anchors tristable well colors (HOME green,
    GATE amber, TRAP red).
  - Continuous `viridis` for streamplots; `RdBu_r` for signed curvature.
  - Fixed-point convention: filled = stable, hollow = unstable,
    half-filled = saddle; saddle-nodes as red stars.
  - Shaded regime regions (ax.axvspan) for bifurcation diagrams.
  - Nullclines as dashed thin lines in palette[1]/palette[2] colors.
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="rhogtpase_dynamics",
    primary_palette="home_gate_trap",
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
        "HOME": "HOME",
        "GATE": "GATE",
        "TRAP": "TRAP",
        "stable": "stable",
        "unstable": "unstable",
        "saddle": "saddle",
    },
    spine_color="#333333",
)
