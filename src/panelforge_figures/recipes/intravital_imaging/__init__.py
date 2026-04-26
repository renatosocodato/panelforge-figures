"""Intravital imaging — in vivo cell tracking, z-stacks, vessel dynamics, shape + homing + events."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="intravital_imaging",
    description=(
        "Cell-track trajectories, depth-coded microglia fields, "
        "two-photon MIPs, vessel-diameter kymographs, cell-shape "
        "descriptor violins, migration rose diagrams, time-to-homing "
        "survival, per-cell event rasters, territory-change pre/post "
        "polygons, surveillance-efficiency forests, pairwise cell-cell "
        "contact matrices, laser-injury radial responses, multi-channel "
        "RGB overlays, ensemble MSD curves with α-slopes, instantaneous-"
        "speed split violins."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    cell_cell_contact_frequency_matrix,
    cell_shape_descriptors_by_state,
    cell_track_trajectory_field,
    depth_projected_microglia_field,
    dwell_time_distribution_per_state,
    emission_distribution_per_state,
    hazard_rate_per_state,
    hmm_vs_hsmm_model_comparison,
    laser_injury_response_radial,
    migration_rose_diagram,
    msd_curve_by_state,
    multi_channel_intravital_overlay,
    process_event_timeline,
    sojourn_survival_per_state,
    surveillance_efficiency_metric,
    territory_change_pre_post,
    time_to_homing_survival,
    two_photon_depth_projection,
    velocity_distribution_by_state,
    vessel_diameter_kymograph,
)

__all__ = [
    "AESTHETIC",
    "cell_cell_contact_frequency_matrix",
    "cell_shape_descriptors_by_state",
    "cell_track_trajectory_field",
    "depth_projected_microglia_field",
    "dwell_time_distribution_per_state",
    "emission_distribution_per_state",
    "hazard_rate_per_state",
    "hmm_vs_hsmm_model_comparison",
    "laser_injury_response_radial",
    "migration_rose_diagram",
    "msd_curve_by_state",
    "multi_channel_intravital_overlay",
    "process_event_timeline",
    "sojourn_survival_per_state",
    "surveillance_efficiency_metric",
    "territory_change_pre_post",
    "time_to_homing_survival",
    "two_photon_depth_projection",
    "velocity_distribution_by_state",
    "vessel_diameter_kymograph",
]
