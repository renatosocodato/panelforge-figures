"""Actin / microtubule morphometry — filament geometry, branch density, persistence, protrusions."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="actin_microtubule_morphometry",
    description=(
        "Filament orientation roses, branch-point density maps, "
        "persistence-length fits, protrusion kinematic scatter, "
        "cortical-thickness ridges, and spatiotemporal skeleton "
        "kymographs."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    branch_point_density_map,
    cortical_thickness_by_region,
    filament_orientation_histogram,
    persistence_length_fit,
    protrusion_length_velocity_joint,
    skeleton_overlay_kymograph,
)

__all__ = [
    "AESTHETIC",
    "branch_point_density_map",
    "cortical_thickness_by_region",
    "filament_orientation_histogram",
    "persistence_length_fit",
    "protrusion_length_velocity_joint",
    "skeleton_overlay_kymograph",
]
