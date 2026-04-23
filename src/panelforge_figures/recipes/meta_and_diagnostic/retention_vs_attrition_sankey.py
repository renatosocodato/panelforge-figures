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
        _, ax = plt.subplots(figsize=(8.4, 3.6))
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

    # Horizontal layout. Each lane gets a centred retention bar
    # (52 % of lane width) with an attrition tab hanging off the
    # right edge. The left chunk of each lane is arrow-gap from the
    # previous stage, so 'n = N' never sits under an arrow head.
    lane_x = 0.02
    lane_w = (1.0 - 2 * lane_x) / n
    baseline_y = 0.52
    max_bar_h = 0.38
    bar_xfrac_lo = 0.18
    bar_xfrac_hi = 0.70
    drop_xfrac_lo = 0.74
    drop_xfrac_hi = 0.96

    prev_bar_right = None
    for i, stage in enumerate(stages):
        x = lane_x + i * lane_w
        bar_h = max_bar_h * (stage.retained / max_ret)
        # Stage retention bar.
        bar_left = x + lane_w * bar_xfrac_lo
        bar_width = lane_w * (bar_xfrac_hi - bar_xfrac_lo)
        ax.add_patch(mpatches.FancyBboxPatch(
            (bar_left, baseline_y - bar_h / 2),
            bar_width, bar_h,
            boxstyle="round,pad=0.002,rounding_size=0.010",
            facecolor="#1565C0", edgecolor="white", linewidth=0.6,
            alpha=0.92, zorder=3,
        ))
        # Stage name wrapped above bar, retention-n inside bar.
        stage_name_wrap = "\n".join(
            textwrap.wrap(stage.name, width=12,
                          break_long_words=False, break_on_hyphens=False)
        )
        ax.text(bar_left + bar_width / 2,
                baseline_y + max_bar_h / 2 + 0.04,
                stage_name_wrap,
                ha="center", va="bottom", fontsize=7.0,
                color="#263238", fontweight="bold", zorder=4)
        ax.text(bar_left + bar_width / 2, baseline_y,
                f"n = {stage.retained:,}",
                ha="center", va="center", fontsize=7.6,
                color="white", fontweight="bold", zorder=5)

        # Attrition tab on the right of the retention bar, inside lane.
        if stage.dropped > 0:
            drop_h = max_bar_h * (stage.dropped / max_ret)
            drop_left = x + lane_w * drop_xfrac_lo
            drop_width = lane_w * (drop_xfrac_hi - drop_xfrac_lo)
            ax.add_patch(mpatches.FancyBboxPatch(
                (drop_left, baseline_y - bar_h / 2),
                drop_width, drop_h,
                boxstyle="round,pad=0.002,rounding_size=0.008",
                facecolor="#E65100", edgecolor="white", linewidth=0.5,
                alpha=0.9, zorder=3,
            ))
            ax.text(drop_left + drop_width / 2,
                    baseline_y - bar_h / 2 + drop_h / 2,
                    f"-{stage.dropped}",
                    ha="center", va="center", fontsize=6.4,
                    color="white", fontweight="bold", zorder=5)
            reason_wrap = textwrap.fill(
                stage.reason, width=16,
                break_long_words=False, break_on_hyphens=False,
            )
            ax.text(drop_left + drop_width / 2,
                    baseline_y - bar_h / 2 - 0.02,
                    reason_wrap,
                    ha="center", va="top", fontsize=5.8,
                    color="#8E4500", zorder=4)

        # Connector arrow — head lands in the arrow-gap zone (the
        # left 0.18 of each lane), so it never overlaps the retention
        # bar or its 'n = N' label.
        if i > 0 and prev_bar_right is not None:
            arrow_head_x = x + lane_w * 0.14
            ax.annotate(
                "",
                xy=(arrow_head_x, baseline_y),
                xytext=(prev_bar_right, baseline_y),
                arrowprops=dict(arrowstyle="-|>", color="#455A64",
                                lw=1.2, mutation_scale=14,
                                shrinkA=0, shrinkB=0),
                zorder=2,
            )
        # Next arrow starts from the right edge of this lane's drop
        # tab (or bar if no drop).
        prev_bar_right = x + lane_w * (drop_xfrac_hi + 0.01)

    # Overall retention rate baked into title (keeps figure interior
    # free of floating callouts that could overlap reason text).
    initial = stages[0].retained
    final = stages[-1].retained
    retention_pct = 100 * final / max(initial, 1)
    ax.set_title(
        f"{contract.title}  ·  overall retention "
        f"{final} / {initial} ({retention_pct:.1f} %)",
        fontsize=8.6, pad=4,
    )
    return ax
