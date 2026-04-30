"""Hub-gene radial — hub at centre, first-neighbours on a circle."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class HubRadialInput(RecipeContract):
    hub_name: str = Field(..., description="central gene / node")
    neighbour_names: list[str] = Field(..., min_length=3)
    edge_weight: list[float] = Field(..., description="per-neighbour weight in [0, 1]")
    interaction_sign: list[int] | None = Field(
        None, description="+1 = activator, -1 = repressor per neighbour"
    )
    title: str = "Hub-gene radial"


def _demo() -> HubRadialInput:
    rng = np.random.default_rng(521)
    neighbours = [f"n{i:02d}" for i in range(12)]
    weights = rng.uniform(0.2, 1.0, len(neighbours)).tolist()
    signs = rng.choice([-1, 1], len(neighbours), p=[0.35, 0.65]).tolist()
    return HubRadialInput(
        hub_name="TF1",
        neighbour_names=neighbours,
        edge_weight=weights,
        interaction_sign=signs,
    )


_META = RecipeMetadata(
    name="hub_gene_radial",
    modality="network_and_pathway",
    family=RecipeFamily.conceptual,
    answers_question=(
        "Around a single hub gene, what are its immediate neighbours "
        "and their edge weights?"
    ),
    required_fields=("hub_name", "neighbour_names", "edge_weight"),
    optional_fields=("interaction_sign", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("regulatory_network_hive",),
)


@register_recipe(
    metadata=_META,
    contract=HubRadialInput,
    demo_contract=_demo,
)
def render(contract: HubRadialInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    neighbours = contract.neighbour_names
    weights = np.asarray(contract.edge_weight, float)
    signs = (np.asarray(contract.interaction_sign, int)
             if contract.interaction_sign is not None
             else np.ones(len(neighbours), int))
    n = len(neighbours)

    theta = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / 2

    # Normalise weights so the longest is at R=1.0.
    r_max = 1.0
    r_min = 0.35
    w_norm = weights / max(weights.max(), 1e-6)
    radii = r_min + (r_max - r_min) * w_norm

    activator_color = "#2E7D32"
    repressor_color = "#C62828"

    # Edges from hub at (0, 0) to each neighbour.
    for i, (th, r, s) in enumerate(zip(theta, radii, signs)):
        x = r * np.cos(th)
        y = r * np.sin(th)
        color = activator_color if s >= 0 else repressor_color
        ax.annotate(
            "", xy=(x, y), xytext=(0, 0),
            arrowprops=dict(
                arrowstyle="->", color=color,
                alpha=0.55 + 0.45 * w_norm[i],
                lw=0.5 + 1.2 * w_norm[i],
                shrinkA=6, shrinkB=10,
            ),
            zorder=2,
        )
        # Neighbour node.
        ax.add_patch(mpatches.Circle(
            (x, y), 0.07,
            facecolor=color, edgecolor="white", linewidth=0.8,
            alpha=0.85, zorder=4,
        ))
        # Neighbour label outside marker.
        label_r = r_max + 0.15
        ax.text(label_r * np.cos(th), label_r * np.sin(th), neighbours[i],
                ha="center", va="center", fontsize=6.6,
                color=color, zorder=6)

    # Hub centre.
    ax.add_patch(mpatches.Circle(
        (0, 0), 0.14,
        facecolor="#111111", edgecolor="white", linewidth=1.2,
        zorder=5,
    ))
    ax.text(0, 0, contract.hub_name, ha="center", va="center",
            fontsize=7.2, color="white", fontweight="bold", zorder=6)

    # Weight reference rings. Labels parked at the bottom (theta=3π/2)
    # so they don't collide with neighbour arrowheads on the right rim.
    for r_ref, lab in [(r_min, "min"), (r_max, "max")]:
        ax.add_patch(mpatches.Circle(
            (0, 0), r_ref,
            facecolor="none", edgecolor="#DDDDDD", linewidth=0.5,
            linestyle=":", zorder=1,
        ))
        ax.text(0, -r_ref - 0.05, lab,
                ha="center", va="top",
                fontsize=5.6, color="#999999", zorder=1)

    # Legend proxies.
    proxies = [
        mpatches.Patch(facecolor=activator_color, edgecolor="white",
                       label=f"activator (n={int((signs >= 0).sum())})"),
        mpatches.Patch(facecolor=repressor_color, edgecolor="white",
                       label=f"repressor (n={int((signs < 0).sum())})"),
    ]
    ax.legend(handles=proxies, fontsize=6.4, frameon=False,
              loc="lower center", bbox_to_anchor=(0.5, -0.06),
              ncols=2, handlelength=1.2)

    ax.set_xlim(-1.4, 1.4)
    ax.set_ylim(-1.4, 1.4)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title(
        f"{contract.title}  ·  {contract.hub_name} "
        f"({n} neighbours, mean w={smart_fmt(float(weights.mean()))})",
        fontsize=8.6, pad=6,
    )
    return ax
