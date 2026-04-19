"""Intravital imaging — in vivo cell tracking, z-stacks, vessel dynamics, shape + homing."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="intravital_imaging",
    description=(
        "Cell track trajectories, two-photon depth-coded projections, "
        "vessel-diameter kymographs, cell-shape descriptor violins, "
        "migration rose diagrams, and time-to-homing survival curves."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    cell_shape_descriptors_by_state,
    cell_track_trajectory_field,
    migration_rose_diagram,
    time_to_homing_survival,
    two_photon_depth_projection,
    vessel_diameter_kymograph,
)

__all__ = [
    "AESTHETIC",
    "cell_shape_descriptors_by_state",
    "cell_track_trajectory_field",
    "migration_rose_diagram",
    "time_to_homing_survival",
    "two_photon_depth_projection",
    "vessel_diameter_kymograph",
]
