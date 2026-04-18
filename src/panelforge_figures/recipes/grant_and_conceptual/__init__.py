"""Grant and conceptual figures — executive summaries, Gantts, WP flows, etc.

This modality is decorative/strategic. Its visual DNA emphasizes readable
typography, semantic color coding (mechanism_class or journal_neutral
palettes), and generous white space over data density.
"""

from ._aesthetic import AESTHETIC
from ...core.contract import register_modality

register_modality(
    name="grant_and_conceptual",
    description=(
        "Executive summaries, Gantts, work-package flows, hypothesis diagrams, "
        "team matrices, and conceptual triptychs for grant proposals."
    ),
    aesthetic=AESTHETIC,
)

# Importing each recipe module triggers its @register_recipe decorator.
from . import (  # noqa: E402,F401
    conceptual_triptych,
    executive_summary_tile,
    hypothesis_diagram,
    team_expertise_matrix,
    timeline_gantt_with_milestones,
    work_package_flow,
)

__all__ = [
    "AESTHETIC",
    "conceptual_triptych",
    "executive_summary_tile",
    "hypothesis_diagram",
    "team_expertise_matrix",
    "timeline_gantt_with_milestones",
    "work_package_flow",
]
