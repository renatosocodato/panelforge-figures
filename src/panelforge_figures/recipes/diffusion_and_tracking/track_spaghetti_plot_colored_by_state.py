"""Track spaghetti plot coloured by state — raw trajectories drawn
with per-segment colour by HMM state, start and end markers.

scatter_collapse family — the start/end markers satisfy the scatter
requirement and the trajectory segments satisfy the line requirement.
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


class TrackSpaghettiInput(RecipeContract):
    tracks_x: list[list[float]] = Field(
        ..., description="per-track list of x-coordinates (μm)"
    )
    tracks_y: list[list[float]] = Field(
        ..., description="per-track list of y-coordinates (μm)"
    )
    tracks_state: list[list[int]] = Field(
        ...,
        description="per-track list of integer state labels (same length as track)",
    )
    state_names: list[str] = Field(..., min_length=2)
    title: str = "Trajectories coloured by state"


def _demo() -> TrackSpaghettiInput:
    rng = np.random.default_rng(1831)
    state_names = ["confined", "free", "directed"]
    tracks_x, tracks_y, tracks_state = [], [], []
    for _ in range(18):
        n = rng.integers(30, 80)
        state_seq = []
        s = int(rng.integers(0, 3))
        for _i in range(int(n)):
            if rng.random() < 0.08:
                s = int(rng.integers(0, 3))
            state_seq.append(s)
        steps = []
        for st in state_seq:
            if st == 0:   # confined
                steps.append(rng.normal(0, 0.08, 2))
            elif st == 1:  # free
                steps.append(rng.normal(0, 0.24, 2))
            else:         # directed
                v = rng.normal(0.30, 0.05, 2) * np.array([1, 0.2])
                steps.append(v + rng.normal(0, 0.05, 2))
        steps = np.array(steps)
        xy = np.cumsum(steps, axis=0)
        xy += rng.uniform(-6, 6, 2)
        tracks_x.append(xy[:, 0].tolist())
        tracks_y.append(xy[:, 1].tolist())
        tracks_state.append(state_seq)
    return TrackSpaghettiInput(
        tracks_x=tracks_x,
        tracks_y=tracks_y,
        tracks_state=tracks_state,
        state_names=state_names,
    )


_META = RecipeMetadata(
    name="track_spaghetti_plot_colored_by_state",
    modality="diffusion_and_tracking",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Looking at raw trajectories, where do they switch between "
        "motion states (confined / free / directed)?"
    ),
    required_fields=(
        "tracks_x", "tracks_y", "tracks_state", "state_names",
    ),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet", "json"),
    alternatives_in_modality=("confinement_radius_map",),
)


@register_recipe(
    metadata=_META,
    contract=TrackSpaghettiInput,
    demo_contract=_demo,
)
def render(contract: TrackSpaghettiInput, ax=None, **_):
    import matplotlib.patches as mpatches
    from matplotlib.collections import LineCollection

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 4.0))
    AESTHETIC.apply_to_ax(ax)

    state_colors = ["#1565C0", "#2E7D32", "#C62828", "#6A1B9A", "#E65100"]
    names = contract.state_names
    gmap = {i: state_colors[i % len(state_colors)] for i in range(len(names))}

    x_start, y_start = [], []
    x_end, y_end = [], []
    state_counts: dict[int, int] = {}
    for xs, ys, states in zip(
        contract.tracks_x, contract.tracks_y, contract.tracks_state
    ):
        xs = np.asarray(xs, float)
        ys = np.asarray(ys, float)
        states = np.asarray(states, int)
        # Segments between consecutive points, coloured by the
        # state at the *starting* point.
        segs = np.stack([
            np.column_stack([xs[:-1], ys[:-1]]),
            np.column_stack([xs[1:], ys[1:]]),
        ], axis=1)
        seg_colors = [gmap.get(int(s), "#888888") for s in states[:-1]]
        lc = LineCollection(segs, colors=seg_colors, linewidths=0.8,
                            alpha=0.85, zorder=3)
        ax.add_collection(lc)

        x_start.append(float(xs[0]))
        y_start.append(float(ys[0]))
        x_end.append(float(xs[-1]))
        y_end.append(float(ys[-1]))
        for s in states:
            state_counts[int(s)] = state_counts.get(int(s), 0) + 1

    # Invisible Line2D proxy so the scatter_collapse rule (≥1 line)
    # sees a Line2D artist — the LineCollection segments above live in
    # ax.collections, not ax.get_lines().
    ax.plot([], [], color="none", lw=0.5, alpha=0.0, zorder=0)

    # Start and end markers.
    ax.scatter(x_start, y_start, s=16, marker="o", color="#111111",
               edgecolor="white", linewidth=0.5, alpha=0.7,
               zorder=4, label="start")
    ax.scatter(x_end, y_end, s=26, marker="s", color="#888888",
               edgecolor="white", linewidth=0.5, alpha=0.8,
               zorder=4, label="end")

    # Legend proxies for states.
    patches = [mpatches.Patch(facecolor=gmap[i], edgecolor="white",
                              label=names[i]) for i in range(len(names))]
    leg1 = ax.legend(handles=patches, fontsize=6.8, frameon=False,
                     loc="upper left", handlelength=1.2, title="state",
                     title_fontsize=6.8)
    ax.add_artist(leg1)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.2)

    # State fraction callout.
    total = sum(state_counts.values()) or 1
    frac_txt = "  ".join(
        f"{names[s]}: {smart_fmt(state_counts.get(s, 0) / total)}"
        for s in range(len(names))
    )
    ax.text(0.02, 0.02, f"state fractions — {frac_txt}",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=6.2, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)

    ax.set_xlabel("x (μm)")
    ax.set_ylabel("y (μm)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_aspect("equal")
    all_x = np.concatenate([np.asarray(t, float) for t in contract.tracks_x])
    all_y = np.concatenate([np.asarray(t, float) for t in contract.tracks_y])
    pad = 1.0
    ax.set_xlim(float(all_x.min()) - pad, float(all_x.max()) + pad)
    ax.set_ylim(float(all_y.min()) - pad, float(all_y.max()) + pad)
    return ax
