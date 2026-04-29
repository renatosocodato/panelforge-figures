"""Omics differential expression figures — volcanos, GSEA, heatmaps, overlap, meta-analysis."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="omics_differential",
    description=(
        "Volcano plots with repelled top-N labels and pathway-grouped "
        "proteome variants, MA plots with lowess, annotated cluster "
        "heatmaps and module-level activity heatmaps, GSEA running-"
        "enrichment curves, ORA dotplots by ontology, UpSet bar + "
        "Euler area-proportional set comparisons, differential rank "
        "ladders and rank-product meta-analysis ladders, pathway-flux "
        "bubbles, effect-size vs significance scatters, replicate-"
        "concordance scatters with agreement bands, raw-vs-shrunken "
        "effect-size diagnostics, multi-contrast volcano grids."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    annotated_cluster_heatmap,
    contrast_overlap_euler,
    differential_rank_ladder,
    effect_size_replicate_concordance,
    effect_size_vs_significance,
    gge_branch_selectivity_permutation_bar,
    gsea_running_enrichment,
    ma_plot_with_lowess,
    module_concordance_signed_heatmap,
    multi_contrast_volcano_grid,
    ora_dotplot_by_ontology,
    pathway_flux_bubble,
    pathway_module_activity_heatmap,
    pathway_module_activity_with_sign_concordance,
    pathway_space_bridge_summary_heatmap,
    pathway_space_triangulation_heatmap,
    proteome_phosphoproteome_pathway_scatter,
    proteome_volcano_labeled_pathways,
    rank_product_meta_analysis,
    shrinkage_estimate_scatter,
    upset_set_comparisons,
    volcano_labeled_repelled,
)

__all__ = [
    "AESTHETIC",
    "annotated_cluster_heatmap",
    "contrast_overlap_euler",
    "differential_rank_ladder",
    "effect_size_replicate_concordance",
    "effect_size_vs_significance",
    "gge_branch_selectivity_permutation_bar",
    "gsea_running_enrichment",
    "ma_plot_with_lowess",
    "module_concordance_signed_heatmap",
    "multi_contrast_volcano_grid",
    "ora_dotplot_by_ontology",
    "pathway_flux_bubble",
    "pathway_module_activity_heatmap",
    "pathway_module_activity_with_sign_concordance",
    "pathway_space_bridge_summary_heatmap",
    "pathway_space_triangulation_heatmap",
    "proteome_phosphoproteome_pathway_scatter",
    "proteome_volcano_labeled_pathways",
    "rank_product_meta_analysis",
    "shrinkage_estimate_scatter",
    "upset_set_comparisons",
    "volcano_labeled_repelled",
]
