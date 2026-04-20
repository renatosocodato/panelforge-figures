"""Sensitivity analysis — Sobol, Morris, FAST, LHS, tornado, 2D scans, Pi-group collapses.

Used whenever a model (ODE, PDE, ABM, statistical, mechanistic) has more than
~3 parameters and the question is which ones matter for which output.
"""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="sensitivity_analysis",
    description=(
        "Global sensitivity (Sobol, Morris, FAST), LHS sampling-design "
        "coverage, OAT tornado, multi-output sensitivity matrices, "
        "bootstrap-CI convergence, interaction graphs, time-resolved "
        "sensitivity indices, 2-D parameter scans, dimensionless "
        "Pi-group collapses, active-subspace detection, and pairwise "
        "interaction matrices."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    convergence_diagnostic_sobol,
    dimensionless_pi_group_collapse,
    fast_sensitivity_spectrum,
    fast_subspace_detection,
    interaction_matrix_sobol,
    interaction_network_sobol,
    lhs_parameter_space_coverage,
    morris_elementary_effects,
    parameter_scan_2d_contour,
    pi_group_rank_plot,
    sensitivity_by_output_quantity,
    sensitivity_time_evolution,
    sobol_bootstrap_convergence,
    sobol_first_total_pair,
    tornado_diagram,
)

__all__ = [
    "AESTHETIC",
    "convergence_diagnostic_sobol",
    "dimensionless_pi_group_collapse",
    "fast_sensitivity_spectrum",
    "fast_subspace_detection",
    "interaction_matrix_sobol",
    "interaction_network_sobol",
    "lhs_parameter_space_coverage",
    "morris_elementary_effects",
    "parameter_scan_2d_contour",
    "pi_group_rank_plot",
    "sensitivity_by_output_quantity",
    "sensitivity_time_evolution",
    "sobol_bootstrap_convergence",
    "sobol_first_total_pair",
    "tornado_diagram",
]
