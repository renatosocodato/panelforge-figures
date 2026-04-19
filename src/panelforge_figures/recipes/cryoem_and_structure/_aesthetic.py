"""Visual DNA for `cryoem_and_structure` recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="cryoem_and_structure",
    primary_palette="okabe_ito",
    continuous_cmap="viridis",
    density_cmap="cividis",
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
        "fsc": "FSC", "res": "resolution",
        "phi": r"$\varphi$", "psi": r"$\psi$",
    },
    spine_color="#333333",
)
