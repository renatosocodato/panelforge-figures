"""Single-cell embeddings — UMAP, trajectory, PCA, diffusion maps."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="single_cell_embeddings",
    description=(
        "UMAP scatters colored categorically with density contours or "
        "continuously by expression, pseudotime trajectory arrows, per-cluster "
        "expression dotplots, PCA biplots with loadings, diffusion maps, "
        "neighborhood-composition stacks."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    diffusion_map_2d,
    expression_dotplot_by_cluster,
    neighborhood_composition_stacked,
    pca_biplot_with_loadings,
    trajectory_pseudotime_arrow,
    umap_categorical_with_density_contours,
    umap_continuous_expression,
)

__all__ = [
    "AESTHETIC",
    "diffusion_map_2d",
    "expression_dotplot_by_cluster",
    "neighborhood_composition_stacked",
    "pca_biplot_with_loadings",
    "trajectory_pseudotime_arrow",
    "umap_categorical_with_density_contours",
    "umap_continuous_expression",
]
