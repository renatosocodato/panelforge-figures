"""Contact map with secondary-structure tracks — residue × residue
contact heatmap with α-helix / β-strand / loop tracks along both axes.
"""

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


class ContactMapInput(RecipeContract):
    contact_matrix: list[list[float]] = Field(
        ...,
        description=(
            "symmetric n_res × n_res matrix: 1 = contact, "
            "or continuous distance in Å"
        ),
    )
    secondary_structure: list[str] = Field(
        ...,
        description="per-residue SS code: 'H' / 'E' / '-'",
    )
    residue_labels: list[str] | None = Field(
        None, description="optional residue labels for axis ticks"
    )
    is_binary: bool = Field(
        True,
        description="True = binary contact matrix; False = distance matrix",
    )
    title: str = "Residue contact map"


def _demo() -> ContactMapInput:
    rng = np.random.default_rng(3011)
    n = 80
    # Build a synthetic contact map with diagonal + cross-helix contacts.
    M = np.zeros((n, n))
    # Diagonal band (local contacts).
    for i in range(n):
        for j in range(n):
            if abs(i - j) <= 4:
                M[i, j] = 1
    # Long-range helix-helix contacts.
    for start in [(10, 60), (25, 70)]:
        a, b = start
        for k in range(8):
            M[a + k, b + k] = 1
            M[b + k, a + k] = 1
    # Random noise contacts.
    for _ in range(40):
        i, j = rng.integers(0, n, 2)
        M[i, j] = 1
        M[j, i] = 1
    # Secondary structure.
    ss = ["-"] * n
    for start, end in [(8, 22), (30, 44), (58, 72)]:
        for i in range(start, end):
            ss[i] = "H"
    for start, end in [(48, 56)]:
        for i in range(start, end):
            ss[i] = "E"
    return ContactMapInput(
        contact_matrix=M.tolist(),
        secondary_structure=ss,
        is_binary=True,
    )


_META = RecipeMetadata(
    name="contact_map_with_secondary_structure",
    modality="cryoem_and_structure",
    family=RecipeFamily.matrix,
    answers_question=(
        "Which residue pairs form contacts, in the context of the "
        "protein's secondary structure?"
    ),
    required_fields=("contact_matrix", "secondary_structure"),
    optional_fields=("residue_labels", "is_binary", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("ramachandran_plot",),
)


@register_recipe(
    metadata=_META,
    contract=ContactMapInput,
    demo_contract=_demo,
)
def render(contract: ContactMapInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.contact_matrix, float)
    ss = contract.secondary_structure
    n = M.shape[0]

    if contract.is_binary:
        cmap_name = "Greys"
        vmin, vmax = 0.0, 1.0
    else:
        cmap_name = "viridis_r"
        vmin, vmax = 0.0, float(M[M > 0].max() if (M > 0).any() else 1.0)

    im = ax.imshow(M, cmap=cmap_name, origin="lower",
                   vmin=vmin, vmax=vmax,
                   extent=[0, n, 0, n],
                   interpolation="nearest", zorder=2)

    # Secondary-structure tracks along top (x) and right (y) edges.
    ss_colors = {"H": "#C62828", "E": "#2E7D32", "-": "#BDBDBD"}
    strip_h = n * 0.04
    # Top strip.
    i = 0
    while i < n:
        j = i
        while j < n and ss[j] == ss[i]:
            j += 1
        color = ss_colors.get(ss[i], "#BDBDBD")
        ax.add_patch(mpatches.Rectangle(
            (i, n), j - i, strip_h,
            facecolor=color, edgecolor="none", alpha=0.85,
            clip_on=False, zorder=4,
        ))
        i = j
    # Right strip.
    i = 0
    while i < n:
        j = i
        while j < n and ss[j] == ss[i]:
            j += 1
        color = ss_colors.get(ss[i], "#BDBDBD")
        ax.add_patch(mpatches.Rectangle(
            (n, i), strip_h, j - i,
            facecolor=color, edgecolor="none", alpha=0.85,
            clip_on=False, zorder=4,
        ))
        i = j

    # Diagonal.
    ax.plot([0, n], [0, n], color="#BBBBBB", lw=0.6, ls=":",
            zorder=3)

    ax.set_xlim(0, n + strip_h + 0.5)
    ax.set_ylim(0, n + strip_h + 0.5)
    ax.set_aspect("equal")
    ax.set_xlabel("residue i")
    ax.set_ylabel("residue j")

    # Contact stats + legend.
    n_contacts = int(np.sum(M > 0) // 2)
    frac_long = float(np.sum(
        [(M[i, j] > 0 and abs(i - j) > 12)
         for i in range(n) for j in range(n)]
    )) / max(n_contacts * 2, 1)

    proxies = [
        mpatches.Patch(facecolor="#C62828", label="α-helix"),
        mpatches.Patch(facecolor="#2E7D32", label="β-strand"),
        mpatches.Patch(facecolor="#BDBDBD", label="loop"),
    ]
    ax.legend(handles=proxies, fontsize=6.8, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=3, handlelength=1.0)

    ax.set_title(
        f"{contract.title}  ·  contacts = {n_contacts}  ·  "
        f"long-range fraction = {smart_fmt(frac_long)}",
        fontsize=8.2, pad=10,
    )
    return ax
