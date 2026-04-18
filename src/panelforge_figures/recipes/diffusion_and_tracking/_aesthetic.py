"""Visual DNA for `diffusion_and_tracking` recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="diffusion_and_tracking",
    primary_palette="okabe_ito",
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
    label_vocabulary={"msd": "MSD", "tau": r"$\tau$", "alpha": r"$\alpha$"},
    spine_color="#333333",
)
