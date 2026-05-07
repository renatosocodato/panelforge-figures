"""Transition matrix diagonal-dominance callout — variant of
`state_transition_kernel_matrix` that adds a per-state diagonal-
dominance score callout (A[i,i] - max(A[i,j!=i])) with permutation
p-values.

Renders the N × N transition kernel as a cividis `imshow` (matching
the base recipe's encoding) plus a vertical right-margin lollipop
callout per state showing the dominance score; sticky states (above
the manuscript threshold) are highlighted in teal.

Matrix family: >=1 imshow OR >=4 cell patches. Satisfied by the
`imshow` of the N×N kernel.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import DecodedStateSeries, DiagonalDominanceSummary


class TransitionMatrixDDCalloutInput(RecipeContract):
    decoded: list[DecodedStateSeries] = Field(..., min_length=1)
    states: list[str] = Field(..., min_length=2)
    dominance: list[DiagonalDominanceSummary] = Field(..., min_length=2)
    decoder_label: str = "HMM"
    title: str = "Transition kernel + diagonal-dominance callout"


def _demo() -> TransitionMatrixDDCalloutInput:
    rng = np.random.default_rng(834)
    states = ["homeostatic", "surveillant", "activated"]
    n_t = 360
    # Sticky chain — manuscript F2H values: mean diagonal ≈ 0.82,
    # off-diagonal max surveillant→activated 0.09.
    A_truth = np.array([
        [0.85, 0.10, 0.05],
        [0.06, 0.85, 0.09],
        [0.04, 0.05, 0.91],
    ])
    state_idx = 0
    seq: list[str] = []
    for _ in range(n_t):
        nxt = rng.choice(3, p=A_truth[state_idx])
        seq.append(states[nxt])
        state_idx = nxt
    decoded = [DecodedStateSeries(
        cell_id="C00",
        t_s=list(range(n_t)),
        state=seq,
        decoder="HMM",
    )]
    # Dominance scores: diagonal − max(off-diagonal) per row.
    dominance = []
    for i, s in enumerate(states):
        diag = A_truth[i, i]
        off_max = float(np.max(np.delete(A_truth[i], i)))
        score = float(diag - off_max)
        dominance.append(DiagonalDominanceSummary(
            state=s,
            dominance_score=score,
            p_perm=0.001 + 0.002 * (1 - score),
            is_dominant=score > 0.50,
        ))
    return TransitionMatrixDDCalloutInput(
        decoded=decoded, states=states, dominance=dominance,
    )


_META = RecipeMetadata(
    name="transition_matrix_diagonal_dominance_callout",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "What are the per-step transition probabilities between "
        "decoded latent states, and which states are statistically "
        "sticky (large diagonal-vs-off-diagonal margin)?"
    ),
    required_fields=("decoded", "states", "dominance"),
    optional_fields=("decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("state_transition_kernel_matrix",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=TransitionMatrixDDCalloutInput,
    demo_contract=_demo,
)
def render(contract: TransitionMatrixDDCalloutInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.2))
    AESTHETIC.apply_to_ax(ax)

    n_states = len(contract.states)
    state_to_idx = {s: i for i, s in enumerate(contract.states)}

    # Estimate kernel from decoded series.
    counts = np.zeros((n_states, n_states), float)
    for d in contract.decoded:
        for prev, nxt in zip(d.state[:-1], d.state[1:]):
            if prev in state_to_idx and nxt in state_to_idx:
                counts[state_to_idx[prev], state_to_idx[nxt]] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    matrix = np.divide(counts, np.maximum(row_sums, 1.0))

    # imshow (the matrix-family-rule satisfier).
    im = ax.imshow(matrix, cmap="cividis", vmin=0, vmax=1.0,
                   aspect="equal", zorder=2)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("P(next | current)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Cell numeric annotations.
    for i in range(n_states):
        for j in range(n_states):
            v = matrix[i, j]
            text_colour = "white" if v < 0.5 else "#222222"
            ax.text(j, i, smart_fmt(v),
                    ha="center", va="center", fontsize=6.6,
                    color=text_colour, fontweight="bold")

    # Highlight diagonal cells of dominant states with a teal border.
    dom_by_state = {d.state: d for d in contract.dominance}
    for i, s in enumerate(contract.states):
        d = dom_by_state.get(s)
        if d is None or not d.is_dominant:
            continue
        # Inset border around the diagonal cell.
        from matplotlib.patches import Rectangle
        ax.add_patch(Rectangle(
            (i - 0.48, i - 0.48), 0.96, 0.96,
            facecolor="none", edgecolor="#26A69A",
            linewidth=1.4, zorder=5,
        ))

    slugs = [s[:4] if len(s) > 4 else s for s in contract.states]
    ax.set_xticks(range(n_states))
    ax.set_xticklabels(slugs, fontsize=7.0)
    ax.set_yticks(range(n_states))
    ax.set_yticklabels(slugs, fontsize=7.0)
    ax.set_xlabel("next state")
    ax.set_ylabel("current state")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Title: per-state dominance score summary.
    parts = []
    for d in contract.dominance:
        flag = " [dom.]" if d.is_dominant else ""
        parts.append(f"{d.state[:4]} = {smart_fmt(d.dominance_score)}{flag}")
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        + "  ·  ".join(parts),
        fontsize=7.4, pad=4,
    )
    return ax
