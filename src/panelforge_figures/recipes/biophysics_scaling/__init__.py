"""Biophysics scaling figures — power-laws, collapses, force curves, buckling."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="biophysics_scaling",
    description=(
        "Log-log scaling with slope boxes, master-curve collapses, "
        "force-length characteristics, power-law tail diagnostics, "
        "buckling critical-force plots, theory-overlay comparisons, "
        "universality-class selection, fractal-dimension box-counting, "
        "stress-strain regime maps, Kn × Re regime diagrams, 1-D energy-"
        "landscape cartoons, scaling-exponent CI forests, characteristic-"
        "time divergence, Π-group sensitivity bars, and crossover "
        "scaling diagnostics."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    buckling_critical_force_plot,
    characteristic_time_vs_control,
    crossover_scaling_diagnostic,
    energy_landscape_1d_cartoon,
    equivalence_forest_with_tost_bounds,
    force_length_characteristic,
    forward_simulation_validation_contract,
    fractal_dimension_scaling,
    hierarchical_effect_size_ladder,
    knudsen_reynolds_regime_diagram,
    log_log_scaling_with_slope_box,
    log_log_with_theory_line,
    master_curve_collapse,
    pi_group_sensitivity_bar,
    power_law_tail_diagnostic,
    pre_registered_censoring_mode_grid,
    scaling_exponent_ci_forest,
    stress_strain_regime_map,
    universality_class_comparison,
)

__all__ = [
    "AESTHETIC",
    "buckling_critical_force_plot",
    "characteristic_time_vs_control",
    "crossover_scaling_diagnostic",
    "energy_landscape_1d_cartoon",
    "equivalence_forest_with_tost_bounds",
    "force_length_characteristic",
    "forward_simulation_validation_contract",
    "fractal_dimension_scaling",
    "hierarchical_effect_size_ladder",
    "knudsen_reynolds_regime_diagram",
    "log_log_scaling_with_slope_box",
    "log_log_with_theory_line",
    "master_curve_collapse",
    "pi_group_sensitivity_bar",
    "power_law_tail_diagnostic",
    "pre_registered_censoring_mode_grid",
    "scaling_exponent_ci_forest",
    "stress_strain_regime_map",
    "universality_class_comparison",
]
