"""CryoEM and structural biology — resolution, orientation, 2D classes, dihedrals."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="cryoem_and_structure",
    description=(
        "Gold-standard FSC curves, angular distributions, local-resolution "
        "slices, 2D class-average montages, Ramachandran plots, and "
        "per-residue B-factor profiles."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    angular_distribution_hist,
    bfactor_vs_residue,
    fsc_resolution_curve,
    local_resolution_surface,
    particle_2d_class_montage,
    ramachandran_plot,
)

__all__ = [
    "AESTHETIC",
    "angular_distribution_hist",
    "bfactor_vs_residue",
    "fsc_resolution_curve",
    "local_resolution_surface",
    "particle_2d_class_montage",
    "ramachandran_plot",
]
