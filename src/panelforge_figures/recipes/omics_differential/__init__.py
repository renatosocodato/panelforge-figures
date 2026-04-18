"""Omics differential expression figures — volcanos, GSEA, heatmaps, etc."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="omics_differential",
    description=(
        "Volcano plots with repelled top-N labels, MA plots with lowess, "
        "annotated cluster heatmaps, GSEA running-enrichment curves, "
        "ORA dotplots by ontology, UpSet set-comparisons, differential "
        "rank ladders, pathway-flux bubbles, effect-size vs significance "
        "scatters, multi-contrast volcano grids."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    annotated_cluster_heatmap,
    differential_rank_ladder,
    effect_size_vs_significance,
    gsea_running_enrichment,
    ma_plot_with_lowess,
    multi_contrast_volcano_grid,
    ora_dotplot_by_ontology,
    pathway_flux_bubble,
    upset_set_comparisons,
    volcano_labeled_repelled,
)

__all__ = [
    "AESTHETIC",
    "annotated_cluster_heatmap",
    "differential_rank_ladder",
    "effect_size_vs_significance",
    "gsea_running_enrichment",
    "ma_plot_with_lowess",
    "multi_contrast_volcano_grid",
    "ora_dotplot_by_ontology",
    "pathway_flux_bubble",
    "upset_set_comparisons",
    "volcano_labeled_repelled",
]
