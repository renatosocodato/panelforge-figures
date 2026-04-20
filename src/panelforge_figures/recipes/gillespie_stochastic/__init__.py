"""Gillespie stochastic simulation figures — trajectories, dwell times, spectra, identifiability."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="gillespie_stochastic",
    description=(
        "Trajectory fans with first-passage-time markers, log-scale "
        "dwell-time violins, waiting-time ECDFs with analytical fits, "
        "rate vs control-parameter curves, state occupancy rasters, "
        "ensemble mean-variance tubes, noise power spectra + trajectory "
        "autocorrelation, master-equation steady-state overlap with "
        "sampled distributions, tau-leaping vs exact comparisons, mean "
        "first-passage-time matrices, Fisher-information matrices for "
        "parameter identifiability, transcription burst-size "
        "distributions, extinction-probability curves, stochastic-"
        "resonance SNR signatures."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    autocorrelation_of_trajectories,
    burst_size_distribution,
    dwell_time_log_violin,
    ensemble_mean_variance_tube,
    extinction_probability_vs_parameter,
    fisher_information_parameter_estimation,
    master_equation_steady_state,
    mean_first_passage_time_matrix,
    noise_power_spectrum,
    rate_vs_control_parameter,
    state_occupancy_raster,
    stochastic_resonance_signature,
    tau_leaping_comparison,
    trajectory_fan_with_fpt,
    waiting_time_ecdf_fitted,
)

__all__ = [
    "AESTHETIC",
    "autocorrelation_of_trajectories",
    "burst_size_distribution",
    "dwell_time_log_violin",
    "ensemble_mean_variance_tube",
    "extinction_probability_vs_parameter",
    "fisher_information_parameter_estimation",
    "master_equation_steady_state",
    "mean_first_passage_time_matrix",
    "noise_power_spectrum",
    "rate_vs_control_parameter",
    "state_occupancy_raster",
    "stochastic_resonance_signature",
    "tau_leaping_comparison",
    "trajectory_fan_with_fpt",
    "waiting_time_ecdf_fitted",
]
