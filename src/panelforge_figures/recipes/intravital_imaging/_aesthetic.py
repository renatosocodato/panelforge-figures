"""Visual DNA for `intravital_imaging` recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="intravital_imaging",
    primary_palette="microglia_states",
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
        "v": "velocity", "MSD": "MSD", "theta": r"$\theta$",
    },
    spine_color="#333333",
)
