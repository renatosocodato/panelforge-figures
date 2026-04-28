"""Panel provenance ledger table — per-panel reproducibility ledger
showing dataset layer, sample composition, support class, and
manuscript status as a coloured matrix table.

Matrix family: >=1 imshow OR >=4 cell patches.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC
from ._shared import PanelProvenanceRow

_SUPPORT_COLOR = {
    "main_inference": "#2E7D32",
    "support_layer": "#26A69A",
    "constraint_layer": "#FB8C00",
    "discovery_layer": "#AB47BC",
    "limitation_only": "#C62828",
}


class PanelProvenanceInput(RecipeContract):
    rows: list[PanelProvenanceRow] = Field(..., min_length=4)
    title: str = "Panel provenance ledger"


def _demo() -> PanelProvenanceInput:
    rng = np.random.default_rng(802)
    rows: list[PanelProvenanceRow] = []
    spec = [
        ("Fig 1A", "main", 15, 393, "main_inference"),
        ("Fig 1C", "main", 12, 120, "main_inference"),
        ("Fig 2A", "main", 8, 191, "main_inference"),
        ("Fig 2J", "main", 15, 200, "constraint_layer"),
        ("Fig 4A", "main", 10, 60, "support_layer"),
        ("Fig 4B", "main", 7, 1431, "support_layer"),
        ("Fig 4D", "main", 15, 15, "discovery_layer"),
        ("Fig 5A", "main", 15, 392, "main_inference"),
        ("Fig 6A", "main", 15, 200, "main_inference"),
        ("Fig S2G", "supp", 15, 200, "support_layer"),
        ("Fig S4D", "supp", 15, 1431, "support_layer"),
        ("Fig S5B", "supp", 15, 11, "limitation_only"),
    ]
    for panel, layer, n_m, n_o, support in spec:
        rows.append(PanelProvenanceRow(
            panel_id=panel, dataset_layer=layer,
            n_mice=int(n_m), n_observations=int(n_o),
            support_class=support,
            manuscript_status="current",
        ))
    _ = rng.normal(0, 0.05, 1)
    return PanelProvenanceInput(rows=rows)


_META = RecipeMetadata(
    name="panel_provenance_ledger_table",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Per panel in a manuscript, what is the dataset layer, "
        "sample composition, and support-class verdict that "
        "documents the panel's epistemic role?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("replication_retrospective_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=PanelProvenanceInput,
    demo_contract=_demo,
)
def render(contract: PanelProvenanceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.rows)
    columns = ["panel", "layer", "n mice", "n obs", "support class"]
    n_cols = len(columns)

    # Background pcolormesh: support_class column gets coloured by
    # tier; other columns stay white.
    X = np.arange(n_cols + 1) - 0.5
    Y = np.arange(n + 1) - 0.5
    bg = np.zeros((n, n_cols))
    mask = np.ones((n, n_cols), dtype=bool)
    mask[:, 4] = False   # support_class column
    # Encode support class as numeric for colormap.
    support_keys = list(_SUPPORT_COLOR)
    support_to_idx = {k: i for i, k in enumerate(support_keys)}
    for i, r in enumerate(contract.rows):
        bg[i, 4] = float(support_to_idx.get(r.support_class, 0))
    bg_masked = np.ma.masked_array(bg, mask=mask)
    from matplotlib.colors import ListedColormap
    support_cmap = ListedColormap([_SUPPORT_COLOR[k] for k in support_keys])
    ax.pcolormesh(X, Y, bg_masked, cmap=support_cmap,
                  vmin=-0.5, vmax=len(support_keys) - 0.5,
                  shading="auto", alpha=0.65, zorder=2)

    # Cell annotations.
    for i, r in enumerate(contract.rows):
        ax.text(0, i, r.panel_id,
                ha="center", va="center", fontsize=6.4,
                color="#222222", fontweight="bold", zorder=4)
        ax.text(1, i, r.dataset_layer,
                ha="center", va="center", fontsize=6.4,
                color="#222222", zorder=4)
        ax.text(2, i, str(r.n_mice),
                ha="center", va="center", fontsize=6.4,
                color="#222222", zorder=4)
        ax.text(3, i, str(r.n_observations),
                ha="center", va="center", fontsize=6.4,
                color="#222222", zorder=4)
        ax.text(4, i, r.support_class.replace("_", " "),
                ha="center", va="center", fontsize=6.4,
                color="white", fontweight="bold", zorder=4)

    ax.set_yticks(range(n))
    ax.set_yticklabels([f"row {i + 1}" for i in range(n)],
                       fontsize=6.0)
    ax.invert_yaxis()
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(columns, fontsize=6.6)
    ax.tick_params(left=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Support-class legend strip below.
    legend_text = "  ·  ".join(
        f"{k.replace('_', ' ')}" for k in support_keys
    )
    ax.text(0.5, -0.10, legend_text,
            transform=ax.transAxes,
            ha="center", va="top", fontsize=6.0,
            color="#666666", style="italic", zorder=4)

    # Tally per support class.
    tally: dict[str, int] = {}
    for r in contract.rows:
        tally[r.support_class] = tally.get(r.support_class, 0) + 1
    bits = "  ".join(
        f"{k.replace('_', ' ')}: {v}" for k, v in tally.items()
    )
    ax.set_title(
        f"{contract.title}  ·  n = {n} panels  ·  {bits}",
        fontsize=8.2, pad=4,
    )
    return ax
