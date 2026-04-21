"""Single-cell embeddings — UMAP, trajectory, PCA, diffusion maps, velocity, signalling."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="single_cell_embeddings",
    description=(
        "UMAP scatters coloured categorically with density contours (per "
        "cluster or per condition), UMAP coloured continuously by "
        "expression, UMAP spotlighting a rare population, pseudotime "
        "trajectory arrows and branching-trajectory force-directed "
        "layouts, per-cluster expression dotplots and marker heatmaps, "
        "ligand-receptor signalling dotplots, PCA biplots with loadings, "
        "diffusion maps, neighbourhood-composition stacks by condition "
        "and per-sample, gene expression along pseudotime, RNA-velocity "
        "quiver fields on UMAP."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    cluster_proportion_stacked_by_sample,
    diffusion_map_2d,
    expression_dotplot_by_cluster,
    neighborhood_composition_stacked,
    pca_biplot_with_loadings,
    per_cluster_marker_heatmap,
    pseudotime_gene_expression_trajectory,
    rare_population_highlighted_umap,
    receptor_ligand_signaling_dotplot,
    rnavelocity_arrow_field,
    trajectory_branching_force_directed,
    trajectory_pseudotime_arrow,
    umap_categorical_with_density_contours,
    umap_continuous_expression,
    umap_density_contour_overlay,
)

__all__ = [
    "AESTHETIC",
    "cluster_proportion_stacked_by_sample",
    "diffusion_map_2d",
    "expression_dotplot_by_cluster",
    "neighborhood_composition_stacked",
    "pca_biplot_with_loadings",
    "per_cluster_marker_heatmap",
    "pseudotime_gene_expression_trajectory",
    "rare_population_highlighted_umap",
    "receptor_ligand_signaling_dotplot",
    "rnavelocity_arrow_field",
    "trajectory_branching_force_directed",
    "trajectory_pseudotime_arrow",
    "umap_categorical_with_density_contours",
    "umap_continuous_expression",
    "umap_density_contour_overlay",
]
