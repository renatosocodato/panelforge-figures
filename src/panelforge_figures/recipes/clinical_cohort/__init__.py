"""Clinical cohort — survival, consort flow, subgroup effects, baseline balance."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="clinical_cohort",
    description=(
        "Kaplan-Meier survival, Cox forest, CONSORT flow, baseline "
        "characteristics balance, subgroup HR forests, and outcome "
        "vs. exposure quartile."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    baseline_table_visualization,
    consort_flow_diagram,
    cox_forest_hazard_ratios,
    kaplan_meier_by_stratum,
    outcome_by_quartile,
    subgroup_forest_plot,
)

__all__ = [
    "AESTHETIC",
    "baseline_table_visualization",
    "consort_flow_diagram",
    "cox_forest_hazard_ratios",
    "kaplan_meier_by_stratum",
    "outcome_by_quartile",
    "subgroup_forest_plot",
]
