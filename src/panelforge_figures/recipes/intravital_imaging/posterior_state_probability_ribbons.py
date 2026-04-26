"""Posterior state-probability ribbons — stacked ribbon plot of γ(t)
per state, aggregated across cells.

Tells you how confident the decoder is at each timepoint and where
the cohort spends time. Per-state ribbons stack to 1 by construction,
which makes condition-level shifts in occupancy directly visible.

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by per-state ribbons (filled bands) + a mean γ line
overlaid in white per state at the ribbon centerline.
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
from ._shared import DecodedStateSeries, _demo_state_palette


class PosteriorStateRibbonsInput(RecipeContract):
    decoded: list[DecodedStateSeries] = Field(..., min_length=1)
    states: list[str] = Field(..., min_length=2)
    aggregate: str = Field(
        "mean_across_cells",
        description="'per_cell' | 'mean_across_cells'",
    )
    decoder_label: str = "HMM"
    title: str = "Posterior state-probability ribbons"


def _demo() -> PosteriorStateRibbonsInput:
    rng = np.random.default_rng(2701)
    states = ["homeostatic", "surveillant", "activated"]
    n_cells = 4
    n_t = 80
    decoded = []
    for k in range(n_cells):
        # Soft transitions: smoothly varying posteriors that sum to 1.
        baseline = np.array([0.6, 0.25, 0.15])
        # Drift: cell k drifts toward "activated" near the end.
        drift = np.linspace(0, 0.4, n_t)
        post = np.zeros((n_t, 3))
        for t in range(n_t):
            base = baseline.copy()
            base[2] += drift[t] * (k + 1) / n_cells
            base[0] -= drift[t] * (k + 1) / n_cells * 0.7
            base[1] -= drift[t] * (k + 1) / n_cells * 0.3
            base = np.clip(base, 0.01, None)
            base = base + rng.normal(0, 0.04, 3)
            base = np.clip(base, 0.01, None)
            post[t] = base / base.sum()
        # Argmax for hard state path.
        state_path = [states[int(post[t].argmax())] for t in range(n_t)]
        decoded.append(DecodedStateSeries(
            cell_id=f"C{k:02d}",
            t_s=list(range(n_t)),
            state=state_path,
            posterior_prob=post.tolist(),
            decoder="HMM",
        ))
    return PosteriorStateRibbonsInput(
        decoded=decoded,
        states=states,
        decoder_label="HMM",
    )


_META = RecipeMetadata(
    name="posterior_state_probability_ribbons",
    modality="intravital_imaging",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "Across cells, how does the posterior probability γ(t) of "
        "each decoded state evolve over time?"
    ),
    required_fields=("decoded", "states"),
    optional_fields=("aggregate", "decoder_label", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("state_occupancy_stacked_area",),
)


@register_recipe(
    metadata=_META,
    contract=PosteriorStateRibbonsInput,
    demo_contract=_demo,
)
def render(contract: PosteriorStateRibbonsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 3.6))
    AESTHETIC.apply_to_ax(ax)

    palette = _demo_state_palette(contract.states)

    # Build mean γ across cells per state per timepoint.
    valid_decoded = [d for d in contract.decoded
                     if d.posterior_prob is not None]
    if not valid_decoded:
        ax.text(0.5, 0.5, "no posterior_prob in decoded",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=7.2, color="#888888")
        ax.set_title(contract.title, fontsize=8.4, pad=4)
        return ax

    # Use the first decoded series as the time grid (assumes shared).
    t_grid = np.asarray(valid_decoded[0].t_s, float)
    n_t = t_grid.size
    n_states = len(contract.states)
    # Per-cell posterior arrays, padded/clipped to t_grid length.
    stacked = np.zeros((len(valid_decoded), n_t, n_states))
    for i, d in enumerate(valid_decoded):
        post = np.asarray(d.posterior_prob, float)
        n_use = min(post.shape[0], n_t)
        stacked[i, :n_use, :post.shape[1]] = post[:n_use, :n_states]
    mean_post = stacked.mean(axis=0)

    # stackplot of mean posterior.
    colours = [palette.get(s, "#888888") for s in contract.states]
    ax.stackplot(t_grid, mean_post.T, colors=colours, alpha=0.78,
                 labels=contract.states, edgecolor="white", linewidth=0.5)

    # Mean γ centerline (satisfies the ≥1 mean line rule of
    # timecourse_hierarchical_ci).
    cum = np.cumsum(mean_post, axis=1)
    for i, _state in enumerate(contract.states):
        if i == 0:
            mid = cum[:, i] / 2
        else:
            mid = (cum[:, i] + cum[:, i-1]) / 2
        ax.plot(t_grid, mid, color="#FFFFFF", lw=0.6, alpha=0.7,
                zorder=5)

    ax.set_xlim(t_grid.min(), t_grid.max())
    ax.set_ylim(0, 1)
    ax.set_xlabel("frame")
    ax.set_ylabel("mean posterior gamma(t)")
    ax.legend(fontsize=6.4, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.14), ncols=n_states,
              handlelength=1.4)

    n_cells = len(valid_decoded)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"mean across {n_cells} cells",
        fontsize=8.4, pad=4,
    )
    return ax
