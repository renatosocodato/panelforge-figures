"""Study × replication-attempt matrix — per-cell success / failure
with ES magnitude overlay.
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


class ReplicationMatrixInput(RecipeContract):
    study_names: list[str] = Field(..., min_length=3)
    attempt_names: list[str] = Field(..., min_length=2)
    status_matrix: list[list[str]] = Field(
        ...,
        description=(
            "n_studies × n_attempts cells, each 'success' / 'failure' "
            "/ 'partial' / 'na'"
        ),
    )
    effect_size_matrix: list[list[float]] | None = Field(
        None,
        description="optional per-cell effect size to overlay as text",
    )
    title: str = "Replication retrospective"


def _demo() -> ReplicationMatrixInput:
    rng = np.random.default_rng(631)
    studies = [f"Study {i + 1}" for i in range(8)]
    attempts = ["Direct", "Conceptual", "Registered"]
    statuses = np.empty((len(studies), len(attempts)), dtype=object)
    es = np.empty_like(statuses, dtype=float)
    cats = ["success", "failure", "partial", "na"]
    probs = [0.45, 0.30, 0.18, 0.07]
    for i in range(len(studies)):
        for j in range(len(attempts)):
            s = rng.choice(cats, p=probs)
            statuses[i, j] = s
            if s == "na":
                es[i, j] = np.nan
            elif s == "failure":
                es[i, j] = rng.uniform(-0.1, 0.15)
            elif s == "partial":
                es[i, j] = rng.uniform(0.15, 0.35)
            else:
                es[i, j] = rng.uniform(0.35, 0.80)
    return ReplicationMatrixInput(
        study_names=studies,
        attempt_names=attempts,
        status_matrix=statuses.tolist(),
        effect_size_matrix=es.tolist(),
    )


_META = RecipeMetadata(
    name="replication_retrospective_matrix",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across study × replication attempt, which attempts succeeded "
        "and by how much (effect size)?"
    ),
    required_fields=("study_names", "attempt_names", "status_matrix"),
    optional_fields=("effect_size_matrix", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("reproducibility_correlogram",),
)


@register_recipe(
    metadata=_META,
    contract=ReplicationMatrixInput,
    demo_contract=_demo,
)
def render(contract: ReplicationMatrixInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.0))
    AESTHETIC.apply_to_ax(ax)

    studies = contract.study_names
    attempts = contract.attempt_names
    S = np.asarray(contract.status_matrix, object)
    n_s, n_a = S.shape
    ES = (np.asarray(contract.effect_size_matrix, float)
          if contract.effect_size_matrix is not None
          else np.full((n_s, n_a), np.nan))

    status_colors = {
        "success":  "#2E7D32",
        "partial":  "#F9A825",
        "failure":  "#C62828",
        "na":       "#CFD8DC",
    }

    # Paint each cell as a Rectangle.
    for i in range(n_s):
        for j in range(n_a):
            status = str(S[i, j])
            color = status_colors.get(status, "#CFD8DC")
            ax.add_patch(mpatches.Rectangle(
                (j, n_s - 1 - i), 1, 1,
                facecolor=color, edgecolor="white", linewidth=0.8,
                alpha=0.90, zorder=2,
            ))
            # ES numeric overlay.
            if status != "na" and not np.isnan(ES[i, j]):
                es = float(ES[i, j])
                ax.text(j + 0.5, n_s - 1 - i + 0.5,
                        smart_fmt(es),
                        ha="center", va="center", fontsize=7.0,
                        color=("white" if status != "partial" else "#222222"),
                        fontweight="bold", zorder=4)

    ax.set_xlim(0, n_a)
    ax.set_ylim(0, n_s)
    ax.set_xticks(np.arange(n_a) + 0.5)
    ax.set_xticklabels(attempts, fontsize=7.0)
    ax.set_yticks(np.arange(n_s) + 0.5)
    ax.set_yticklabels(studies[::-1], fontsize=7.0)
    ax.set_xlabel("replication attempt")

    # Success-rate summary baked into title to avoid colliding with
    # the title line or with cell labels.
    flat = S.ravel()
    n_success = int((flat == "success").sum())
    n_partial = int((flat == "partial").sum())
    n_fail = int((flat == "failure").sum())
    total = n_success + n_partial + n_fail
    success_rate = (n_success + 0.5 * n_partial) / max(total, 1)
    ax.set_title(
        f"{contract.title}  ·  weighted success "
        f"{smart_fmt(success_rate * 100)} %   "
        f"(S {n_success} · P {n_partial} · F {n_fail})",
        fontsize=8.2, pad=4,
    )

    # Legend below axes, with extra vertical offset so the x-tick
    # labels stay clear.
    legend_patches = [
        mpatches.Patch(facecolor=status_colors[k], edgecolor="white",
                       label=k)
        for k in ["success", "partial", "failure", "na"]
    ]
    ax.legend(handles=legend_patches, fontsize=6.8, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=4, handlelength=1.0)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return ax
