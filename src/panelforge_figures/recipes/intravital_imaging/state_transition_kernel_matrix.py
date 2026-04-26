"""State transition kernel matrix — N × N heatmap of P(next-state |
current-state), with off-diagonal emphasis.

Two kernel modes: `A_full` (HMM-style per-step A matrix) or
`embedded_chain` (HSMM-style given-a-switch transition kernel,
which masks the diagonal).

Matrix family: >=4 cell patches OR >=1 imshow. Satisfied by
`imshow` of the N×N matrix.
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
from ._shared import DecodedStateSeries


class StateTransitionKernelInput(RecipeContract):
    decoded: list[DecodedStateSeries] = Field(..., min_length=1)
    states: list[str] = Field(..., min_length=2)
    kernel: str = Field(
        "A_full",
        description="'A_full' (HMM A matrix) | 'embedded_chain' (HSMM)",
    )
    decoder_label: str = "HMM"
    title: str = "State transition kernel"


def _demo() -> StateTransitionKernelInput:
    rng = np.random.default_rng(2741)
    states = ["homeostatic", "surveillant", "activated"]
    n_t = 240
    # Generate from a sticky chain with weak off-diagonal asymmetry.
    A_truth = np.array([
        [0.92, 0.06, 0.02],
        [0.05, 0.90, 0.05],
        [0.04, 0.04, 0.92],
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
    return StateTransitionKernelInput(
        decoded=decoded,
        states=states,
    )


_META = RecipeMetadata(
    name="state_transition_kernel_matrix",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "What are the per-step (or per-switch) transition probabilities "
        "between decoded latent states?"
    ),
    required_fields=("decoded", "states"),
    optional_fields=("kernel", "decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("state_occupancy_stacked_area",),
)


@register_recipe(
    metadata=_META,
    contract=StateTransitionKernelInput,
    demo_contract=_demo,
)
def render(contract: StateTransitionKernelInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.2))
    AESTHETIC.apply_to_ax(ax)

    n_states = len(contract.states)
    state_to_idx = {s: i for i, s in enumerate(contract.states)}

    # Count transitions across all decoded series.
    counts = np.zeros((n_states, n_states), float)
    for d in contract.decoded:
        for prev, nxt in zip(d.state[:-1], d.state[1:]):
            if prev in state_to_idx and nxt in state_to_idx:
                if contract.kernel == "embedded_chain" and prev == nxt:
                    continue
                counts[state_to_idx[prev], state_to_idx[nxt]] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    matrix = np.divide(counts, np.maximum(row_sums, 1.0))

    # Use cividis for the heatmap (modern, perceptually uniform).
    im = ax.imshow(matrix, cmap="cividis", vmin=0, vmax=1.0,
                   aspect="equal", zorder=2)
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("P(next | current)", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Cell annotations.
    for i in range(n_states):
        for j in range(n_states):
            v = matrix[i, j]
            text_colour = "white" if v < 0.5 else "#222222"
            ax.text(j, i, smart_fmt(v),
                    ha="center", va="center",
                    fontsize=6.6, color=text_colour, fontweight="bold")

    # 4-letter slugs for tick labels (so e.g. "homeostatic" doesn't
    # collide with the cell numerics).
    slugs = [s[:4] if len(s) > 4 else s for s in contract.states]
    ax.set_xticks(range(n_states))
    ax.set_xticklabels(slugs, fontsize=7.0)
    ax.set_yticks(range(n_states))
    ax.set_yticklabels(slugs, fontsize=7.0)
    ax.set_xlabel("next state")
    ax.set_ylabel("current state")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Verdict footer: stickiness (mean diagonal) + most-likely
    # off-diagonal transition.
    diag_mean = float(np.mean(np.diag(matrix))) if contract.kernel == "A_full" \
        else float("nan")
    off_diag = matrix.copy()
    np.fill_diagonal(off_diag, 0.0)
    if off_diag.max() > 0:
        i_max, j_max = np.unravel_index(np.argmax(off_diag), off_diag.shape)
        top_off_text = (f"top off-diag: "
                        f"{contract.states[i_max]}->"
                        f"{contract.states[j_max]} = "
                        f"{smart_fmt(float(off_diag[i_max, j_max]))}")
    else:
        top_off_text = ""

    bits = []
    if contract.kernel == "A_full":
        bits.append(f"mean diag = {smart_fmt(diag_mean)}")
    bits.append(top_off_text)
    bits.append(f"kernel: {contract.kernel}")
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        + "  ·  ".join(b for b in bits if b),
        fontsize=7.4, pad=4,
    )
    return ax
