"""FRET biosensor figures — ratio fields, timecourses, calibrations, SNR maps."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="fret_biosensors",
    description=(
        "Ratio heatmaps over imaging fields, hierarchical-CI ratio "
        "timecourses, stimulus-response fans, donor/acceptor dual-channel "
        "views, sensor calibration curves, FRET-specific Hill dose-response, "
        "single-cell ratio trajectories, ratio distributions by condition, "
        "signal-to-noise maps, ROI-level summary grids."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    donor_acceptor_dual_channel,
    dose_response_hill_fret,
    fret_signal_to_noise_map,
    ratio_distribution_by_condition,
    ratio_heatmap_over_field,
    ratio_timecourse_hierarchical_ci,
    roi_ratio_summary_grid,
    sensor_calibration_curve,
    single_cell_ratio_trajectories,
    stimulus_response_fan,
)

__all__ = [
    "AESTHETIC",
    "donor_acceptor_dual_channel",
    "dose_response_hill_fret",
    "fret_signal_to_noise_map",
    "ratio_distribution_by_condition",
    "ratio_heatmap_over_field",
    "ratio_timecourse_hierarchical_ci",
    "roi_ratio_summary_grid",
    "sensor_calibration_curve",
    "single_cell_ratio_trajectories",
    "stimulus_response_fan",
]
