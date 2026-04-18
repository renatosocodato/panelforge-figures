"""Work package flow — boxes with arrows showing inter-WP dependencies."""

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


class WorkPackage(RecipeContract):
    id: str
    title: str
    xy: tuple[float, float]                   # position in axis (0..1)
    size: tuple[float, float] = (0.24, 0.16)
    color_key: str = "signaling"
    bullets: list[str] = Field(default_factory=list)


class WorkPackageEdge(RecipeContract):
    src: str
    dst: str
    label: str | None = None


class WorkPackageFlowInput(RecipeContract):
    wps: list[WorkPackage] = Field(..., min_length=2)
    edges: list[WorkPackageEdge] = Field(default_factory=list)


def _demo() -> WorkPackageFlowInput:
    wps = [
        WorkPackage(id="WP1", title="Cohorts & Imaging",
                    xy=(0.08, 0.70), color_key="signaling",
                    bullets=["Recruit N=180", "2P intravital", "FRET"]),
        WorkPackage(id="WP2", title="Computational models",
                    xy=(0.40, 0.70), color_key="metabolic",
                    bullets=["ODE landscape", "Gillespie", "Sensitivity"]),
        WorkPackage(id="WP3", title="In vivo validation",
                    xy=(0.40, 0.30), color_key="cytoskeletal",
                    bullets=["Pharmacology", "Genetic tools", "Behavior"]),
        WorkPackage(id="WP4", title="Translational readouts",
                    xy=(0.72, 0.50), color_key="other",
                    bullets=["Patient biomarkers", "Clinical cohort", "Licensing"]),
    ]
    edges = [
        WorkPackageEdge(src="WP1", dst="WP2", label="data"),
        WorkPackageEdge(src="WP2", dst="WP3", label="predictions"),
        WorkPackageEdge(src="WP2", dst="WP4"),
        WorkPackageEdge(src="WP3", dst="WP4", label="validated target"),
    ]
    return WorkPackageFlowInput(wps=wps, edges=edges)


_META = RecipeMetadata(
    name="work_package_flow",
    modality="grant_and_conceptual",
    family=RecipeFamily.flow,
    answers_question="How do the work packages depend on each other and what flows between them?",
    required_fields=("wps",),
    optional_fields=("edges",),
    file_format_hints=("yaml", "toml"),
    alternatives_in_modality=("timeline_gantt_with_milestones", "conceptual_triptych"),
)


@register_recipe(metadata=_META, contract=WorkPackageFlowInput, demo_contract=_demo)
def render(contract: WorkPackageFlowInput, ax=None, **_):
    """Render WPs as rounded boxes + arrows for dependencies."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 3.8))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    palette = get_palette(AESTHETIC.primary_palette)

    # Draw boxes.
    wp_by_id: dict[str, WorkPackage] = {w.id: w for w in contract.wps}
    for wp in contract.wps:
        color = palette.pick(wp.color_key) if wp.color_key in palette.semantic else palette[0]
        x, y = wp.xy
        w, h = wp.size
        box = mpatches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.008,rounding_size=0.020",
            facecolor=color,
            edgecolor="white",
            linewidth=1.2,
            alpha=0.92,
        )
        ax.add_patch(box)
        add_halo_label(ax, x + w / 2, y + h - 0.028, wp.id,
                       fontsize=8.0, fontweight="bold", color="white",
                       halo_color=color, halo_width=1.8,
                       ha="center", va="top")
        ax.text(x + w / 2, y + h - 0.058, wp.title, ha="center", va="top",
                fontsize=7.6, color="white", fontweight="bold")
        for i, b in enumerate(wp.bullets[:4]):
            ax.text(x + 0.014, y + h - 0.085 - 0.022 * i, f"• {b}",
                    ha="left", va="top", fontsize=6.4, color="white", alpha=0.92)

    # Draw edges with arrowheads and optional labels.
    for e in contract.edges:
        src, dst = wp_by_id[e.src], wp_by_id[e.dst]
        sx = src.xy[0] + src.size[0] / 2
        sy = src.xy[1] + src.size[1] / 2
        dx = dst.xy[0] + dst.size[0] / 2
        dy = dst.xy[1] + dst.size[1] / 2
        ax.annotate(
            "",
            xy=(dx, dy),
            xytext=(sx, sy),
            arrowprops=dict(
                arrowstyle="-|>",
                color="#444444",
                lw=1.3,
                shrinkA=26,
                shrinkB=26,
                connectionstyle="arc3,rad=0.12",
            ),
            zorder=1,
        )
        if e.label:
            add_halo_label(ax, (sx + dx) / 2, (sy + dy) / 2 + 0.02,
                           e.label, fontsize=6.8, color="#333333",
                           fontweight="bold", halo_width=2.8)
    return ax
