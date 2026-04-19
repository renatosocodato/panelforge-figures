"""FRET biosensor figures — ratiometric imaging, dose/time responses, kymographs."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="fret_biosensors",
    description=(
        "Ratiometric FRET imaging figures: donor/acceptor channels and "
        "linearity diagnostics, field-level and edge-to-centre kymographs, "
        "ROI grids, dose × time response matrices, Hill fits, hierarchical "
        "CI timecourses, paired pre/post stimulus comparisons, single-cell "
        "responder partitioning, stimulus-response fans, windowed-ROI "
        "trajectories, FRET-vs-orthogonal-activity regressions, "
        "signal-to-noise maps, Förster-distance calibrations, sensor "
        "calibration curves, and ratio maps with cell-segmentation overlays."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    biosensor_dose_response_matrix,
    donor_acceptor_dual_channel,
    donor_acceptor_scatter_linearity,
    dose_response_hill_fret,
    fret_efficiency_vs_distance,
    fret_signal_to_noise_map,
    fret_vs_scalar_activity_regression,
    kymograph_ratio_edge_to_center,
    paired_pre_post_stimulus,
    ratio_distribution_by_condition,
    ratio_heatmap_over_field,
    ratio_map_with_segmentation_overlay,
    ratio_timecourse_hierarchical_ci,
    roi_ratio_summary_grid,
    sensor_calibration_curve,
    single_cell_ratio_trajectories,
    stimulus_response_fan,
    windowed_roi_ratio_trajectory,
)

__all__ = [
    "AESTHETIC",
    "biosensor_dose_response_matrix",
    "donor_acceptor_dual_channel",
    "donor_acceptor_scatter_linearity",
    "dose_response_hill_fret",
    "fret_efficiency_vs_distance",
    "fret_signal_to_noise_map",
    "fret_vs_scalar_activity_regression",
    "kymograph_ratio_edge_to_center",
    "paired_pre_post_stimulus",
    "ratio_distribution_by_condition",
    "ratio_heatmap_over_field",
    "ratio_map_with_segmentation_overlay",
    "ratio_timecourse_hierarchical_ci",
    "roi_ratio_summary_grid",
    "sensor_calibration_curve",
    "single_cell_ratio_trajectories",
    "stimulus_response_fan",
    "windowed_roi_ratio_trajectory",
]
