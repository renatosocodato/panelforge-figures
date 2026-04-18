"""Biophysics scaling figures — power-laws, collapses, force curves, buckling."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="biophysics_scaling",
    description=(
        "Log-log scaling with slope boxes, master-curve collapses, "
        "force-length characteristics, power-law tail diagnostics, and "
        "buckling critical-force plots."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    buckling_critical_force_plot,
    force_length_characteristic,
    log_log_scaling_with_slope_box,
    master_curve_collapse,
    power_law_tail_diagnostic,
)

__all__ = [
    "AESTHETIC",
    "buckling_critical_force_plot",
    "force_length_characteristic",
    "log_log_scaling_with_slope_box",
    "master_curve_collapse",
    "power_law_tail_diagnostic",
]
