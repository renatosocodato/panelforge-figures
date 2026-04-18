"""Gillespie stochastic simulation figures — trajectories, dwell times, spectra."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="gillespie_stochastic",
    description=(
        "Trajectory fans with first-passage-time markers, log-scale dwell-time "
        "violins, waiting-time ECDFs with analytical fits, rate vs control-"
        "parameter curves, state occupancy rasters, ensemble mean-variance "
        "tubes, noise power spectra."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    dwell_time_log_violin,
    ensemble_mean_variance_tube,
    noise_power_spectrum,
    rate_vs_control_parameter,
    state_occupancy_raster,
    trajectory_fan_with_fpt,
    waiting_time_ecdf_fitted,
)

__all__ = [
    "AESTHETIC",
    "dwell_time_log_violin",
    "ensemble_mean_variance_tube",
    "noise_power_spectrum",
    "rate_vs_control_parameter",
    "state_occupancy_raster",
    "trajectory_fan_with_fpt",
    "waiting_time_ecdf_fitted",
]
