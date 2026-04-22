"""Deliverables timeline — point-event timeline of deliverables (D1.1,
D1.2, …) with per-WP colour coding and status markers.

Distinct from `timeline_gantt_with_milestones` (duration bars for
tasks): here each deliverable is a single month point-event on a
per-WP lane.
"""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class Deliverable(RecipeContract):
    id: str = Field(..., description="EU-style ID, e.g. 'D1.1'")
    title: str
    wp: str
    due_month: float
    status: str = Field(
        "pending",
        description="'pending' / 'on-track' / 'at-risk' / 'delivered'",
    )


class DeliverablesTimelineInput(RecipeContract):
    deliverables: list[Deliverable] = Field(..., min_length=4)
    months_total: int = Field(36, description="project duration in months")
    title: str = "Deliverables timeline"


def _demo() -> DeliverablesTimelineInput:
    return DeliverablesTimelineInput(
        deliverables=[
            Deliverable(id="D1.1", title="Data-mgmt plan",
                        wp="WP1", due_month=3, status="delivered"),
            Deliverable(id="D1.2", title="Cohort pipeline",
                        wp="WP1", due_month=9, status="on-track"),
            Deliverable(id="D1.3", title="Imaging dataset v1",
                        wp="WP1", due_month=18, status="pending"),
            Deliverable(id="D2.1", title="Model landscape",
                        wp="WP2", due_month=12, status="on-track"),
            Deliverable(id="D2.2", title="Sensitivity atlas",
                        wp="WP2", due_month=22, status="at-risk"),
            Deliverable(id="D3.1", title="In vivo rollout",
                        wp="WP3", due_month=28, status="pending"),
            Deliverable(id="D3.2", title="Pharmacology protocol",
                        wp="WP3", due_month=34, status="pending"),
            Deliverable(id="D4.1", title="Translational kit",
                        wp="WP4", due_month=32, status="pending"),
            Deliverable(id="D5.1", title="Final report",
                        wp="WP5", due_month=36, status="pending"),
        ],
        months_total=36,
    )


_META = RecipeMetadata(
    name="deliverables_timeline",
    modality="grant_and_conceptual",
    family=RecipeFamily.gantt,
    answers_question=(
        "When does each deliverable (D1.1, D1.2, …) fall, and which "
        "work-package lane does it belong to?"
    ),
    required_fields=("deliverables",),
    optional_fields=("months_total", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("timeline_gantt_with_milestones",),
)


@register_recipe(
    metadata=_META,
    contract=DeliverablesTimelineInput,
    demo_contract=_demo,
)
def render(contract: DeliverablesTimelineInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    dels = contract.deliverables
    months = int(contract.months_total)

    # WP lanes in encounter order.
    wps = list(dict.fromkeys(d.wp for d in dels))
    wp_y = {wp: i for i, wp in enumerate(wps)}
    wp_colors = {wp: palette[i % len(palette.colors)]
                 for i, wp in enumerate(wps)}

    # Lane backgrounds (≥3 patches for gantt rule — each lane is one
    # Rectangle, plus one per deliverable => many more).
    for wp, yi in wp_y.items():
        ax.add_patch(mpatches.Rectangle(
            (0, yi - 0.4), months, 0.8,
            facecolor="#F8F8F8", edgecolor="none", alpha=0.9, zorder=1,
        ))
        # Lane label at left.
        ax.text(-0.5, yi, wp, ha="right", va="center",
                fontsize=7.0, color="#333333")

    # Status → marker style.
    status_styles = {
        "delivered":  dict(marker="o", edgecolor="#2E7D32", size=0.6),
        "on-track":   dict(marker="o", edgecolor="#1565C0", size=0.6),
        "at-risk":    dict(marker="D", edgecolor="#F57C00", size=0.5),
        "pending":    dict(marker="o", edgecolor="#888888", size=0.5),
    }

    # Deliverable markers. Each WP lane is already a Rectangle patch
    # so the gantt ≥3-patches rule is satisfied via lanes.
    for d in dels:
        yi = wp_y[d.wp]
        style = status_styles.get(d.status, status_styles["pending"])
        color = wp_colors[d.wp]
        # Status-coloured ring under the WP-coloured fill.
        ax.scatter([d.due_month], [yi], s=180,
                   marker=style["marker"], color="white",
                   edgecolor=style["edgecolor"], linewidth=1.8,
                   zorder=4)
        ax.scatter([d.due_month], [yi], s=90,
                   marker=style["marker"], color=color,
                   edgecolor="white", linewidth=0.6,
                   alpha=0.95, zorder=5)
        # ID label inside / below marker.
        ax.text(d.due_month, yi - 0.02, d.id,
                ha="center", va="center", fontsize=5.8,
                color="white", fontweight="bold", zorder=6)
        # Title angled above marker (rotation=20) to avoid horizontal
        # overlap between closely-spaced deliverables.
        ax.text(d.due_month, yi + 0.25, d.title,
                ha="left", va="bottom", fontsize=5.8,
                color="#333333", rotation=20, zorder=5)

    # Year dividers.
    for year_m in range(12, months, 12):
        ax.axvline(year_m, color="#BBBBBB", lw=0.6, ls=":", zorder=2)

    ax.set_xlim(-1, months + 6)
    ax.set_ylim(-0.8, len(wps) - 0.2)
    ax.invert_yaxis()
    ax.set_yticks([])
    ax.set_xticks(list(range(0, months + 1, 6)))
    ax.set_xlabel("months from kickoff")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    # Status legend.
    status_patches = []
    for status in ["delivered", "on-track", "at-risk", "pending"]:
        s = status_styles[status]
        status_patches.append(
            mpatches.Patch(facecolor="white", edgecolor=s["edgecolor"],
                           label=status)
        )
    ax.legend(handles=status_patches, fontsize=6.8, frameon=False,
              loc="lower right", bbox_to_anchor=(1.0, -0.30),
              ncols=4, handlelength=1.0)

    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    return ax
