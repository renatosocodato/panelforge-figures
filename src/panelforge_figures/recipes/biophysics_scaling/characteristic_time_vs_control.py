"""Characteristic time τ(p) — divergence / decay vs a control parameter
with critical-divergence or Arrhenius fit, fitted exponent + residuals.
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


class CharacteristicTimeInput(RecipeContract):
    control: list[float] = Field(..., min_length=5, description="control parameter p")
    tau: list[float] = Field(..., min_length=5, description="characteristic time τ(p)")
    mode: str = Field(
        "critical",
        description="'critical' for τ ~ |p - p_c|^-ν; 'arrhenius' for τ ~ exp(Ea/kT)",
    )
    p_c: float | None = Field(None, description="critical value, if mode='critical'")
    kT: float = Field(1.0, description="k_B T for Arrhenius")
    control_label: str = "control p"
    title: str = "Characteristic time vs control"


def _demo() -> CharacteristicTimeInput:
    rng = np.random.default_rng(683)
    p_c = 1.0
    p = np.concatenate([
        np.linspace(0.05, 0.92, 12),
        np.linspace(1.08, 2.0, 12),
    ])
    nu = 1.4
    tau = 2.5 * np.abs(p - p_c) ** (-nu) * np.exp(rng.normal(0, 0.08, p.size))
    return CharacteristicTimeInput(
        control=p.tolist(),
        tau=tau.tolist(),
        mode="critical",
        p_c=p_c,
        control_label="p / p_c",
        title="Critical slowing-down of state switching",
    )


_META = RecipeMetadata(
    name="characteristic_time_vs_control",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "How does the characteristic time τ diverge or decay as a "
        "control parameter is varied?"
    ),
    required_fields=("control", "tau"),
    optional_fields=("mode", "p_c", "kT", "control_label", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("buckling_critical_force_plot",),
)


@register_recipe(
    metadata=_META,
    contract=CharacteristicTimeInput,
    demo_contract=_demo,
)
def render(contract: CharacteristicTimeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    p = np.asarray(contract.control, float)
    tau = np.asarray(contract.tau, float)

    ax.scatter(p, tau, s=30, color="#1565C0", alpha=0.8,
               edgecolor="white", linewidth=0.5, zorder=4,
               label="data")

    if contract.mode == "critical":
        p_c = float(contract.p_c) if contract.p_c is not None else float(
            p[np.argmax(tau)])
        eps = np.abs(p - p_c)
        valid = eps > 1e-6
        leps, ltau = np.log(eps[valid]), np.log(tau[valid])
        slope, intercept = np.polyfit(leps, ltau, 1)
        nu_fit = -slope
        # Fit curve plotted on each side of p_c.
        for side, sign in [("left", -1), ("right", 1)]:
            ps_side = np.linspace(p_c + sign * 0.9, p_c + sign * 0.02, 100)
            eps_side = np.abs(ps_side - p_c)
            ts_side = np.exp(intercept) * eps_side ** slope
            ax.plot(ps_side, ts_side, color="#222222", lw=1.1, zorder=5,
                    label=(f"fit (ν = {smart_fmt(float(nu_fit))})"
                           if side == "left" else None))
        # Critical line.
        ax.axvline(p_c, color="#C62828", lw=0.8, ls="--", zorder=3,
                   label=f"p_c = {smart_fmt(p_c)}")
        ax.set_xlabel(contract.control_label)
        ax.set_ylabel(r"τ (arb.)")
        ax.set_yscale("log")
        ax.text(0.02, 0.97,
                f"mode: critical\n"
                f"τ ~ |p - p_c|$^{{-ν}}$\n"
                f"ν = {smart_fmt(float(nu_fit))}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=6.8, color="#333333",
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec="#BBBBBB", lw=0.5, alpha=0.92),
                zorder=6)
    else:
        # Arrhenius: log τ vs 1/p (treating p as kT).
        kT_inv = 1.0 / p
        ltau = np.log(tau)
        slope, intercept = np.polyfit(kT_inv, ltau, 1)
        Ea = slope   # in the same units as p
        pfit = np.linspace(p.min(), p.max(), 100)
        tfit = np.exp(intercept) * np.exp(slope / pfit)
        ax.plot(pfit, tfit, color="#222222", lw=1.1, zorder=5,
                label=f"Arrhenius (E$_a$ = {smart_fmt(float(Ea))})")
        ax.set_xlabel(contract.control_label)
        ax.set_ylabel(r"τ (arb.)")
        ax.set_yscale("log")
        ax.text(0.02, 0.97,
                f"mode: Arrhenius\n"
                f"τ ~ exp(E$_a$/kT)\n"
                f"E$_a$ = {smart_fmt(float(Ea))}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=6.8, color="#333333",
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec="#BBBBBB", lw=0.5, alpha=0.92),
                zorder=6)

    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
