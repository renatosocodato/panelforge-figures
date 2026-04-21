"""(Sender × receiver) × LR-pair dotplot for cell-cell signaling.

Rows are ligand-receptor pairs, columns are ordered (sender → receiver)
cell-type pairs. Dot size ∝ interaction strength (e.g., communication
probability), colour ∝ −log10(p-value) for significance. Standard
CellChat / CellPhoneDB output grammar.
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


class ReceptorLigandInput(RecipeContract):
    sender_receiver_pairs: list[str] = Field(
        ..., description="e.g. 'homeostatic -> activated'"
    )
    lr_pairs: list[str] = Field(..., description="e.g. 'CCL5-CCR5'")
    strength: list[list[float]] = Field(
        ..., description="n_lr × n_sr interaction strength in [0, 1]"
    )
    neg_log10_p: list[list[float]] = Field(
        ..., description="n_lr × n_sr -log10(p-value)"
    )
    title: str = "Ligand-receptor signaling"


def _demo() -> ReceptorLigandInput:
    rng = np.random.default_rng(1123)
    senders_receivers = [
        "homeostatic -> activated",
        "activated -> DAM",
        "homeostatic -> DAM",
        "DAM -> activated",
        "surveillant -> activated",
    ]
    lrs = ["CCL5-CCR5", "CXCL10-CXCR3", "TNF-TNFR1", "CSF1-CSF1R",
           "IL1B-IL1R1", "APOE-LRP1", "CCL3-CCR5"]
    n_lr = len(lrs)
    n_sr = len(senders_receivers)
    strength = rng.uniform(0, 0.6, (n_lr, n_sr))
    # Inject strong hits.
    strength[0, 0] = 0.92
    strength[1, 2] = 0.85
    strength[5, 1] = 0.88
    p_neg = rng.uniform(0.2, 2.5, (n_lr, n_sr))
    p_neg[0, 0] = 5.1
    p_neg[1, 2] = 4.3
    p_neg[5, 1] = 4.8
    return ReceptorLigandInput(
        sender_receiver_pairs=senders_receivers,
        lr_pairs=lrs,
        strength=strength.tolist(),
        neg_log10_p=p_neg.tolist(),
    )


_META = RecipeMetadata(
    name="receptor_ligand_signaling_dotplot",
    modality="single_cell_embeddings",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across sender × receiver cell-type pairs, which ligand-"
        "receptor interactions are enriched?"
    ),
    required_fields=(
        "sender_receiver_pairs", "lr_pairs", "strength", "neg_log10_p",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("expression_dotplot_by_cluster",),
)


@register_recipe(
    metadata=_META,
    contract=ReceptorLigandInput,
    demo_contract=_demo,
)
def render(contract: ReceptorLigandInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    pairs = contract.sender_receiver_pairs
    lrs = contract.lr_pairs
    S = np.asarray(contract.strength, float)
    P = np.asarray(contract.neg_log10_p, float)
    n_lr, n_sr = S.shape

    xs: list[int] = []
    ys: list[int] = []
    sizes: list[float] = []
    colors: list[float] = []
    for li in range(n_lr):
        for si in range(n_sr):
            xs.append(si)
            ys.append(li)
            sizes.append(float(S[li, si]) * 160)
            colors.append(float(P[li, si]))

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    sc = ax.scatter(xs, ys, s=sizes, c=colors, cmap=cmap,
                    edgecolor="white", linewidth=0.4, alpha=0.92, zorder=3)

    ax.set_xticks(range(n_sr))
    ax.set_xticklabels(pairs, rotation=35, ha="right", fontsize=6.4)
    ax.set_yticks(range(n_lr))
    ax.set_yticklabels(lrs, fontsize=6.6)
    ax.invert_yaxis()

    cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.038, pad=0.03)
    cbar.set_label(r"$-\log_{10}(p)$", fontsize=6.8)
    cbar.ax.tick_params(labelsize=6.4)

    # Size legend.
    from matplotlib.lines import Line2D
    size_vals = [0.25, 0.5, 1.0]
    proxies = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#888888", markeredgecolor="white",
               markersize=np.sqrt(v * 160),
               label=f"{smart_fmt(v)}")
        for v in size_vals
    ]
    ax.legend(handles=proxies, loc="center left",
              bbox_to_anchor=(1.20, 0.5),
              fontsize=6.2, frameon=False, handlelength=1.0,
              title="strength", title_fontsize=6.4)

    # Top-interaction callout.
    top_i, top_j = np.unravel_index(int(np.argmax(S * P)), S.shape)
    ax.set_title(
        f"{contract.title}  ·  top: "
        f"{lrs[top_i]} in ({pairs[top_j]})",
        fontsize=8.4, pad=4,
    )
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
