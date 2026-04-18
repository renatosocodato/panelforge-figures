"""Work package flow — boxes with arrows showing inter-WP dependencies."""

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


class WorkPackage(RecipeContract):
    id: str
    title: str
    xy: tuple[float, float]                   # position in axis (0..1)
    size: tuple[float, float] = (0.28, 0.22)
    color_key: str = "signaling"
    bullets: list[str] = Field(default_factory=list, max_length=3)


class WorkPackageEdge(RecipeContract):
    src: str
    dst: str
    label: str | None = None


class WorkPackageFlowInput(RecipeContract):
    wps: list[WorkPackage] = Field(..., min_length=2)
    edges: list[WorkPackageEdge] = Field(default_factory=list)


def _demo() -> WorkPackageFlowInput:
    wps = [
        WorkPackage(id="WP1", title="Cohorts & imaging",
                    xy=(0.02, 0.60), size=(0.30, 0.32),
                    color_key="signaling",
                    bullets=["Recruit N=180", "FRET + 2P"]),
        WorkPackage(id="WP2", title="Computation",
                    xy=(0.36, 0.60), size=(0.30, 0.32),
                    color_key="metabolic",
                    bullets=["ODE landscape", "Sensitivity"]),
        WorkPackage(id="WP3", title="In vivo",
                    xy=(0.36, 0.10), size=(0.30, 0.32),
                    color_key="cytoskeletal",
                    bullets=["Pharmacology", "Genetic tools"]),
        WorkPackage(id="WP4", title="Translation",
                    xy=(0.70, 0.35), size=(0.28, 0.32),
                    color_key="other",
                    bullets=["Biomarkers", "Clinical"]),
    ]
    edges = [
        WorkPackageEdge(src="WP1", dst="WP2", label="data"),
        WorkPackageEdge(src="WP2", dst="WP3", label="preds"),
        WorkPackageEdge(src="WP2", dst="WP4"),
        WorkPackageEdge(src="WP3", dst="WP4", label="target"),
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
        _, ax = plt.subplots(figsize=(5.6, 3.6))
    AESTHETIC.apply_to_ax(ax)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    palette = get_palette(AESTHETIC.primary_palette)

    wp_by_id: dict[str, WorkPackage] = {w.id: w for w in contract.wps}
    for wp in contract.wps:
        color = palette.pick(wp.color_key) if wp.color_key in palette.semantic else palette[0]
        x, y = wp.xy
        w, h = wp.size
        ax.add_patch(mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.006,rounding_size=0.014",
            facecolor=color, edgecolor="white",
            linewidth=1.2, alpha=0.94,
        ))
        # ID at the top strip.
        ax.text(x + w / 2, y + h - 0.035, wp.id,
                ha="center", va="top", color="white",
                fontsize=8.2, fontweight="bold")
        # Title below ID — one compact line.
        ax.text(x + w / 2, y + h - 0.085, wp.title,
                ha="center", va="top", color="white",
                fontsize=6.6, fontweight="bold", alpha=0.92)
        # Bullets — keep max 2 visible to avoid overflow at small sizes.
        for i, b in enumerate(wp.bullets[:2]):
            ax.text(x + 0.012, y + h - 0.12 - 0.050 * (i + 1),
                    f"• {b}",
                    ha="left", va="top", color="white",
                    fontsize=6.0, alpha=0.92)

    # Edges: curved arrows, labels with halo effect via white bbox.
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
                lw=1.2,
                shrinkA=32,
                shrinkB=32,
                connectionstyle="arc3,rad=0.18",
            ),
            zorder=1,
        )
        if e.label:
            ax.text((sx + dx) / 2, (sy + dy) / 2 + 0.02,
                    e.label, ha="center", va="center",
                    color="#333333", fontsize=6.6, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.12", fc="white",
                              ec="none", alpha=0.92),
                    zorder=2)
    return ax
