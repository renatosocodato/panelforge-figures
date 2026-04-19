"""Actin / microtubule morphometry — distributions, topology, spatial, thumbnails, dim-reduction, coloc."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="actin_microtubule_morphometry",
    description=(
        "Per-cell morphometric distributions (raincloud / split-violin / "
        "bivariate shape scatter), skeleton and network topology (branch "
        "angles, ternary simplex, persistence), spatial and kinematic "
        "(edge-velocity autocorrelation, mitochondrial alignment), "
        "per-cell thumbnail grids and exemplar mosaics, dimensionality "
        "reduction of shape space (UMAP, morphospace trajectories, SPLOM), "
        "and colocalization / intensity / component-ratio panels (spatial "
        "ratio maps, radial profiles, tip-vs-shaft enrichment, coloc × "
        "morphology correlation matrices)."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    actin_mt_ratio_spatial_map,
    branch_angle_distribution,
    branch_point_count_raincloud,
    branch_point_density_map,
    cell_body_area_distribution,
    colocalization_vs_morphology_correlation,
    condition_average_cell_composite,
    cortical_thickness_by_region,
    edge_velocity_spatial_correlation,
    exemplar_extremes_panel,
    filament_orientation_histogram,
    intensity_radial_profile,
    mitochondrial_axis_alignment,
    morphospace_trajectory_by_time,
    per_cell_thumbnail_grid_with_metrics,
    persistence_length_fit,
    process_end_count_violin,
    protrusion_length_velocity_joint,
    shape_descriptor_scatter_matrix,
    shape_umap_by_condition,
    skeleton_overlay_kymograph,
    sphericity_vs_elongation_scatter,
    tip_enrichment_vs_shaft_scatter,
    topology_ternary_simplex,
)

__all__ = [
    "AESTHETIC",
    "actin_mt_ratio_spatial_map",
    "branch_angle_distribution",
    "branch_point_count_raincloud",
    "branch_point_density_map",
    "cell_body_area_distribution",
    "colocalization_vs_morphology_correlation",
    "condition_average_cell_composite",
    "cortical_thickness_by_region",
    "edge_velocity_spatial_correlation",
    "exemplar_extremes_panel",
    "filament_orientation_histogram",
    "intensity_radial_profile",
    "mitochondrial_axis_alignment",
    "morphospace_trajectory_by_time",
    "per_cell_thumbnail_grid_with_metrics",
    "persistence_length_fit",
    "process_end_count_violin",
    "protrusion_length_velocity_joint",
    "shape_descriptor_scatter_matrix",
    "shape_umap_by_condition",
    "skeleton_overlay_kymograph",
    "sphericity_vs_elongation_scatter",
    "tip_enrichment_vs_shaft_scatter",
    "topology_ternary_simplex",
]
