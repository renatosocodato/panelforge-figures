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
    censoring_mode_waterfall_cascade,
    characteristic_time_vs_control,
    compartment_paired_delta_scatter,
    compartment_split_curvature_crosscorr,
    confinement_energy_gauge_per_genotype,
    confinement_free_energy_vs_width_curve,
    crossover_scaling_diagnostic,
    dual_scale_significance_lollipop,
    energy_landscape_1d_cartoon,
    equivalence_forest_with_tost_bounds,
    euler_critical_length_crossing_distribution,
    feature_outcome_sankey_sig_vs_null,
    force_length_characteristic,
    forward_simulation_validation_contract,
    fractal_dimension_scaling,
    geometric_mediation_path_diagram,
    hierarchical_effect_size_ladder,
    knudsen_reynolds_regime_diagram,
    log_log_scaling_with_slope_box,
    log_log_with_theory_line,
    master_curve_collapse,
    ordered_trajectory_checkpoint_divergence,
    per_cell_colocalization_parallel_coordinates,
    persistence_length_lp_with_equivalence_bounds,
    pi_group_sensitivity_bar,
    power_law_tail_diagnostic,
    pre_registered_censoring_mode_grid,
    psd_active_gel_overlay_with_motor_inset,
    random_forest_importance_by_scale,
    robustness_neighborhood_phase_corner,
    s_state_frontier_tip_raster,
    scale_stratified_permanova_r2,
    scaling_exponent_ci_forest,
    shared_manifold_scatter_with_residuals,
    stress_strain_regime_map,
    universality_class_comparison,
    width_alignment_buffered_unbuffered_interaction,
    width_alpha_regime_phase_map,
    xz_microtubule_bowing_z_span,
    z_span_vs_width_with_euler_threshold,
)

__all__ = [
    "AESTHETIC",
    "buckling_critical_force_plot",
    "censoring_mode_waterfall_cascade",
    "characteristic_time_vs_control",
    "compartment_paired_delta_scatter",
    "compartment_split_curvature_crosscorr",
    "confinement_energy_gauge_per_genotype",
    "confinement_free_energy_vs_width_curve",
    "crossover_scaling_diagnostic",
    "dual_scale_significance_lollipop",
    "energy_landscape_1d_cartoon",
    "equivalence_forest_with_tost_bounds",
    "euler_critical_length_crossing_distribution",
    "feature_outcome_sankey_sig_vs_null",
    "force_length_characteristic",
    "forward_simulation_validation_contract",
    "fractal_dimension_scaling",
    "geometric_mediation_path_diagram",
    "hierarchical_effect_size_ladder",
    "knudsen_reynolds_regime_diagram",
    "log_log_scaling_with_slope_box",
    "log_log_with_theory_line",
    "master_curve_collapse",
    "ordered_trajectory_checkpoint_divergence",
    "per_cell_colocalization_parallel_coordinates",
    "persistence_length_lp_with_equivalence_bounds",
    "pi_group_sensitivity_bar",
    "power_law_tail_diagnostic",
    "pre_registered_censoring_mode_grid",
    "psd_active_gel_overlay_with_motor_inset",
    "random_forest_importance_by_scale",
    "robustness_neighborhood_phase_corner",
    "s_state_frontier_tip_raster",
    "scale_stratified_permanova_r2",
    "scaling_exponent_ci_forest",
    "shared_manifold_scatter_with_residuals",
    "stress_strain_regime_map",
    "universality_class_comparison",
    "width_alignment_buffered_unbuffered_interaction",
    "width_alpha_regime_phase_map",
    "xz_microtubule_bowing_z_span",
    "z_span_vs_width_with_euler_threshold",
]
