"""Visual DNA for `spatial_statistics` recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="spatial_statistics",
    primary_palette="okabe_ito",
    continuous_cmap="magma",
    density_cmap="inferno",
    ratio_cmap="RdBu_r",
    annotation_style=AnnotationStyle(
        halo_width=0.0,
        label_fontsize=7.0,
        label_fontweight="normal",
        callout_pad=0.28,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=True,
    label_vocabulary={
        "L": "$L(r)$", "g": "$g(r)$", "I": "Moran's $I$",
        "nn": "nearest-neighbor", "csr": "CSR",
    },
    spine_color="#333333",
)
