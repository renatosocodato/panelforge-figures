"""Clinical cohort — survival, consort flow, subgroup effects, baseline balance."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="clinical_cohort",
    description=(
        "Kaplan-Meier survival, Cox forest, CONSORT flow, baseline "
        "characteristics balance, subgroup HR forests, outcome vs. "
        "exposure quartile, ROC with Youden cutoff, Hosmer-Lemeshow "
        "calibration, decision-curve net benefit, competing-risks "
        "CIF, time-varying HR (PH diagnostic), risk-score tertile "
        "ladder, NNT subgroup forest, propensity-score balance "
        "diagnostic, and per-AE incidence bars."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    adverse_event_incidence_bar,
    baseline_table_visualization,
    calibration_plot_with_hl_test,
    competing_risks_cumulative_incidence,
    consort_flow_diagram,
    cox_forest_hazard_ratios,
    decision_curve_analysis,
    hazard_ratio_over_time_smoothed,
    kaplan_meier_by_stratum,
    number_needed_to_treat_forest,
    outcome_by_quartile,
    propensity_score_balance_diagnostic,
    risk_score_discrimination_ladder,
    roc_with_cutoff_optimization,
    subgroup_forest_plot,
)

__all__ = [
    "AESTHETIC",
    "adverse_event_incidence_bar",
    "baseline_table_visualization",
    "calibration_plot_with_hl_test",
    "competing_risks_cumulative_incidence",
    "consort_flow_diagram",
    "cox_forest_hazard_ratios",
    "decision_curve_analysis",
    "hazard_ratio_over_time_smoothed",
    "kaplan_meier_by_stratum",
    "number_needed_to_treat_forest",
    "outcome_by_quartile",
    "propensity_score_balance_diagnostic",
    "risk_score_discrimination_ladder",
    "roc_with_cutoff_optimization",
    "subgroup_forest_plot",
]
