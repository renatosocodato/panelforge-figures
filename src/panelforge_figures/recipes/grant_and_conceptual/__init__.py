"""Grant and conceptual figures — executive summaries, Gantts, WP flows, etc.

This modality is decorative/strategic. Its visual DNA emphasizes readable
typography, semantic color coding (mechanism_class or journal_neutral
palettes), and generous white space over data density.
"""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="grant_and_conceptual",
    description=(
        "Executive summaries, Gantts, work-package flows, hypothesis "
        "diagrams, team matrices, conceptual triptychs, aims pyramids, "
        "linear methods pipelines, milestone × risk matrices, "
        "innovation-positioning quadrants, cost-by-WP stacked bars, "
        "ethics & impact blocks, interdisciplinary spider plots, team "
        "network graphs, and deliverable-point timelines for grant "
        "proposals."
    ),
    aesthetic=AESTHETIC,
)

# Importing each recipe module triggers its @register_recipe decorator.
from . import (  # noqa: E402,F401
    conceptual_triptych,
    cost_by_work_package_bar,
    deliverables_timeline,
    ethics_and_impact_block,
    executive_summary_tile,
    hypothesis_diagram,
    innovation_positioning_quadrant,
    interdisciplinary_contribution_spider,
    methods_pipeline_flow,
    milestone_vs_risk_matrix,
    research_aims_pyramid,
    team_expertise_matrix,
    team_network_graph,
    timeline_gantt_with_milestones,
    work_package_flow,
)

__all__ = [
    "AESTHETIC",
    "conceptual_triptych",
    "cost_by_work_package_bar",
    "deliverables_timeline",
    "ethics_and_impact_block",
    "executive_summary_tile",
    "hypothesis_diagram",
    "innovation_positioning_quadrant",
    "interdisciplinary_contribution_spider",
    "methods_pipeline_flow",
    "milestone_vs_risk_matrix",
    "research_aims_pyramid",
    "team_expertise_matrix",
    "team_network_graph",
    "timeline_gantt_with_milestones",
    "work_package_flow",
]
