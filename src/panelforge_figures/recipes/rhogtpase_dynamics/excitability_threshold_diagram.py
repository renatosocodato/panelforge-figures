"""Excitability threshold diagram — rest, threshold, sub/super-threshold orbits.

Excitability is a distinct dynamical class from bistability, tristability,
and simple oscillation. The canonical FitzHugh-Nagumo story: one stable
rest point, a threshold (approximated here by the middle branch of the
v-nullcline), and two sample perturbations of nearly identical amplitude
— one that decays back to rest without event, one that triggers a large
excursion (an "action-potential"-like loop) before returning.
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


class ExcitabilityInput(RecipeContract):
    x_grid: list[list[float]] = Field(...)
    y_grid: list[list[float]] = Field(...)
    u: list[list[float]] = Field(..., description="flow dv/dt on grid")
    v: list[list[float]] = Field(..., description="flow dw/dt on grid")
    rest_point: tuple[float, float]
    threshold_curve: dict[str, list[float]] = Field(
        ..., description="{'x': [...], 'y': [...]} polyline approximating the threshold"
    )
    sub_threshold_traj: dict[str, list[float]] = Field(
        ..., description="{'x': [...], 'y': [...]} — decays to rest"
    )
    super_threshold_traj: dict[str, list[float]] = Field(
        ..., description="{'x': [...], 'y': [...]} — makes excursion and returns"
    )
    nullcline_v: dict[str, list[float]] | None = None
    nullcline_w: dict[str, list[float]] | None = None
    title: str = "Excitability threshold"


def _demo() -> ExcitabilityInput:
    # FitzHugh-Nagumo: dv/dt = v - v^3/3 - w + I, dw/dt = eps*(v + a - b*w).
    I_ext = 0.34
    a = 0.7
    b = 0.8
    eps = 0.08

    def rhs(state: np.ndarray) -> np.ndarray:
        v, w = state
        return np.array([v - v ** 3 / 3.0 - w + I_ext,
                         eps * (v + a - b * w)])

    def rk4(ic: tuple[float, float], tmax: float, dt: float = 0.04) -> np.ndarray:
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

    # Grid for streamplot.
    vs = np.linspace(-2.4, 2.2, 30)
    ws = np.linspace(-0.8, 1.6, 30)
    VV, WW = np.meshgrid(vs, ws)
    U_field = VV - VV ** 3 / 3.0 - WW + I_ext
    V_field = eps * (VV + a - b * WW)

    # Find rest: iterate the w-nullcline w = (v+a)/b, intersect with v-nullcline.
    # Solve v - v^3/3 - (v+a)/b + I = 0 numerically.
    v_range = np.linspace(-2.5, 2.5, 4000)
    resid = v_range - v_range ** 3 / 3.0 - (v_range + a) / b + I_ext
    sign_change = np.where(np.diff(np.sign(resid)))[0]
    v_rest = float(v_range[sign_change[0]]) if sign_change.size else -1.2
    w_rest = (v_rest + a) / b
    rest = (v_rest, w_rest)

    # Threshold approximation: the middle branch of the v-nullcline.
    v_thr = np.linspace(-0.9, 0.9, 120)
    w_thr = v_thr - v_thr ** 3 / 3.0 + I_ext
    threshold = {"x": v_thr.tolist(), "y": w_thr.tolist()}

    # Sub-threshold: small perturbation stays in the rest basin.
    sub = rk4((v_rest + 0.18, w_rest), tmax=40.0, dt=0.04)
    sub_dict = {"x": sub[:, 0].tolist(), "y": sub[:, 1].tolist()}

    # Super-threshold: slightly larger perturbation triggers the excursion.
    sup = rk4((v_rest + 0.55, w_rest), tmax=60.0, dt=0.04)
    sup_dict = {"x": sup[:, 0].tolist(), "y": sup[:, 1].tolist()}

    # Nullclines for context.
    v_nc_x = np.linspace(-2.3, 2.1, 120)
    v_nc_y = v_nc_x - v_nc_x ** 3 / 3.0 + I_ext
    w_nc_x = np.linspace(-2.3, 2.1, 120)
    w_nc_y = (w_nc_x + a) / b

    return ExcitabilityInput(
        x_grid=VV.tolist(), y_grid=WW.tolist(),
        u=U_field.tolist(), v=V_field.tolist(),
        rest_point=rest,
        threshold_curve=threshold,
        sub_threshold_traj=sub_dict,
        super_threshold_traj=sup_dict,
        nullcline_v={"x": v_nc_x.tolist(), "y": v_nc_y.tolist()},
        nullcline_w={"x": w_nc_x.tolist(), "y": w_nc_y.tolist()},
    )


_META = RecipeMetadata(
    name="excitability_threshold_diagram",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question=(
        "What distinguishes a sub-threshold perturbation that decays from a "
        "super-threshold perturbation that triggers a large excursion?"
    ),
    required_fields=(
        "x_grid", "y_grid", "u", "v", "rest_point",
        "threshold_curve", "sub_threshold_traj", "super_threshold_traj",
    ),
    optional_fields=("nullcline_v", "nullcline_w", "title"),
    file_format_hints=("pickle", "npz"),
    alternatives_in_modality=("phase_portrait_oscillator",),
)


@register_recipe(
    metadata=_META,
    contract=ExcitabilityInput,
    demo_contract=_demo,
)
def render(contract: ExcitabilityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    _ = get_palette(AESTHETIC.primary_palette)

    XX = np.array(contract.x_grid, dtype=float)
    YY = np.array(contract.y_grid, dtype=float)
    U = np.array(contract.u, dtype=float)
    V = np.array(contract.v, dtype=float)

    ax.streamplot(XX, YY, U, V, color="#CCCCCC", linewidth=0.5, density=1.0,
                  arrowsize=0.7, arrowstyle="-|>", zorder=1)

    # Nullclines (optional): dashed lines.
    if contract.nullcline_v is not None:
        ax.plot(contract.nullcline_v["x"], contract.nullcline_v["y"],
                color="#666666", lw=0.9, ls="--", zorder=2,
                label="$v$-nullcline")
    if contract.nullcline_w is not None:
        ax.plot(contract.nullcline_w["x"], contract.nullcline_w["y"],
                color="#888888", lw=0.9, ls=":", zorder=2,
                label="$w$-nullcline")

    # Threshold curve — the excitable separatrix proxy.
    thr_x = contract.threshold_curve["x"]
    thr_y = contract.threshold_curve["y"]
    ax.plot(thr_x, thr_y, color="#333333", lw=1.4, zorder=3,
            label="threshold")

    # Sub-threshold: blue, decays quickly.
    ax.plot(contract.sub_threshold_traj["x"],
            contract.sub_threshold_traj["y"],
            color="#1565C0", lw=1.3, zorder=4, label="sub-threshold (decays)")
    sx0 = contract.sub_threshold_traj["x"][0]
    sy0 = contract.sub_threshold_traj["y"][0]
    ax.scatter([sx0], [sy0], s=40, facecolor="white",
               edgecolor="#1565C0", linewidth=1.1, zorder=6)

    # Super-threshold: red, large excursion.
    ax.plot(contract.super_threshold_traj["x"],
            contract.super_threshold_traj["y"],
            color="#C62828", lw=1.3, zorder=4,
            label="super-threshold (excursion)")
    zx0 = contract.super_threshold_traj["x"][0]
    zy0 = contract.super_threshold_traj["y"][0]
    ax.scatter([zx0], [zy0], s=40, facecolor="white",
               edgecolor="#C62828", linewidth=1.1, zorder=6)

    # Rest point.
    rx, ry = contract.rest_point
    ax.scatter([rx], [ry], s=72, facecolor="black",
               edgecolor="white", linewidth=1.2, zorder=7)
    ax.annotate("rest", xy=(rx, ry), xytext=(8, 8),
                textcoords="offset points", fontsize=6.8, color="#111111",
                bbox=dict(boxstyle="round,pad=0.16", fc="white",
                          ec="none", alpha=0.9))

    amp_sub = abs(sx0 - rx)
    amp_sup = abs(zx0 - rx)
    ax.set_xlabel(r"$v$ (fast variable)")
    ax.set_ylabel(r"$w$ (slow variable)")
    ax.set_xlim(float(XX.min()), float(XX.max()))
    ax.set_ylim(float(YY.min()), float(YY.max()))
    ax.set_title(
        f"{contract.title}  ·  "
        f"sub $\\Delta v$={smart_fmt(amp_sub)},  "
        f"sup $\\Delta v$={smart_fmt(amp_sup)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
