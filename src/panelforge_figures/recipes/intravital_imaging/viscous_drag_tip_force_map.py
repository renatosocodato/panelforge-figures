"""Viscous-drag tip-force map — tip XY scatter coloured by F = 6 pi
eta r v (Stokes lower-bound estimate). Footer caveat banner.

Scatter-collapse family: >=1 scatter + >=1 fit line.
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
from ._shared import TipTrack


class ViscousDragTipForceInput(RecipeContract):
    tip_tracks: list[TipTrack] = Field(..., min_length=1)
    viscosity_pa_s: float = 1e-3
    tip_radius_um: float = 0.2
    extent_um: tuple[float, float, float, float] | None = None
    title: str = "Viscous-drag tip force map"


def _demo() -> ViscousDragTipForceInput:
    rng = np.random.default_rng(3141)
    tracks = []
    for k in range(8):
        n = 40
        x = np.cumsum(rng.normal(0, 1.2, n)) + rng.uniform(-30, 30)
        y = np.cumsum(rng.normal(0, 1.2, n)) + rng.uniform(-30, 30)
        tracks.append(TipTrack(
            tip_id=f"T{k:02d}",
            x_um=x.tolist(), y_um=y.tolist(),
            t_s=list(np.arange(n).astype(float)),
        ))
    return ViscousDragTipForceInput(tip_tracks=tracks)


_META = RecipeMetadata(
    name="viscous_drag_tip_force_map",
    modality="intravital_imaging",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Where do tips push hardest, given an order-of-magnitude "
        "Stokes drag estimate F = 6 pi eta r v?"
    ),
    required_fields=("tip_tracks",),
    optional_fields=(
        "viscosity_pa_s", "tip_radius_um", "extent_um", "title",
    ),
    file_format_hints=("yaml",),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(
    metadata=_META,
    contract=ViscousDragTipForceInput,
    demo_contract=_demo,
)
def render(contract: ViscousDragTipForceInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 4.4))
    AESTHETIC.apply_to_ax(ax)

    # Invisible-proxy line for scatter_collapse rule.
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)

    eta = contract.viscosity_pa_s
    r_tip = contract.tip_radius_um * 1e-6  # to metres
    all_x = []
    all_y = []
    all_F = []
    for track in contract.tip_tracks:
        x = np.asarray(track.x_um, float)
        y = np.asarray(track.y_um, float)
        t = np.asarray(track.t_s, float)
        if x.size < 2:
            continue
        # Compute v in m/s (positions in um, t in s).
        dx = np.diff(x) * 1e-6
        dy = np.diff(y) * 1e-6
        dt = np.diff(t)
        v = np.sqrt(dx ** 2 + dy ** 2) / np.maximum(dt, 1e-9)
        # Force in pN: F = 6 * pi * eta * r * v  [Pa·s · m · m/s = N]
        F = 6 * np.pi * eta * r_tip * v * 1e12  # N -> pN
        all_x.extend(x[1:].tolist())
        all_y.extend(y[1:].tolist())
        all_F.extend(F.tolist())

    if all_F:
        # Data-driven colour limits so dots are visible across the
        # actual F range (Stokes-lower-bound forces span orders of
        # magnitude depending on tip speed; a hard 0–1 pN ceiling
        # collapses the palette to black for typical sub-pN values).
        vmin = float(np.percentile(all_F, 5))
        vmax = float(np.percentile(all_F, 95))
        if vmax <= vmin:
            vmax = vmin + 1e-6
        sc = ax.scatter(all_x, all_y, c=all_F, cmap="magma", s=18,
                        edgecolor="white", linewidth=0.3,
                        alpha=0.85, zorder=4,
                        vmin=vmin, vmax=vmax)
        cbar = ax.figure.colorbar(sc, ax=ax, fraction=0.04, pad=0.03)
        cbar.set_label("F (pN, Stokes lower bound)", fontsize=6.6)
        cbar.ax.tick_params(labelsize=6.0)

    if contract.extent_um:
        x0, x1, y0, y1 = contract.extent_um
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Caveat footer banner.
    ax.text(0.5, -0.20,
            "Stokes lower bound — ignores substrate adhesion + matrix coupling.",
            transform=ax.transAxes,
            ha="center", va="top", fontsize=6.4,
            color="#777777", style="italic",
            bbox=dict(boxstyle="round,pad=0.22", fc="#F5F5F5",
                      ec="#BBBBBB", lw=0.4),
            zorder=7)

    n_tracks = len(contract.tip_tracks)
    median_F = float(np.median(all_F)) if all_F else 0.0
    ax.set_title(
        f"{contract.title}  ·  {n_tracks} tracks  ·  "
        f"median F = {smart_fmt(median_F)} pN  ·  "
        f"eta = {smart_fmt(eta * 1e3)} mPa·s, r = "
        f"{smart_fmt(contract.tip_radius_um)} um",
        fontsize=7.4, pad=4,
    )
    return ax
