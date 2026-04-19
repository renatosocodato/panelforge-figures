"""Spatial statistics — point-pattern analysis, density, autocorrelation."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="spatial_statistics",
    description=(
        "Ripley's L, pair correlation, nearest-neighbor distributions, "
        "Voronoi territories, 2D KDE heatmaps, and Moran's I vs lag."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    kernel_density_heatmap,
    moran_i_by_lag,
    nearest_neighbor_distance_distribution,
    pair_correlation_function,
    ripley_l_function,
    voronoi_territory_map,
)

__all__ = [
    "AESTHETIC",
    "kernel_density_heatmap",
    "moran_i_by_lag",
    "nearest_neighbor_distance_distribution",
    "pair_correlation_function",
    "ripley_l_function",
    "voronoi_territory_map",
]
