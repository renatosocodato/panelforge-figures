"""Team / consortium network graph — partner nodes (colour by
institution, size by role seniority) and prior-collaboration edges.

Conceptual family: ≥3 text labels + ≥2 Circle patches.
"""

from __future__ import annotations

import numpy as np
import matplotlib.patches as mpatches
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class Partner(RecipeContract):
    id: str
    name: str
    institution: str
    role: str = Field(
        "member",
        description="coordinator / PI / co-I / postdoc / student / member",
    )


class Collaboration(RecipeContract):
    a: str
    b: str
    strength: float = Field(0.5, ge=0.0, le=1.0,
                            description="prior collaboration strength in [0,1]")


class TeamNetworkInput(RecipeContract):
    partners: list[Partner] = Field(..., min_length=4)
    collaborations: list[Collaboration] = Field(default_factory=list)
    title: str = "Consortium network"


def _demo() -> TeamNetworkInput:
    return TeamNetworkInput(
        partners=[
            Partner(id="P1", name="PI", institution="i3S",
                    role="coordinator"),
            Partner(id="P2", name="co-I", institution="i3S",
                    role="co-I"),
            Partner(id="P3", name="postdoc A", institution="i3S",
                    role="postdoc"),
            Partner(id="P4", name="PI-partner", institution="INESC",
                    role="PI"),
            Partner(id="P5", name="postdoc B", institution="INESC",
                    role="postdoc"),
            Partner(id="P6", name="clinical", institution="CHUSJ",
                    role="clinician"),
            Partner(id="P7", name="industry",
                    institution="spin-out", role="CSO"),
        ],
        collaborations=[
            Collaboration(a="P1", b="P2", strength=0.95),
            Collaboration(a="P1", b="P3", strength=0.80),
            Collaboration(a="P1", b="P4", strength=0.65),
            Collaboration(a="P4", b="P5", strength=0.90),
            Collaboration(a="P2", b="P5", strength=0.50),
            Collaboration(a="P1", b="P6", strength=0.40),
            Collaboration(a="P6", b="P7", strength=0.35),
            Collaboration(a="P1", b="P7", strength=0.30),
        ],
    )


_META = RecipeMetadata(
    name="team_network_graph",
    modality="grant_and_conceptual",
    family=RecipeFamily.conceptual,
    answers_question=(
        "How do partners in the consortium connect (institution, role, "
        "prior-collaboration strength)?"
    ),
    required_fields=("partners",),
    optional_fields=("collaborations", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("team_expertise_matrix", "work_package_flow"),
)


def _radial_layout(partners, seed=0):
    """Group by institution around a circle, institutions in sectors."""
    rng = np.random.default_rng(seed)
    insts = list(dict.fromkeys(p.institution for p in partners))
    n_inst = len(insts)
    pos: dict[str, np.ndarray] = {}
    for ii, inst in enumerate(insts):
        members = [p for p in partners if p.institution == inst]
        # Sector angle.
        theta0 = 2 * np.pi * ii / max(n_inst, 1) - np.pi / 2
        sector_w = 2 * np.pi / max(n_inst, 1) * 0.7
        # Radial placement with inner ring for coordinators.
        for mi, p in enumerate(members):
            r = 0.75 if p.role == "coordinator" else 0.88
            if len(members) > 1:
                th = theta0 + sector_w * (mi / max(len(members) - 1, 1) - 0.5)
            else:
                th = theta0
            th += rng.uniform(-0.02, 0.02)
            pos[p.id] = np.array([r * np.cos(th), r * np.sin(th)])
    return pos


@register_recipe(
    metadata=_META,
    contract=TeamNetworkInput,
    demo_contract=_demo,
)
def render(contract: TeamNetworkInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    pos = _radial_layout(contract.partners, seed=7)

    # Institution colour map.
    insts = list(dict.fromkeys(p.institution for p in contract.partners))
    inst_colors = ["#1976D2", "#D81B60", "#388E3C", "#F57C00", "#6A1B9A"]
    imap = {inst: inst_colors[i % len(inst_colors)]
            for i, inst in enumerate(insts)}

    # Role → size map.
    role_size = {
        "coordinator": 0.14,
        "PI": 0.11,
        "co-I": 0.10,
        "postdoc": 0.08,
        "student": 0.07,
        "CSO": 0.10,
        "clinician": 0.10,
        "member": 0.085,
    }

    # Edges.
    for edge in contract.collaborations:
        if edge.a not in pos or edge.b not in pos:
            continue
        p_a = pos[edge.a]
        p_b = pos[edge.b]
        lw = 0.5 + 1.4 * edge.strength
        alpha = 0.35 + 0.55 * edge.strength
        ax.plot([p_a[0], p_b[0]], [p_a[1], p_b[1]],
                color="#888888", lw=lw, alpha=alpha, zorder=2)

    # Nodes.
    for p in contract.partners:
        xy = pos[p.id]
        r = role_size.get(p.role, 0.09)
        color = imap[p.institution]
        ax.add_patch(mpatches.Circle(
            xy, r, facecolor=color, edgecolor="white",
            linewidth=1.0, alpha=0.92, zorder=4,
        ))
        # Short ID inside the circle (always fits).
        ax.text(xy[0], xy[1], p.id,
                ha="center", va="center", fontsize=6.6,
                color="white", fontweight="bold", zorder=5)
        # Full name + role below circle (name first, then role on a
        # second line in a lighter weight).
        ax.text(xy[0], xy[1] - r - 0.025, p.name,
                ha="center", va="top", fontsize=6.4,
                color="#222222", zorder=5)
        ax.text(xy[0], xy[1] - r - 0.080, f"({p.role})",
                ha="center", va="top", fontsize=5.8,
                color="#777777", zorder=5)

    # Institution legend (Patch proxies).
    proxies = [
        mpatches.Patch(facecolor=imap[i], edgecolor="white", label=i)
        for i in insts
    ]
    ax.legend(handles=proxies, fontsize=6.8, frameon=False,
              loc="lower center", bbox_to_anchor=(0.5, -0.08),
              ncols=min(len(insts), 5), handlelength=1.0)

    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"{contract.title}  ·  {len(contract.partners)} partners "
        f"across {len(insts)} institutions",
        fontsize=8.6, pad=6,
    )
    return ax
