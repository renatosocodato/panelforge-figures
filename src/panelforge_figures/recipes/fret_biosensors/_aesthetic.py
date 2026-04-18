"""Visual DNA for `fret_biosensors` recipes.

Conventions:
  - `fret_donor_acceptor` palette (teal donor, amber acceptor, ratio accents).
  - `RdBu_r` ratio colormap anchored at F/F₀ = 1.0.
  - Stimulus annotation bar convention: grey hatched span above data.
  - Mandatory scale bars for field images (μm).
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, InsetConvention, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="fret_biosensors",
    primary_palette="fret_donor_acceptor",
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
    inset_convention=InsetConvention(
        position="upper_right",
        size_frac=(0.25, 0.25),
        pad_frac=0.02,
    ),
    required_scale_bars=True,
    label_vocabulary={
        "donor": "donor",
        "acceptor": "acceptor",
        "ratio": r"F$_\mathrm{A}$/F$_\mathrm{D}$",
        "stim": "stim",
    },
    color_anchor=1.0,                 # ratio-neutral
    spine_color="#333333",
)
