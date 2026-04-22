"""Diffusion and single-particle tracking figures."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="diffusion_and_tracking",
    description=(
        "Per-condition MSD curves, step-size distributions, angle "
        "autocorrelation decay, confinement-radius maps, track-"
        "persistence histograms, per-track α anomalous-diffusion fits, "
        "track-duration CCDFs, van Hove self-correlations, state-"
        "coloured spaghetti plots, HMM state dwell distributions, "
        "residence-conditional displacement matrices, spatial D maps, "
        "directionality polar histograms, EA-vs-TA ergodicity "
        "diagnostics, and confinement-radius time evolution."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    angle_correlation_decay,
    confinement_radius_map,
    confinement_radius_vs_time,
    diffusion_coefficient_heatmap_spatial,
    displacement_vs_state_residence,
    ensemble_vs_time_averaged_msd,
    hmm_state_dwell_distribution,
    jump_distance_van_hove,
    msd_anomalous_exponent_fit,
    msd_by_condition,
    step_size_distribution,
    track_directionality_polar,
    track_length_distribution,
    track_persistence_hist,
    track_spaghetti_plot_colored_by_state,
)

__all__ = [
    "AESTHETIC",
    "angle_correlation_decay",
    "confinement_radius_map",
    "confinement_radius_vs_time",
    "diffusion_coefficient_heatmap_spatial",
    "displacement_vs_state_residence",
    "ensemble_vs_time_averaged_msd",
    "hmm_state_dwell_distribution",
    "jump_distance_van_hove",
    "msd_anomalous_exponent_fit",
    "msd_by_condition",
    "step_size_distribution",
    "track_directionality_polar",
    "track_length_distribution",
    "track_persistence_hist",
    "track_spaghetti_plot_colored_by_state",
]
