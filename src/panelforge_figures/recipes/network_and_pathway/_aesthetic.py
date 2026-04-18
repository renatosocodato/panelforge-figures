"""Visual DNA for `network_and_pathway` recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="network_and_pathway",
    primary_palette="mechanism_class",
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
    label_vocabulary={"source": "source", "target": "target"},
    spine_color="#333333",
)
