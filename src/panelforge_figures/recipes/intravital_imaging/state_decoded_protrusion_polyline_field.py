"""State-decoded protrusion polyline field — per-protrusion polyline
overlays coloured by their parent cell's decoded state at the
polyline's timestamp.

Distinct from A.1 in that the graphical atom is a curve of arbitrary
length (a polyline), not a tip path. Useful for protrusion shape
heterogeneity visualisations.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
endpoint-marker scatter + an invisible-proxy line.
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
from ._shared import (
    DecodedStateSeries,
    ProtrusionPolylineWithTime,
    _demo_state_palette,
)


class StateDecodedPolylineFieldInput(RecipeContract):
    polylines: list[ProtrusionPolylineWithTime] = Field(..., min_length=3)
    decoded: list[DecodedStateSeries] = Field(..., min_length=2)
    extent_um: tuple[float, float, float, float] | None = None
    show_endpoints: bool = True
    decoder_label: str = "HMM"
    title: str = "State-decoded protrusion polylines"


def _demo() -> StateDecodedPolylineFieldInput:
    rng = np.random.default_rng(2613)
    states = ["homeostatic", "surveillant", "activated"]
    cells = [f"C{k:02d}" for k in range(4)]
    decoded: list[DecodedStateSeries] = []
    polylines: list[ProtrusionPolylineWithTime] = []
    for cell in cells:
        n = 30
        seq = [states[rng.integers(0, 3)] for _ in range(n)]
        decoded.append(DecodedStateSeries(
            cell_id=cell,
            t_s=list(range(n)),
            state=seq,
            decoder="HMM",
        ))
        # 2 protrusions per cell, each observed at 8 timepoints.
        for p in range(2):
            origin = np.array([rng.uniform(-25, 25), rng.uniform(-25, 25)])
            theta = rng.uniform(0, 2 * np.pi)
            t_obs = sorted(rng.choice(range(n), 8, replace=False).tolist())
            xy_per_t: list[list[list[float]]] = []
            for t in t_obs:
                length = 4 + 0.4 * t + rng.normal(0, 0.6)
                # 12-point arc.
                arc_th = np.linspace(theta - 0.35, theta + 0.35, 12)
                xs = origin[0] + np.cos(arc_th) * np.linspace(0, length, 12)
                ys = origin[1] + np.sin(arc_th) * np.linspace(0, length, 12)
                xy_per_t.append([[float(a), float(b)]
                                 for a, b in zip(xs, ys)])
            polylines.append(ProtrusionPolylineWithTime(
                protrusion_id=f"{cell}_p{p}",
                parent_cell_id=cell,
                t_s=[float(t) for t in t_obs],
                polyline_xy_um_per_t=xy_per_t,
            ))
    return StateDecodedPolylineFieldInput(
        polylines=polylines,
        decoded=decoded,
    )


_META = RecipeMetadata(
    name="state_decoded_protrusion_polyline_field",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "How do protrusion shapes (polylines of arbitrary length) "
        "differ across decoded latent states?"
    ),
    required_fields=("polylines", "decoded"),
    optional_fields=(
        "extent_um", "show_endpoints", "decoder_label", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("state_decoded_tip_track_field",),
)


@register_recipe(
    metadata=_META,
    contract=StateDecodedPolylineFieldInput,
    demo_contract=_demo,
)
def render(contract: StateDecodedPolylineFieldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.8))
    AESTHETIC.apply_to_ax(ax)

    decoded_by_cell = {d.cell_id: d for d in contract.decoded}
    all_states: list[str] = []
    for d in contract.decoded:
        for s in d.state:
            if s not in all_states:
                all_states.append(s)
    palette = _demo_state_palette(all_states)

    # Invisible-proxy line for scatter_collapse rule.
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)

    for poly in contract.polylines:
        d = decoded_by_cell.get(poly.parent_cell_id)
        for t_obs, xy_at_t in zip(poly.t_s, poly.polyline_xy_um_per_t):
            arr = np.asarray(xy_at_t, float)
            # State at this protrusion timepoint.
            if d is None:
                colour = "#888888"
            else:
                t_idx = int(min(round(t_obs), len(d.state) - 1))
                colour = palette.get(d.state[t_idx], "#888888")
            ax.plot(arr[:, 0], arr[:, 1],
                    color=colour, lw=0.9, alpha=0.55, zorder=3)
            if contract.show_endpoints:
                ax.scatter([arr[-1, 0]], [arr[-1, 1]], s=10,
                           color=colour, edgecolor="white",
                           linewidth=0.4, zorder=5)

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

    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=palette[s], lw=1.4, label=s)
               for s in all_states]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=len(all_states), handlelength=1.4)

    n_proto = len(contract.polylines)
    ax.set_title(
        f"{contract.title}  ·  {contract.decoder_label}  ·  "
        f"{n_proto} protrusions  ·  {len(all_states)} states",
        fontsize=8.4, pad=4,
    )
    return ax
