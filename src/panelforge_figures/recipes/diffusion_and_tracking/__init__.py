"""Diffusion and single-particle tracking figures."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="diffusion_and_tracking",
    description=(
        "Per-condition MSD curves, step-size distributions, angle "
        "autocorrelation decay, confinement-radius maps, track-persistence "
        "histograms."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    angle_correlation_decay,
    confinement_radius_map,
    msd_by_condition,
    step_size_distribution,
    track_persistence_hist,
)

__all__ = [
    "AESTHETIC",
    "angle_correlation_decay",
    "confinement_radius_map",
    "msd_by_condition",
    "step_size_distribution",
    "track_persistence_hist",
]
