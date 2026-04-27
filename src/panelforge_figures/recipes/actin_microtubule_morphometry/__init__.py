"""Actin / microtubule morphometry — distributions, topology, spatial, thumbnails, dim-reduction, coloc."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="actin_microtubule_morphometry",
    description=(
        "Per-cell morphometric distributions (raincloud / split-violin / "
        "bivariate shape scatter / sex × genotype strata), skeleton and "
        "network topology (branch angles, ternary simplex, persistence by "
        "segment, complexity radar, branching sunburst), spatial and "
        "kinematic (edge-velocity autocorrelation / kymograph, "
        "mitochondrial alignment, actin × MT quiver, multi-cell polarity "
        "vector field), per-cell thumbnail grids / exemplar mosaics / "
        "Airyscan raw+segmentation panels, dimensionality reduction of "
        "shape space (PCA morphospace, UMAP, morphospace trajectories, "
        "SPLOM), and colocalization / intensity / component-ratio panels "
        "(spatial ratio maps, radial profiles, tip-vs-shaft enrichment, "
        "coloc × morphology correlation matrices, condition × coefficient "
        "coloc matrices)."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    actin_microtubule_crosstalk_quiver,
    actin_mt_ratio_spatial_map,
    airyscan_segmentation_mosaic,
    airyscan_to_zone_territory_triptych,
    branch_angle_distribution,
    branch_point_count_raincloud,
    branch_point_density_map,
    branching_topology_sunburst,
    cell_body_area_distribution,
    colocalization_coefficient_matrix,
    colocalization_raincloud_per_metric,
    colocalization_vs_morphology_correlation,
    condition_average_cell_composite,
    cortical_thickness_by_region,
    cytoskeleton_polarity_vectorfield,
    edge_velocity_spatial_correlation,
    exemplar_extremes_panel,
    filament_orientation_histogram,
    intensity_radial_profile,
    mitochondrial_axis_alignment,
    morphospace_trajectory_by_time,
    pca_silhouette_glyph_morphospace,
    per_cell_thumbnail_grid_with_metrics,
    persistence_length_by_segment,
    persistence_length_fit,
    process_end_count_violin,
    process_length_distribution_by_sex,
    protrusion_length_velocity_joint,
    protrusion_retraction_kymograph,
    sex_stratified_cvvelocity,
    shape_descriptor_scatter_matrix,
    shape_pca_morphospace,
    shape_umap_by_condition,
    skeleton_complexity_radar,
    skeleton_overlay_kymograph,
    sphericity_vs_elongation_scatter,
    territory_contact_network_overlay,
    tip_enrichment_vs_shaft_scatter,
    topology_ternary_simplex,
    zone_fraction_alluvial_sankey,
)

__all__ = [
    "AESTHETIC",
    "actin_microtubule_crosstalk_quiver",
    "actin_mt_ratio_spatial_map",
    "airyscan_segmentation_mosaic",
    "airyscan_to_zone_territory_triptych",
    "branch_angle_distribution",
    "branch_point_count_raincloud",
    "branch_point_density_map",
    "branching_topology_sunburst",
    "cell_body_area_distribution",
    "colocalization_coefficient_matrix",
    "colocalization_raincloud_per_metric",
    "colocalization_vs_morphology_correlation",
    "condition_average_cell_composite",
    "cortical_thickness_by_region",
    "cytoskeleton_polarity_vectorfield",
    "edge_velocity_spatial_correlation",
    "exemplar_extremes_panel",
    "filament_orientation_histogram",
    "intensity_radial_profile",
    "mitochondrial_axis_alignment",
    "morphospace_trajectory_by_time",
    "pca_silhouette_glyph_morphospace",
    "per_cell_thumbnail_grid_with_metrics",
    "persistence_length_by_segment",
    "persistence_length_fit",
    "process_end_count_violin",
    "process_length_distribution_by_sex",
    "protrusion_length_velocity_joint",
    "protrusion_retraction_kymograph",
    "sex_stratified_cvvelocity",
    "shape_descriptor_scatter_matrix",
    "shape_pca_morphospace",
    "shape_umap_by_condition",
    "skeleton_complexity_radar",
    "skeleton_overlay_kymograph",
    "sphericity_vs_elongation_scatter",
    "territory_contact_network_overlay",
    "tip_enrichment_vs_shaft_scatter",
    "topology_ternary_simplex",
    "zone_fraction_alluvial_sankey",
]
