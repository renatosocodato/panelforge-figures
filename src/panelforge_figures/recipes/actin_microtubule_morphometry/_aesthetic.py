"""Visual DNA for `actin_microtubule_morphometry` recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="actin_microtubule_morphometry",
    primary_palette="cytoskeleton_components",
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
    required_scale_bars=True,
    label_vocabulary={
        "Lp": r"$L_p$", "theta": r"$\theta$",
        "actin": "F-actin", "mt": "microtubule",
    },
    spine_color="#333333",
)
