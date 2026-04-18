"""Redox imaging figures — bistability, paracrine coupling, bimodality diagnostics."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="redox_imaging",
    description=(
        "Bistability hysteresis loops, single-cell redox-ratio distributions, "
        "paracrine coupling-length maps, bimodality-coefficient grids, "
        "ratio trajectories with phase annotations, redox-state transition "
        "diagrams, multiplicative-noise diagnostics, drift-diffusion "
        "decompositions."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    bimodality_coefficient_grid,
    bistability_hysteresis_loop,
    drift_diffusion_decomposition,
    multiplicative_noise_diagnostic,
    paracrine_coupling_length_map,
    ratio_trajectory_with_phase_annotation,
    redox_state_transition_diagram,
    single_cell_ratio_distribution,
)

__all__ = [
    "AESTHETIC",
    "bimodality_coefficient_grid",
    "bistability_hysteresis_loop",
    "drift_diffusion_decomposition",
    "multiplicative_noise_diagnostic",
    "paracrine_coupling_length_map",
    "ratio_trajectory_with_phase_annotation",
    "redox_state_transition_diagram",
    "single_cell_ratio_distribution",
]
