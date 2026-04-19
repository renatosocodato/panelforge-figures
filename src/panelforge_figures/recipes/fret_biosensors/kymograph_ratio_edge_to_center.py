"""Edge-to-centre FRET-ratio kymograph — 1-D spatial × temporal wavefronts."""

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


class EdgeKymoInput(RecipeContract):
    distance_um: list[float] = Field(..., description="distance from cell edge, 0 = edge, μm")
    time_s: list[float] = Field(..., description="time axis in seconds")
    ratio: list[list[float]] = Field(
        ..., description="[n_distance × n_time] array of F_A / F_D"
    )
    edge_velocity_um_s: float | None = Field(
        None, description="propagation velocity of the leading front (overlaid if given)"
    )
    title: str = "Edge-to-centre ratio kymograph"


def _demo() -> EdgeKymoInput:
    rng = np.random.default_rng(609)
    dist = np.linspace(0, 36, 90)
    time = np.linspace(0, 180, 110)
    DD, TT = np.meshgrid(dist, time, indexing="ij")
    # Inward-travelling wave: front speed ~0.35 μm/s, amplitude 0.35 above 1.0,
    # decays into the interior over a length scale λ ≈ 12 μm.
    c = 0.35
    wave = 0.35 * np.exp(-(DD - c * TT) ** 2 / 30.0) * np.exp(-DD / 12.0)
    baseline = 1.00 + 0.03 * np.cos(TT * 0.04)
    ratio = baseline + wave + rng.normal(0, 0.015, DD.shape)
    return EdgeKymoInput(
        distance_um=dist.tolist(),
        time_s=time.tolist(),
        ratio=ratio.tolist(),
        edge_velocity_um_s=c,
    )


_META = RecipeMetadata(
    name="kymograph_ratio_edge_to_center",
    modality="fret_biosensors",
    family=RecipeFamily.heatmap,
    answers_question=(
        "Along a 1-D axis from cell edge to centre, how does the FRET ratio "
        "propagate in time (waves, gradients)?"
    ),
    required_fields=("distance_um", "time_s", "ratio"),
    optional_fields=("edge_velocity_um_s", "title"),
    file_format_hints=("csv", "parquet", "npz"),
    alternatives_in_modality=(
        "ratio_heatmap_over_field",
        "ratio_timecourse_hierarchical_ci",
    ),
)


@register_recipe(
    metadata=_META,
    contract=EdgeKymoInput,
    demo_contract=_demo,
)
def render(contract: EdgeKymoInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    dist = np.asarray(contract.distance_um, dtype=float)
    time = np.asarray(contract.time_s, dtype=float)
    R = np.asarray(contract.ratio, dtype=float)

    # Anchor RdBu_r at the FRET-neutral ratio 1.0 to keep the modality
    # convention stable across recipes.
    anchor = 1.0
    vrange = max(float(np.max(np.abs(R - anchor))), 0.01)
    extent = (float(time.min()), float(time.max()),
              float(dist.max()), float(dist.min()))  # edge at top
    im = ax.imshow(
        R, origin="upper", extent=extent, aspect="auto",
        cmap=AESTHETIC.ratio_cmap or "RdBu_r",
        vmin=anchor - vrange, vmax=anchor + vrange,
        interpolation="bilinear",
    )

    # Optional front-velocity overlay.
    if contract.edge_velocity_um_s is not None:
        c = float(contract.edge_velocity_um_s)
        t_front = np.linspace(float(time.min()), float(time.max()), 60)
        d_front = c * t_front
        mask = (d_front >= dist.min()) & (d_front <= dist.max())
        ax.plot(t_front[mask], d_front[mask], color="#111111",
                lw=1.1, ls="--", zorder=4,
                label=rf"front $v$ = {smart_fmt(c)} $\mu$m / s")
        ax.legend(fontsize=6.4, frameon=False, loc="upper right",
                  handlelength=1.8)

    # Reference: time of peak along the edge (row 0).
    edge_row = R[0]
    t_peak_edge = float(time[int(np.argmax(edge_row))])
    ax.scatter([t_peak_edge], [float(dist.min())], s=32,
               facecolor="none", edgecolor="#111111",
               linewidth=1.1, zorder=5)

    ax.set_xlabel("time (s)")
    ax.set_ylabel(r"distance from edge ($\mu$m)")
    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label(r"F$_A$/F$_D$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)
    ax.set_title(
        f"{contract.title}  ·  "
        f"range {smart_fmt(float(R.min()))}-{smart_fmt(float(R.max()))}",
        fontsize=8.6, pad=4,
    )
    return ax
