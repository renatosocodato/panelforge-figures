"""Gantt-style timeline with milestones — canonical grant-proposal chart."""

from __future__ import annotations

import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class GanttTask(RecipeContract):
    name: str
    wp: str = "WP 1"
    start: float
    end: float


class GanttMilestone(RecipeContract):
    name: str
    at: float
    wp: str | None = None


class GanttInput(RecipeContract):
    tasks: list[GanttTask] = Field(..., min_length=1)
    milestones: list[GanttMilestone] = Field(default_factory=list)
    month_labels: list[str] | None = None
    x_label: str = "Months from kickoff"


def _demo() -> GanttInput:
    tasks = [
        GanttTask(name="Recruit cohorts", wp="WP 1", start=0, end=6),
        GanttTask(name="Imaging pipeline", wp="WP 1", start=3, end=15),
        GanttTask(name="ODE calibration", wp="WP 2", start=6, end=20),
        GanttTask(name="Gillespie surrogate", wp="WP 2", start=12, end=26),
        GanttTask(name="In vivo validation", wp="WP 3", start=18, end=30),
        GanttTask(name="Translational readout", wp="WP 3", start=22, end=36),
        GanttTask(name="Dissemination", wp="WP 4", start=24, end=36),
    ]
    mss = [
        GanttMilestone(name="M1 · data freeze", at=6),
        GanttMilestone(name="M2 · model locked", at=15),
        GanttMilestone(name="M3 · in vivo go/no-go", at=24),
        GanttMilestone(name="M4 · manuscripts", at=33),
    ]
    return GanttInput(tasks=tasks, milestones=mss)


_META = RecipeMetadata(
    name="timeline_gantt_with_milestones",
    modality="grant_and_conceptual",
    family=RecipeFamily.gantt,
    answers_question="When does each work package happen and when do its milestones land?",
    required_fields=("tasks",),
    optional_fields=("milestones", "month_labels", "x_label"),
    file_format_hints=("yaml", "toml", "csv"),
    alternatives_in_modality=("work_package_flow", "executive_summary_tile"),
    example_manifest="skill/example_manifests/fct_grant.yaml",
)


@register_recipe(metadata=_META, contract=GanttInput, demo_contract=_demo)
def render(contract: GanttInput, ax=None, **_):
    """Render a horizontal Gantt with per-WP color and milestone diamonds."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)
    wp_colors = {}
    for i, t in enumerate(contract.tasks):
        if t.wp not in wp_colors:
            wp_colors[t.wp] = palette[len(wp_colors)]
    tasks = list(contract.tasks)
    yticks = list(range(len(tasks)))
    yticklabels: list[str] = []
    for y, t in zip(yticks, tasks):
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (t.start, y - 0.36),
                max(t.end - t.start, 0.1),
                0.72,
                boxstyle="round,pad=0.02,rounding_size=0.2",
                facecolor=wp_colors[t.wp],
                edgecolor="white",
                alpha=0.88,
                linewidth=0.6,
            )
        )
        yticklabels.append(t.name)
        add_halo_label(
            ax,
            t.start + 0.3,
            y,
            t.wp,
            fontsize=6.6,
            color="white",
            halo_color=wp_colors[t.wp],
            halo_width=2.0,
            ha="left",
            va="center",
        )
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    ax.invert_yaxis()
    xmax = max(t.end for t in tasks)
    ax.set_xlim(-0.5, xmax + 1.0)
    ax.set_xlabel(contract.x_label)
    # Milestone diamonds — just the markers, label them in a legend below the axis.
    ms_color = "#D32F2F"
    for ms in contract.milestones:
        ax.scatter([ms.at], [-1.0], marker="D", s=55, color=ms_color,
                   edgecolor="white", linewidth=1.0, zorder=5, clip_on=False)
        # Short callout — just the Mn token above the marker.
        short = ms.name.split(" ")[0] if ms.name else ""
        add_halo_label(ax, ms.at, -1.9, short, fontsize=6.8, color=ms_color,
                       ha="center", va="bottom",
                       halo_width=2.4)

    # WP legend AND milestone legend sit below the x-axis on separate lines.
    # Use mpatches.Patch proxies in a real Legend so matplotlib handles spacing.
    from matplotlib.lines import Line2D
    wp_proxies = [
        mpatches.Patch(facecolor=wp_colors[wp], edgecolor="none", label=wp)
        for wp in sorted(wp_colors)
    ]
    ms_proxies = [
        Line2D([0], [0], marker="D", color="none", markerfacecolor=ms_color,
               markeredgecolor="white", markersize=7,
               label=" · ".join(m.name for m in contract.milestones[:4]))
    ] if contract.milestones else []
    leg = ax.legend(
        handles=wp_proxies + ms_proxies,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=min(len(wp_proxies) + len(ms_proxies), 5),
        frameon=False,
        fontsize=6.6,
        handlelength=1.6,
        columnspacing=1.0,
    )
    leg.set_in_layout(False)

    ax.grid(axis="x", which="major", color="#DDDDDD", linewidth=0.5, alpha=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_ylim(len(tasks) + 0.4, -2.8)
    ax.margins(x=0.01)
    return ax
