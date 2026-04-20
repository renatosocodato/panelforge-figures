"""Extinction probability P_ext(θ) vs a control parameter.

Per initial-state curve of P_ext(θ) over a sweep of the control
parameter θ. Annotated with the θ at which each curve crosses
P_ext = 0.5 (the "tipping-point" parameter).
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


class ExtinctionInput(RecipeContract):
    theta: list[float] = Field(..., min_length=3)
    p_ext_by_initial: dict[str, list[float]] = Field(
        ..., description="initial-state label → P_ext(θ)"
    )
    parameter_label: str = "control parameter θ"
    horizon_label: str = ""
    title: str = "Extinction probability"


def _demo() -> ExtinctionInput:
    rng = np.random.default_rng(409)
    theta = np.linspace(0.3, 2.5, 40)
    curves = {}
    # Lower initial population → extinction rises earlier.
    for name, k in [("N0=5", 1.0), ("N0=20", 2.2), ("N0=50", 3.8)]:
        pe = 1.0 / (1.0 + np.exp((theta - k) * 4.0))
        pe += rng.normal(0, 0.008, theta.size)
        curves[name] = np.clip(pe, 0, 1).tolist()
    return ExtinctionInput(
        theta=theta.tolist(),
        p_ext_by_initial=curves,
        parameter_label="control θ",
        horizon_label="T = 100 s",
    )


_META = RecipeMetadata(
    name="extinction_probability_vs_parameter",
    modality="gillespie_stochastic",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "As a control parameter varies, what is the probability that "
        "the population goes extinct before some horizon?"
    ),
    required_fields=("theta", "p_ext_by_initial"),
    optional_fields=("parameter_label", "horizon_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("rate_vs_control_parameter",),
)


@register_recipe(
    metadata=_META,
    contract=ExtinctionInput,
    demo_contract=_demo,
)
def render(contract: ExtinctionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    theta = np.asarray(contract.theta, float)
    crossings = []
    for i, (name, vals) in enumerate(contract.p_ext_by_initial.items()):
        v = np.asarray(vals, float)
        color = palette[i % len(palette.colors)]
        ax.plot(theta, v, color=color, lw=1.3, zorder=3, label=name)
        # Find θ at P_ext = 0.5 (signed linear interpolation — works for
        # both increasing and decreasing sigmoids).
        idx = np.where(np.diff(np.sign(v - 0.5)))[0]
        if idx.size:
            k = int(idx[0])
            denom = v[k + 1] - v[k]
            if abs(denom) > 1e-6:
                frac = (0.5 - v[k]) / denom
                theta_cross = float(theta[k] + frac * (theta[k + 1] - theta[k]))
                crossings.append((name, theta_cross, color))
                ax.scatter([theta_cross], [0.5], s=26, color=color,
                           edgecolor="white", linewidth=0.6, zorder=5)

    # 0.5 reference.
    ax.axhline(0.5, color="#888888", lw=0.6, ls="--", zorder=1,
               label="P_ext = 0.5")

    ax.set_xlabel(contract.parameter_label)
    ax.set_ylabel("P(extinction)")
    ax.set_xlim(theta.min(), theta.max())
    ax.set_ylim(-0.03, 1.03)
    title = contract.title
    if contract.horizon_label:
        title += "  ·  " + contract.horizon_label
    ax.set_title(title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="center right",
              handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    if crossings:
        bits = ", ".join(f"{n}: θ*={smart_fmt(t)}"
                         for n, t, _ in crossings)
        fig = ax.figure
        fig.text(
            0.5, -0.16,
            f"tipping points: {bits}",
            ha="center", va="top", fontsize=6.6, color="#333333",
            transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
        )
    return ax
