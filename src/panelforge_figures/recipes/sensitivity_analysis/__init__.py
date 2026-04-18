"""Sensitivity analysis — Sobol, Morris, 2D scans, Pi-group collapses.

Used whenever a model (ODE, PDE, ABM, statistical, mechanistic) has more than
~3 parameters and the question is which ones matter for which output.
"""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="sensitivity_analysis",
    description=(
        "Global sensitivity (Sobol, Morris), parameter scans, dimensionless "
        "Pi-group collapses, interaction matrices, and convergence diagnostics."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    convergence_diagnostic_sobol,
    dimensionless_pi_group_collapse,
    fast_subspace_detection,
    interaction_matrix_sobol,
    morris_elementary_effects,
    parameter_scan_2d_contour,
    pi_group_rank_plot,
    sobol_first_total_pair,
)

__all__ = [
    "AESTHETIC",
    "convergence_diagnostic_sobol",
    "dimensionless_pi_group_collapse",
    "fast_subspace_detection",
    "interaction_matrix_sobol",
    "morris_elementary_effects",
    "parameter_scan_2d_contour",
    "pi_group_rank_plot",
    "sobol_first_total_pair",
]
