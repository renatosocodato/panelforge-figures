"""Spatial statistics — point-pattern analysis, density, autocorrelation."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="spatial_statistics",
    description=(
        "Ripley's L, pair correlation, nearest-neighbour distributions, "
        "Voronoi territories, 2D KDE heatmaps, Moran's I vs lag, Clark-"
        "Evans aggregation index, F function empty-space, spatial "
        "covariogram, LISA cluster maps, bivariate pair correlation, "
        "Voronoi area distributions, co-occurrence significance "
        "matrices, quadrat χ² tests, and spatial permutation null "
        "distributions."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    bivariate_pair_correlation,
    clark_evans_aggregation_bar,
    co_occurrence_significance_matrix,
    f_function_empty_space,
    kernel_density_heatmap,
    lisa_cluster_map,
    moran_i_by_lag,
    nearest_neighbor_distance_distribution,
    pair_correlation_function,
    quadrat_count_chisq,
    ripley_l_function,
    spatial_covariogram,
    spatial_permutation_null_distribution,
    voronoi_area_distribution,
    voronoi_territory_map,
)

__all__ = [
    "AESTHETIC",
    "bivariate_pair_correlation",
    "clark_evans_aggregation_bar",
    "co_occurrence_significance_matrix",
    "f_function_empty_space",
    "kernel_density_heatmap",
    "lisa_cluster_map",
    "moran_i_by_lag",
    "nearest_neighbor_distance_distribution",
    "pair_correlation_function",
    "quadrat_count_chisq",
    "ripley_l_function",
    "spatial_covariogram",
    "spatial_permutation_null_distribution",
    "voronoi_area_distribution",
    "voronoi_territory_map",
]
