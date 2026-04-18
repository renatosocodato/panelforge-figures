"""Visual DNA for `dose_response_pharmacology` recipes.

Conventions:
  - `mechanism_class` palette since compounds often cluster by mechanism
    (signaling vs metabolic, etc.).
  - Log-x axis is standard for dose-response — recipes set xscale="log"
    where appropriate.
  - Thin crisp fit curves, small scatter markers.
  - No strokes, no bold annotations.
"""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="dose_response_pharmacology",
    primary_palette="mechanism_class",
    continuous_cmap="viridis",
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
    label_vocabulary={
        "IC50": r"$\mathrm{IC}_{50}$",
        "EC50": r"$\mathrm{EC}_{50}$",
        "pA2": r"$\mathrm{pA}_2$",
    },
    spine_color="#333333",
)
