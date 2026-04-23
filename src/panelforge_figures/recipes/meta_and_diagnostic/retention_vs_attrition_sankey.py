"""Cohort retention / attrition Sankey — participants flow through
enrolment, drop-outs, and analysis stages with per-stage retention
counts and attrition reasons.

Flow family: ≥2 rounded boxes + ≥1 arrow annotation.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class CohortStage(RecipeContract):
    name: str
    retained: int
    dropped: int = 0
    reason: str = ""


class RetentionSankeyInput(RecipeContract):
    stages: list[CohortStage] = Field(..., min_length=3, max_length=6)
    title: str = "Cohort retention / attrition"


def _demo() -> RetentionSankeyInput:
    return RetentionSankeyInput(
        stages=[
            CohortStage(name="Enrolled",        retained=420, dropped=0,
                        reason=""),
            CohortStage(name="Baseline visit",  retained=392, dropped=28,
                        reason="consent withdrawal"),
            CohortStage(name="Randomised",      retained=380, dropped=12,
                        reason="failed eligibility"),
            CohortStage(name="Mid-trial",       retained=338, dropped=42,
                        reason="adverse events + LTFU"),
            CohortStage(name="Analysis set",    retained=312, dropped=26,
                        reason="protocol deviations"),
        ],
    )


_META = RecipeMetadata(
    name="retention_vs_attrition_sankey",
    modality="meta_and_diagnostic",
    family=RecipeFamily.flow,
    answers_question=(
        "How do participants / samples flow through enrolment, drop-"
        "outs, and the analysis stages, and why do they leave?"
    ),
    required_fields=("stages",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("prisma_flow_diagram",),
)


@register_recipe(
    metadata=_META,
    contract=RetentionSankeyInput,
    demo_contract=_demo,
)
def render(contract: RetentionSankeyInput, ax=None, **_):
    import textwrap

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.8, 3.6))
    AESTHETIC.apply_to_ax(ax)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)

    stages = contract.stages
    n = len(stages)
    max_ret = max(s.retained for s in stages)

    # Horizontal layout.
    lane_x = 0.04
    lane_w = (1.0 - 2 * lane_x) / n
    baseline_y = 0.50
    max_bar_h = 0.40   # max stage bar height, scaled by retention

    prev_ret_x = None
    for i, stage in enumerate(stages):
        x = lane_x + i * lane_w
        bar_h = max_bar_h * (stage.retained / max_ret)
        # Stage retention bar.
        ax.add_patch(mpatches.FancyBboxPatch(
            (x + lane_w * 0.10, baseline_y - bar_h / 2),
            lane_w * 0.55, bar_h,
            boxstyle="round,pad=0.002,rounding_size=0.010",
            facecolor="#1565C0", edgecolor="white", linewidth=0.6,
            alpha=0.92, zorder=3,
        ))
        # Stage name above, retention n below-center.
        ax.text(x + lane_w * 0.375, baseline_y + bar_h / 2 + 0.04,
                stage.name,
                ha="center", va="bottom", fontsize=7.0,
                color="#263238", fontweight="bold", zorder=4)
        ax.text(x + lane_w * 0.375, baseline_y,
                f"n = {stage.retained:,}",
                ha="center", va="center", fontsize=7.6,
                color="white", fontweight="bold", zorder=5)

        # Attrition tab on the right of the retention bar.
        if stage.dropped > 0:
            drop_h = max_bar_h * (stage.dropped / max_ret)
            ax.add_patch(mpatches.FancyBboxPatch(
                (x + lane_w * 0.70, baseline_y - bar_h / 2),
                lane_w * 0.22, drop_h,
                boxstyle="round,pad=0.002,rounding_size=0.008",
                facecolor="#E65100", edgecolor="white", linewidth=0.5,
                alpha=0.9, zorder=3,
            ))
            ax.text(x + lane_w * 0.81,
                    baseline_y - bar_h / 2 + drop_h / 2,
                    f"-{stage.dropped}",
                    ha="center", va="center", fontsize=6.4,
                    color="white", fontweight="bold", zorder=5)
            reason_wrap = textwrap.fill(stage.reason, width=18)
            ax.text(x + lane_w * 0.81, baseline_y - bar_h / 2 - 0.02,
                    reason_wrap,
                    ha="center", va="top", fontsize=5.8,
                    color="#8E4500", zorder=4)

        # Connector arrow from prev right-edge to this left-edge.
        if i > 0:
            ax.annotate(
                "",
                xy=(x + lane_w * 0.10, baseline_y),
                xytext=(prev_ret_x, baseline_y),
                arrowprops=dict(arrowstyle="-|>", color="#455A64",
                                lw=1.2, mutation_scale=14),
                zorder=2,
            )
        prev_ret_x = x + lane_w * 0.65

    # Overall retention rate callout.
    initial = stages[0].retained
    final = stages[-1].retained
    retention_pct = 100 * final / max(initial, 1)
    ax.text(0.02, 0.02,
            f"overall retention: {final} / {initial} "
            f"({retention_pct:.1f} %)",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.8, color="#263238",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    return ax
