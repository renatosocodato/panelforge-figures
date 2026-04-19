"""Poincaré first-return map — 1-D discrete map on a Poincaré section.

Continuous-time phase portraits capture structure; a first-return map
on a Poincaré section reduces a limit-cycle system to a 1-D discrete
map whose fixed points are the periodic orbits of the flow. This
recipe draws `x_{n+1} = P(x_n)` as the primary curve, overlays the
identity diagonal, and renders a cobweb iteration from a sample IC so
the reader can *see* the convergence (or divergence) to the periodic
orbit — including period-doubling when the map has slope magnitude > 1.
It is the only discrete-time recipe in the rhogtpase_dynamics modality.
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


class ReturnMapInput(RecipeContract):
    x_n: list[float] = Field(..., description="value at section crossing n")
    x_n_plus_1: list[float] = Field(..., description="value at crossing n+1")
    section_description: str = "Poincaré section"
    cobweb_trajectory: list[tuple[float, float]] = Field(
        default_factory=list,
        description="sequence of (x_n, x_n+1) pairs visited by iterating an IC",
    )
    fit_slope: float | None = None
    title: str = "First-return map"


def _demo() -> ReturnMapInput:
    # Logistic-flavoured return map with r in the period-2 regime:
    # P(x) = r * x * (1 - x), r = 3.3 → unique fixed point loses stability,
    # stable period-2 orbit born.
    r = 3.3
    xs = np.linspace(0.0, 1.0, 400)
    ps = r * xs * (1.0 - xs)

    # Sample from a simulated limit cycle: iterate a random IC with noise.
    rng = np.random.default_rng(13)
    state = 0.22
    pairs: list[tuple[float, float]] = []
    for _ in range(200):
        nxt = float(np.clip(r * state * (1.0 - state)
                            + rng.normal(0, 0.004), 0.0, 1.0))
        pairs.append((float(state), nxt))
        state = nxt
    # (x_n, x_n+1) scatter pairs from the same orbit.
    x_n_arr = np.array([p[0] for p in pairs])
    x_np1_arr = np.array([p[1] for p in pairs])

    # Cobweb of the first 20 iterations (deterministic).
    state = 0.22
    cobweb: list[tuple[float, float]] = []
    for _ in range(20):
        nxt = r * state * (1.0 - state)
        cobweb.append((state, nxt))
        state = nxt

    return ReturnMapInput(
        x_n=np.concatenate([xs, x_n_arr]).tolist(),
        x_n_plus_1=np.concatenate([ps, x_np1_arr]).tolist(),
        section_description=r"$v = v^*$ upward-crossing (Poincaré section)",
        cobweb_trajectory=cobweb,
        fit_slope=1.0 - 2.0 * (1.0 - 1.0 / r),  # slope of logistic at the FP
    )


_META = RecipeMetadata(
    name="poincare_first_return_map",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "On a Poincaré section, what is the first-return map and how does "
        "it reveal periodic-orbit stability (including period-doubling)?"
    ),
    required_fields=("x_n", "x_n_plus_1"),
    optional_fields=("section_description", "cobweb_trajectory", "fit_slope", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("phase_portrait_oscillator",),
)


@register_recipe(
    metadata=_META,
    contract=ReturnMapInput,
    demo_contract=_demo,
)
def render(contract: ReturnMapInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 4.0))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    xn = np.array(contract.x_n, dtype=float)
    xn1 = np.array(contract.x_n_plus_1, dtype=float)

    lo = float(min(xn.min(), xn1.min()))
    hi = float(max(xn.max(), xn1.max()))
    span = max(hi - lo, 1e-6)
    ax.set_xlim(lo - 0.02 * span, hi + 0.02 * span)
    ax.set_ylim(lo - 0.02 * span, hi + 0.02 * span)

    # Identity diagonal — the reference against which the return map is read.
    ax.plot([lo, hi], [lo, hi], color="#888888", lw=0.8, ls="--",
            zorder=1, label="$x_{n+1} = x_n$")

    # Distinguish dense-curve prior (first ~400 pts) from scatter
    # samples (rest): first pass as line, second pass as points.
    # Heuristic: if there's a monotone-ish block of 200+ pts at the start,
    # render it as a line; otherwise scatter everything.
    if len(xn) > 400:
        ax.plot(xn[:400], xn1[:400], color=palette[2] if len(palette.colors) > 2
                else "#1565C0",
                lw=1.3, zorder=3, label="$P(x)$")
        ax.scatter(xn[400:], xn1[400:], s=10, color="#333333",
                   alpha=0.55, edgecolor="none", zorder=4,
                   label="sampled crossings")
    else:
        ax.scatter(xn, xn1, s=10, color=palette[2] if len(palette.colors) > 2
                   else "#1565C0",
                   alpha=0.85, edgecolor="none", zorder=3,
                   label="sampled crossings")

    # Cobweb iteration traces in red — visually conveys convergence.
    if contract.cobweb_trajectory:
        cwx: list[float] = []
        cwy: list[float] = []
        x_prev = contract.cobweb_trajectory[0][0]
        y_prev = x_prev
        for xn_val, xnp1_val in contract.cobweb_trajectory:
            # Vertical step up to the curve.
            cwx.extend([xn_val, xn_val])
            cwy.extend([y_prev, xnp1_val])
            # Horizontal step to the diagonal.
            cwx.extend([xn_val, xnp1_val])
            cwy.extend([xnp1_val, xnp1_val])
            y_prev = xnp1_val
            x_prev = xnp1_val
        ax.plot(cwx, cwy, color="#C62828", lw=0.8, alpha=0.85,
                zorder=5, label="cobweb iteration")
        # Mark IC.
        ax.scatter([contract.cobweb_trajectory[0][0]],
                   [contract.cobweb_trajectory[0][0]],
                   s=30, facecolor="white", edgecolor="#C62828",
                   linewidth=1.0, zorder=6)

    # Slope-at-FP callout if provided.
    if contract.fit_slope is not None:
        ax.text(
            0.03, 0.97,
            f"slope at FP = {smart_fmt(contract.fit_slope)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.18", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=7,
        )

    ax.set_xlabel(r"$x_n$")
    ax.set_ylabel(r"$x_{n+1}$")
    ax.set_aspect("equal")
    ax.set_title(
        f"{contract.title}  ·  {contract.section_description}",
        fontsize=8.6, pad=4,
    )
    ax.legend(fontsize=6.4, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
