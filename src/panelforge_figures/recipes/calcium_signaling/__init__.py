"""Calcium signaling figures — event rasters, GCaMP trace stacks, waves, synchrony."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="calcium_signaling",
    description=(
        "Event rasters with population rate above, GCaMP trace stacks, "
        "event-frequency comparisons by condition, calcium-wave propagation "
        "fronts, spike-triggered averages, and synchronization matrices."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    calcium_propagation_wavefront,
    event_frequency_by_condition,
    event_raster_with_rate,
    gcamp_trace_stack,
    spike_triggered_average,
    synchronization_matrix,
)

__all__ = [
    "AESTHETIC",
    "calcium_propagation_wavefront",
    "event_frequency_by_condition",
    "event_raster_with_rate",
    "gcamp_trace_stack",
    "spike_triggered_average",
    "synchronization_matrix",
]
