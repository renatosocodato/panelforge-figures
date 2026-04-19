"""Persistence-length fit — exponential decay of filament angular correlation."""

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


class PersistenceLengthInput(RecipeContract):
    contour_length_um: list[float] = Field(...)
    cos_theta_mean: list[float] = Field(..., description="<cos θ(s)> along contour")
    cos_theta_sem: list[float] | None = None
    component: str = "actin"
    title: str = "Filament persistence length"


def _demo() -> PersistenceLengthInput:
    rng = np.random.default_rng(491)
    s = np.linspace(0.1, 10, 60)
    Lp = 3.2  # persistence length in μm
    obs = np.exp(-s / Lp) + rng.normal(0, 0.03, s.size)
    sem = 0.04 * np.ones_like(s)
    return PersistenceLengthInput(
        contour_length_um=s.tolist(),
        cos_theta_mean=obs.tolist(),
        cos_theta_sem=sem.tolist(),
        component="actin",
    )


_META = RecipeMetadata(
    name="persistence_length_fit",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question="What is the persistence length L_p of a filament population, from the exponential decay of angular correlation along the contour?",
    required_fields=("contour_length_um", "cos_theta_mean"),
    optional_fields=("cos_theta_sem", "component", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("filament_orientation_histogram",),
)


@register_recipe(metadata=_META, contract=PersistenceLengthInput, demo_contract=_demo)
def render(contract: PersistenceLengthInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    s = np.array(contract.contour_length_um, dtype=float)
    c = np.array(contract.cos_theta_mean, dtype=float)
    color = (palette.pick(contract.component)
             if contract.component in palette.semantic else palette[0])

    if contract.cos_theta_sem is not None:
        sem = np.array(contract.cos_theta_sem, dtype=float)
        ax.fill_between(s, np.maximum(c - sem, 0), c + sem,
                        color=color, alpha=0.18, linewidth=0, zorder=1)

    ax.scatter(s, c, s=22, color=color,
               edgecolor="white", linewidth=0.5, zorder=3,
               label=f"{contract.component} data")

    # Fit exponential: log(c) vs s → slope = -1/Lp.
    mask = c > 1e-2
    if mask.sum() >= 3:
        slope, intercept = np.polyfit(s[mask], np.log(c[mask]), 1)
        Lp = -1.0 / slope if slope < 0 else np.nan
        s_fine = np.linspace(s.min(), s.max(), 120)
        ax.plot(s_fine, np.exp(intercept) * np.exp(slope * s_fine),
                color="#333333", lw=1.3, zorder=4,
                label=f"fit: $L_p$ = {smart_fmt(float(Lp))} $\\mu$m")

    ax.axhline(0, color="#AAAAAA", lw=0.4, ls=":", zorder=1)
    ax.set_xlabel(r"contour length $s$ ($\mu$m)")
    ax.set_ylabel(r"$\langle \cos \theta(s) \rangle$")
    ax.set_ylim(-0.1, 1.1)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
