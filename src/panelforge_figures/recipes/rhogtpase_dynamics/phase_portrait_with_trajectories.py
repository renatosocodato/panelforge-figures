"""Phase portrait with overlaid integrated trajectories from multiple ICs.

Where existing phase-portrait recipes in this modality render only the
streamplot flow field and fixed-point markers, this recipe adds the
*dynamics* layer: a family of N integrated trajectories from marked
initial conditions, each time-colored along its length, so the reader
sees how solutions relax onto the attractor landscape.
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


class TrajectoryPhaseInput(RecipeContract):
    x_grid: list[list[float]] = Field(..., description="meshgrid X for the flow field")
    y_grid: list[list[float]] = Field(..., description="meshgrid Y for the flow field")
    u: list[list[float]] = Field(..., description="flow dx/dt on the grid")
    v: list[list[float]] = Field(..., description="flow dy/dt on the grid")
    trajectories: list[dict[str, list[float]]] = Field(
        ..., description="list of {'t', 'x', 'y'} dicts, one per initial condition"
    )
    fixed_points: list[dict[str, float | str]] = Field(
        ..., description="list of {'x', 'y', 'kind'} — kind ∈ {'stable','unstable','saddle'}"
    )
    title: str = "Phase portrait · sample trajectories"


def _demo() -> TrajectoryPhaseInput:
    # Damped Duffing bistable: dx/dt = y, dy/dt = x - x^3 - 0.3 y.
    # Stable spirals at (±1, 0); saddle at (0, 0). Rich trajectory diversity.
    damp = 0.3

    def rhs(state: np.ndarray) -> np.ndarray:
        x, y = state
        return np.array([y, x - x ** 3 - damp * y])

    def rk4(ic: tuple[float, float], tmax: float, dt: float = 0.04) -> np.ndarray:
        n = int(tmax / dt)
        out = np.zeros((n + 1, 3), dtype=float)
        out[0] = (0.0, ic[0], ic[1])
        state = np.array(ic, dtype=float)
        for i in range(n):
            k1 = rhs(state)
            k2 = rhs(state + 0.5 * dt * k1)
            k3 = rhs(state + 0.5 * dt * k2)
            k4 = rhs(state + dt * k3)
            state = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
            out[i + 1] = (out[i, 0] + dt, state[0], state[1])
        return out

    xs = np.linspace(-2.0, 2.0, 28)
    ys = np.linspace(-2.0, 2.0, 28)
    XX, YY = np.meshgrid(xs, ys)
    U = YY
    V = XX - XX ** 3 - damp * YY

    ic_list = [
        (-1.8, 1.5), (-1.5, -1.7), (-0.25, 1.6), (0.25, -1.6),
        (1.8, -1.1), (1.4, 1.7), (-1.0, 0.8), (1.0, -0.6),
        (-0.5, 0.1), (0.5, -0.1),
    ]
    trajs = []
    for ic in ic_list:
        data = rk4(ic, tmax=18.0, dt=0.05)
        trajs.append({
            "t": data[:, 0].tolist(),
            "x": data[:, 1].tolist(),
            "y": data[:, 2].tolist(),
        })

    fixed_points = [
        {"x": -1.0, "y": 0.0, "kind": "stable"},
        {"x": 1.0, "y": 0.0, "kind": "stable"},
        {"x": 0.0, "y": 0.0, "kind": "saddle"},
    ]

    return TrajectoryPhaseInput(
        x_grid=XX.tolist(),
        y_grid=YY.tolist(),
        u=U.tolist(),
        v=V.tolist(),
        trajectories=trajs,
        fixed_points=fixed_points,
    )


_META = RecipeMetadata(
    name="phase_portrait_with_trajectories",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question=(
        "How do solution trajectories from multiple initial conditions relax "
        "onto the attractor landscape?"
    ),
    required_fields=("x_grid", "y_grid", "u", "v", "trajectories", "fixed_points"),
    optional_fields=("title",),
    file_format_hints=("pickle", "npz", "csv"),
    alternatives_in_modality=(
        "phase_portrait_bistable",
        "phase_portrait_oscillator",
        "phase_portrait_tristable",
    ),
)


@register_recipe(
    metadata=_META,
    contract=TrajectoryPhaseInput,
    demo_contract=_demo,
)
def render(contract: TrajectoryPhaseInput, ax=None, **_):
    import matplotlib as mpl

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 4.0))
    AESTHETIC.apply_to_ax(ax)
    _ = get_palette(AESTHETIC.primary_palette)  # palette loaded for aesthetic check

    XX = np.array(contract.x_grid, dtype=float)
    YY = np.array(contract.y_grid, dtype=float)
    U = np.array(contract.u, dtype=float)
    V = np.array(contract.v, dtype=float)

    # Muted streamplot backdrop — the "shape" of the flow, not the dynamics.
    ax.streamplot(XX, YY, U, V, color="#BBBBBB", linewidth=0.5, density=1.0,
                  arrowsize=0.8, arrowstyle="-|>", zorder=1)

    # Time-colored trajectories using viridis.
    cmap = mpl.colormaps["viridis"]
    t_max = max(max(traj["t"]) for traj in contract.trajectories)
    for traj in contract.trajectories:
        t = np.array(traj["t"], dtype=float)
        x = np.array(traj["x"], dtype=float)
        y = np.array(traj["y"], dtype=float)
        # Segment-colored plot (LineCollection-equivalent via step-plot).
        for i in range(0, len(t) - 1, 3):
            frac = t[i] / t_max
            ax.plot(x[i:i + 4], y[i:i + 4], color=cmap(frac), lw=1.0,
                    alpha=0.85, zorder=3, solid_capstyle="round")
        # Open-circle IC marker so the reader can see where each trajectory began.
        ax.scatter([x[0]], [y[0]], s=28, facecolor="white",
                   edgecolor="#222222", linewidth=0.9, zorder=5)

    # Fixed points with the modality's stability convention.
    for fp in contract.fixed_points:
        kind = str(fp.get("kind", "stable"))
        fx = float(fp["x"])
        fy = float(fp["y"])
        if kind == "stable":
            ax.scatter([fx], [fy], s=68, facecolor="black",
                       edgecolor="white", linewidth=1.2, zorder=6)
        elif kind == "unstable":
            ax.scatter([fx], [fy], s=68, facecolor="white",
                       edgecolor="black", linewidth=1.2, zorder=6)
        else:  # saddle
            ax.scatter([fx], [fy], s=68, facecolor="#888888",
                       edgecolor="black", linewidth=1.2, zorder=6)

    # Time colorbar proxy.
    sm = mpl.cm.ScalarMappable(
        norm=mpl.colors.Normalize(vmin=0.0, vmax=float(t_max)),
        cmap=cmap,
    )
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.046, pad=0.04, shrink=0.85)
    cbar.set_label(r"time $t$", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    ax.set_xlabel(r"$x$")
    ax.set_ylabel(r"$y$")
    ax.set_xlim(float(XX.min()), float(XX.max()))
    ax.set_ylim(float(YY.min()), float(YY.max()))
    ax.set_aspect("equal")
    ax.set_title(
        f"{contract.title}  ·  {len(contract.trajectories)} ICs,  "
        f"$t_{{max}}$ = {smart_fmt(float(t_max))}",
        fontsize=9.0, pad=4,
    )
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
