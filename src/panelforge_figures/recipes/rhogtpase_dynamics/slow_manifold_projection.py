"""Slow-manifold projection — geometric collapse of fast trajectories onto the slow manifold.

The v1.0 `quasi_steady_state_reduction` recipe shows the *temporal*
comparison of the full 2-D solution against its QSS-reduced 1-D slow
variable. This recipe is the *geometric* sibling: it draws the slow
manifold as a continuous curve in phase space, then overlays a family
of fast trajectories that sweep onto the manifold (nearly orthogonal
at first) and then slide along it toward the slow-system attractor.
The two recipes together form a paired story — dynamics vs geometry.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SlowManifoldInput(RecipeContract):
    x_grid: list[list[float]] = Field(...)
    y_grid: list[list[float]] = Field(...)
    u: list[list[float]] = Field(..., description="flow dx/dt on grid")
    v: list[list[float]] = Field(..., description="flow dy/dt on grid")
    slow_manifold: dict[str, list[float]] = Field(
        ..., description="{'x': [...], 'y': [...]} polyline of the slow manifold"
    )
    fast_trajectories: list[dict[str, list[float]]] = Field(
        ..., description="list of {'x': [...], 'y': [...]} polylines, each a fast trajectory"
    )
    epsilon: float = 0.05
    title: str = "Slow-manifold projection"


def _demo() -> SlowManifoldInput:
    # Slow-fast system:
    #   eps * dx/dt = y - (x^3/3 - x)     (fast: x relaxes to cubic nullcline)
    #   dy/dt      = -x                    (slow)
    eps = 0.05

    def rhs(state: np.ndarray) -> np.ndarray:
        x, y = state
        return np.array([(y - (x ** 3 / 3.0 - x)) / eps, -x])

    def rk4(ic: tuple[float, float], tmax: float, dt: float = 0.002) -> np.ndarray:
        n = int(tmax / dt)
        out = np.zeros((n + 1, 2), dtype=float)
        out[0] = ic
        state = np.array(ic, dtype=float)
        for i in range(n):
            k1 = rhs(state)
            k2 = rhs(state + 0.5 * dt * k1)
            k3 = rhs(state + 0.5 * dt * k2)
            k4 = rhs(state + dt * k3)
            state = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            out[i + 1] = state
        return out

    # Phase-plane grid for the muted streamplot backdrop.
    xs = np.linspace(-2.5, 2.5, 28)
    ys = np.linspace(-2.0, 2.0, 28)
    XX, YY = np.meshgrid(xs, ys)
    U = (YY - (XX ** 3 / 3.0 - XX)) / eps
    V = -XX
    # Cap extreme magnitudes so the streamplot reads cleanly.
    mag = np.sqrt(U ** 2 + V ** 2) + 1e-9
    scale = np.minimum(mag, 40.0) / mag
    U = U * scale
    V = V * scale

    # Slow manifold: y = g(x) = x^3/3 - x.
    sm_x = np.linspace(-2.5, 2.5, 200)
    sm_y = sm_x ** 3 / 3.0 - sm_x

    # Fast trajectories from various starting points above/below the manifold.
    starts = [
        (-2.3, 1.8), (-1.2, 1.8), (0.0, 1.6), (1.2, 1.8), (2.3, 1.8),
        (-2.3, -1.8), (-1.2, -1.8), (0.0, -1.8), (1.2, -1.8), (2.3, -1.8),
    ]
    trajs = []
    for ic in starts:
        path = rk4(ic, tmax=0.6, dt=0.001)  # short time — we want the "collapse".
        trajs.append({"x": path[:, 0].tolist(), "y": path[:, 1].tolist()})

    return SlowManifoldInput(
        x_grid=XX.tolist(), y_grid=YY.tolist(),
        u=U.tolist(), v=V.tolist(),
        slow_manifold={"x": sm_x.tolist(), "y": sm_y.tolist()},
        fast_trajectories=trajs,
        epsilon=eps,
    )


_META = RecipeMetadata(
    name="slow_manifold_projection",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question=(
        "How do fast trajectories geometrically collapse onto the slow "
        "invariant manifold in phase space?"
    ),
    required_fields=("x_grid", "y_grid", "u", "v", "slow_manifold", "fast_trajectories"),
    optional_fields=("epsilon", "title"),
    file_format_hints=("pickle", "npz"),
    alternatives_in_modality=(
        "quasi_steady_state_reduction",
        "timescale_separation_diagnostic",
    ),
)


@register_recipe(
    metadata=_META,
    contract=SlowManifoldInput,
    demo_contract=_demo,
)
def render(contract: SlowManifoldInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    XX = np.array(contract.x_grid, dtype=float)
    YY = np.array(contract.y_grid, dtype=float)
    U = np.array(contract.u, dtype=float)
    V = np.array(contract.v, dtype=float)

    # Backdrop streamplot, very muted.
    ax.streamplot(XX, YY, U, V, color="#DDDDDD", linewidth=0.4,
                  density=1.0, arrowsize=0.6, arrowstyle="-|>", zorder=1)

    # Fast trajectories — faint blue threads sweeping toward the manifold.
    for traj in contract.fast_trajectories:
        ax.plot(traj["x"], traj["y"], color="#1565C0", lw=0.9,
                alpha=0.75, zorder=3)
        # Starting IC marker.
        ax.scatter([traj["x"][0]], [traj["y"][0]], s=16,
                   facecolor="white", edgecolor="#1565C0",
                   linewidth=0.8, zorder=5)

    # Slow manifold — the visual star of the recipe.
    sm_x = contract.slow_manifold["x"]
    sm_y = contract.slow_manifold["y"]
    sm_color = palette.pick("GATE") if "GATE" in palette.semantic else "#F9A825"
    ax.plot(sm_x, sm_y, color=sm_color, lw=2.2, zorder=4,
            label="slow manifold  $y = g(x)$", solid_capstyle="round")

    # Label the manifold midway along its length.
    mid = len(sm_x) // 2
    ax.annotate(
        "slow manifold",
        xy=(sm_x[mid], sm_y[mid]),
        xytext=(18, -12), textcoords="offset points",
        fontsize=6.8, color="#6E4F00",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#D4A01A", lw=0.6, alpha=0.92),
        arrowprops=dict(arrowstyle="-", color="#D4A01A", lw=0.6),
        zorder=7,
    )

    # Callout with epsilon.
    ax.text(
        0.98, 0.02,
        rf"$\varepsilon$ = {smart_fmt(contract.epsilon)}",
        transform=ax.transAxes, ha="right", va="bottom",
        fontsize=6.6, color="#333333",
        bbox=dict(boxstyle="round,pad=0.18", fc="white",
                  ec="#BBBBBB", lw=0.5, alpha=0.92),
        zorder=7,
    )

    ax.set_xlabel(r"$x$ (fast)")
    ax.set_ylabel(r"$y$ (slow)")
    ax.set_xlim(float(XX.min()), float(XX.max()))
    ax.set_ylim(float(YY.min()), float(YY.max()))
    ax.set_aspect("equal")
    ax.set_title(
        f"{contract.title}  ·  "
        f"{len(contract.fast_trajectories)} fast trajectories",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
