"""CryoEM and structural biology — resolution, orientation, 2D classes, dihedrals."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="cryoem_and_structure",
    description=(
        "Gold-standard FSC curves, angular distributions, local-"
        "resolution slices, 2D class-average montages, Ramachandran "
        "plots, per-residue B-factor profiles, per-chain B-factor "
        "ridges, ensemble RMSF, docking score-vs-RMSD funnels, "
        "residue contact maps with secondary-structure tracks, surface "
        "electrostatic-potential projections, BSA-vs-affinity "
        "scatter, normal-mode variance ladders, H-bond network "
        "diagrams, and motion-correction shift quivers."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    angular_distribution_hist,
    b_factor_distribution_by_chain,
    bfactor_vs_residue,
    conformational_ensemble_rmsf,
    contact_map_with_secondary_structure,
    docking_pose_score_vs_rmsd,
    domain_motion_decomposition,
    fsc_resolution_curve,
    hydrogen_bond_network_diagram,
    interface_area_vs_affinity,
    local_resolution_surface,
    motion_correction_shift_vector,
    particle_2d_class_montage,
    ramachandran_plot,
    surface_electrostatics_colormap,
)

__all__ = [
    "AESTHETIC",
    "angular_distribution_hist",
    "b_factor_distribution_by_chain",
    "bfactor_vs_residue",
    "conformational_ensemble_rmsf",
    "contact_map_with_secondary_structure",
    "docking_pose_score_vs_rmsd",
    "domain_motion_decomposition",
    "fsc_resolution_curve",
    "hydrogen_bond_network_diagram",
    "interface_area_vs_affinity",
    "local_resolution_surface",
    "motion_correction_shift_vector",
    "particle_2d_class_montage",
    "ramachandran_plot",
    "surface_electrostatics_colormap",
]
