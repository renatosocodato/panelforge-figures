"""Redox imaging figures — calibration, bistability, paracrine coupling, noise diagnostics."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="redox_imaging",
    description=(
        "roGFP2 calibration titrations, bistability hysteresis loops, "
        "single-cell redox-ratio distributions, condition-level "
        "bimodality statistics (BC, kurtosis, dip), time-above-"
        "threshold duration distributions, paracrine coupling-length "
        "maps and 1-D kernel fits, bimodality grids, ratio "
        "trajectories with phase annotations, redox-state transition "
        "diagrams and spatial switching-rate maps, multiplicative / "
        "additive Langevin noise model comparisons, drift-diffusion "
        "decompositions, temporal autocorrelation decay by state."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    bimodality_coefficient_grid,
    bimodality_kurtosis_vs_conditions,
    bistability_hysteresis_loop,
    drift_diffusion_decomposition,
    multiplicative_noise_diagnostic,
    multiplicative_vs_additive_noise_diagnostic,
    paracrine_coupling_length_map,
    paracrine_kernel_fit,
    ratio_autocorrelation_decay,
    ratio_trajectory_with_phase_annotation,
    redox_state_switching_frequency_map,
    redox_state_transition_diagram,
    roGFP2_ratio_vs_disulfide_titration,
    single_cell_ratio_distribution,
    time_above_threshold_distribution,
)

__all__ = [
    "AESTHETIC",
    "bimodality_coefficient_grid",
    "bimodality_kurtosis_vs_conditions",
    "bistability_hysteresis_loop",
    "drift_diffusion_decomposition",
    "multiplicative_noise_diagnostic",
    "multiplicative_vs_additive_noise_diagnostic",
    "paracrine_coupling_length_map",
    "paracrine_kernel_fit",
    "ratio_autocorrelation_decay",
    "ratio_trajectory_with_phase_annotation",
    "redox_state_switching_frequency_map",
    "redox_state_transition_diagram",
    "roGFP2_ratio_vs_disulfide_titration",
    "single_cell_ratio_distribution",
    "time_above_threshold_distribution",
]
