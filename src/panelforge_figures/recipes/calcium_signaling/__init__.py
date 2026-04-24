"""Calcium signaling figures — rasters, traces, waves, synchrony, landscapes, phase."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="calcium_signaling",
    description=(
        "Event rasters with population rate above + network-burst "
        "detection overlays, GCaMP trace stacks, stim-triggered cell × "
        "time heatmaps, event-frequency and event-amplitude distributions "
        "by condition, calcium-wave propagation fronts + wave-speed maps, "
        "peri-event time histograms, spike-triggered averages, pairwise "
        "synchronization matrices + population synchronization timelines, "
        "single-cell (frequency, amplitude) landscapes, Ca2+ × FRET joint "
        "plots, dominant-oscillation phase polar diagrams."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    calcium_and_fret_joint_plot,
    calcium_event_amplitude_distribution,
    calcium_event_onset_alignment,
    calcium_propagation_wavefront,
    calcium_wave_speed_map,
    event_frequency_by_condition,
    event_raster_with_rate,
    gcamp_trace_stack,
    network_burst_detection_overlay,
    oscillation_frequency_polar,
    population_synchronization_timeline,
    single_cell_calcium_landscape,
    spike_triggered_average,
    stimulus_triggered_calcium_heatmap,
    synchronization_matrix,
)

__all__ = [
    "AESTHETIC",
    "calcium_and_fret_joint_plot",
    "calcium_event_amplitude_distribution",
    "calcium_event_onset_alignment",
    "calcium_propagation_wavefront",
    "calcium_wave_speed_map",
    "event_frequency_by_condition",
    "event_raster_with_rate",
    "gcamp_trace_stack",
    "network_burst_detection_overlay",
    "oscillation_frequency_polar",
    "population_synchronization_timeline",
    "single_cell_calcium_landscape",
    "spike_triggered_average",
    "stimulus_triggered_calcium_heatmap",
    "synchronization_matrix",
]
