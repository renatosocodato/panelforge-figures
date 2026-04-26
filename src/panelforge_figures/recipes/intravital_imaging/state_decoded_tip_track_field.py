"""State-decoded tip-track field — per-tip XY trajectories with
segments coloured by HMM/HSMM-decoded state.

Differs from the alpha `cell_track_trajectory_field` (where states
are inline metadata): here the decoded segments come from a separate
`DecodedStateSeries` time-aligned with each tip's trajectory, and
state colour mapping uses the registered `microglia_states` palette
via `_demo_state_palette`.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the per-tip scatter + an invisible-proxy line (the LineCollection
segments live on `ax.collections`, not `ax.get_lines()`).
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
from ._shared import DecodedStateSeries, TipTrack, _demo_state_palette


class StateDecodedTipTrackInput(RecipeContract):
    tip_tracks: list[TipTrack] = Field(..., min_length=2)
    decoded: list[DecodedStateSeries] = Field(..., min_length=2)
    extent_um: tuple[float, float, float, float] | None = None
    decoder_label: str = "HMM"
    show_endpoints: bool = True
    title: str = "State-decoded tip tracks"


def _demo() -> StateDecodedTipTrackInput:
    rng = np.random.default_rng(2611)
    states = ["homeostatic", "surveillant", "activated"]
    step_by_state = {
        "homeostatic": 0.4,
        "surveillant": 1.1,
        "activated":   2.6,
    }
    tip_tracks: list[TipTrack] = []
    decoded: list[DecodedStateSeries] = []
    for k in range(6):
        n = 60
        # Decoded state series: sticky chain.
        seq: list[str] = []
        s = states[rng.integers(0, 3)]
        for _ in range(n):
            if rng.random() < 0.05:
                s = states[rng.integers(0, 3)]
            seq.append(s)
        # Tip XY: random walk with state-dependent step size.
        x = np.zeros(n)
        y = np.zeros(n)
        x[0] = rng.uniform(-30, 30)
        y[0] = rng.uniform(-30, 30)
        for t in range(1, n):
            sigma = step_by_state[seq[t]]
            x[t] = x[t-1] + rng.normal(0, sigma)
            y[t] = y[t-1] + rng.normal(0, sigma)
        tip_tracks.append(TipTrack(
            tip_id=f"T{k:02d}",
            x_um=x.tolist(),
            y_um=y.tolist(),
            t_s=list(range(n)),
            parent_cell_id=f"C{k:02d}",
        ))
        decoded.append(DecodedStateSeries(
            cell_id=f"C{k:02d}",
            t_s=list(range(n)),
            state=seq,
            decoder="HMM",
        ))
    return StateDecodedTipTrackInput(
        tip_tracks=tip_tracks,
        decoded=decoded,
    )


_META = RecipeMetadata(
    name="state_decoded_tip_track_field",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Where do tips travel, and how do their decoded latent states "
        "map onto the spatial trajectory?"
    ),
    required_fields=("tip_tracks", "decoded"),
    optional_fields=(
        "extent_um", "decoder_label", "show_endpoints", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(
    metadata=_META,
    contract=StateDecodedTipTrackInput,
    demo_contract=_demo,
)
def render(contract: StateDecodedTipTrackInput, ax=None, **_):
    from matplotlib.collections import LineCollection
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.8))
    AESTHETIC.apply_to_ax(ax)

    decoded_by_cell = {d.cell_id: d for d in contract.decoded}
    # Collect all states for palette mapping.
    all_states: list[str] = []
    for d in contract.decoded:
        for s in d.state:
            if s not in all_states:
                all_states.append(s)
    palette = _demo_state_palette(all_states)

    # Invisible-proxy line so scatter_collapse's ≥1-line rule sees
    # something on ax.get_lines() (LineCollection lives on
    # ax.collections, which the rule doesn't count).
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)

    for track in contract.tip_tracks:
        x = np.asarray(track.x_um, float)
        y = np.asarray(track.y_um, float)
        if track.parent_cell_id is None:
            colours_per_seg = ["#888888"] * (len(x) - 1)
        else:
            d = decoded_by_cell.get(track.parent_cell_id)
            if d is None:
                colours_per_seg = ["#888888"] * (len(x) - 1)
            else:
                # Match decoded state at each tip frame (assumes equal
                # length; truncate if mismatched).
                n_seg = min(len(x), len(d.state)) - 1
                colours_per_seg = [
                    palette.get(d.state[t], "#888888")
                    for t in range(n_seg)
                ]
        # Build segments.
        n_seg = len(colours_per_seg)
        segs = np.array([
            [(x[t], y[t]), (x[t+1], y[t+1])]
            for t in range(n_seg)
        ])
        lc = LineCollection(segs, colors=colours_per_seg, lw=1.0,
                            alpha=0.85, zorder=4)
        ax.add_collection(lc)
        # Scatter at every frame (low alpha) + endpoints in high alpha.
        ax.scatter(x, y, s=6, c="#444444", alpha=0.3, zorder=3,
                   linewidths=0)
        if contract.show_endpoints:
            ax.scatter([x[0]], [y[0]], s=20, marker="o",
                       facecolor="white", edgecolor="#222222",
                       linewidth=0.6, zorder=6)
            ax.scatter([x[-1]], [y[-1]], s=20, marker="s",
                       facecolor="#222222", edgecolor="white",
                       linewidth=0.6, zorder=6)

    if contract.extent_um:
        x0, x1, y0, y1 = contract.extent_um
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Scale bar (20 um).
    x_lo, x_hi = ax.get_xlim()
    y_lo, y_hi = ax.get_ylim()
    bar_len = 20.0
    bar_x = x_hi - (x_hi - x_lo) * 0.06 - bar_len
    bar_y = y_lo + (y_hi - y_lo) * 0.06
    ax.plot([bar_x, bar_x + bar_len], [bar_y, bar_y],
            color="#222222", lw=2.2, zorder=7)
    ax.text(bar_x + bar_len / 2, bar_y - (y_hi - y_lo) * 0.025,
            "20 um", ha="center", va="top", fontsize=6.4,
            color="#222222")

    # Legend (states + endpoints).
    from matplotlib.lines import Line2D
    handles = []
    for s in all_states:
        handles.append(Line2D([0], [0], marker="o", color="none",
                              markerfacecolor=palette[s],
                              markeredgecolor="white", markersize=6,
                              label=s))
    if contract.show_endpoints:
        handles.append(Line2D([0], [0], marker="o", color="none",
                              markerfacecolor="white",
                              markeredgecolor="#222222", markersize=5,
                              label="start"))
        handles.append(Line2D([0], [0], marker="s", color="none",
                              markerfacecolor="#222222",
                              markeredgecolor="white", markersize=5,
                              label="end"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=len(handles), handlelength=1.0)

    n_tracks = len(contract.tip_tracks)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"{n_tracks} tracks  ·  {len(all_states)} states",
        fontsize=8.4, pad=4,
    )
    return ax
