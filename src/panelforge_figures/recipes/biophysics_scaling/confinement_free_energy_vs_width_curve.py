"""Confinement free energy F_conf(w) per group — protrusion width on
x, free-energy cost on y, per-group curves with 95 % CI ribbons and a
crossing-width annotation.

Where (along the width axis) does the genotype start to pay a
different confinement cost? The crossing width is reported as a
verdict pill.

Timecourse-hierarchical-CI family: >=1 filled CI band + >=1 mean
line. Satisfied by per-group F_conf(w) curve + ribbon.
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

_GROUP_COLOURS = {"WT": "#1565C0", "LI": "#C62828",
                  "control": "#1565C0", "treated": "#C62828"}


class ConfinementFreeEnergyInput(RecipeContract):
    width_grid_um: list[float] = Field(..., min_length=5)
    fconf_by_group: dict[str, list[float]] = Field(...)
    ci_by_group: dict[str, list[tuple[float, float]]] = Field(...)
    crossing_width_callout: bool = True
    kT_units: bool = True
    title: str = "Confinement free energy vs width"


def _demo() -> ConfinementFreeEnergyInput:
    width = np.linspace(0.4, 4.0, 40)
    # F_conf(w) = a / w^2 — narrower confinement = higher cost. WT and
    # LI differ by a small group factor that grows below w ~ 0.8 um.
    wt = 1.2 / width ** 1.7
    li = 1.6 / width ** 1.7
    half = 0.18 + 0.12 / width
    fconf = {"WT": wt.tolist(), "LI": li.tolist()}
    ci = {
        "WT": [(float(v - h), float(v + h)) for v, h in zip(wt, half)],
        "LI": [(float(v - h), float(v + h)) for v, h in zip(li, half)],
    }
    return ConfinementFreeEnergyInput(
        width_grid_um=width.tolist(),
        fconf_by_group=fconf,
        ci_by_group=ci,
    )


_META = RecipeMetadata(
    name="confinement_free_energy_vs_width_curve",
    modality="biophysics_scaling",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "How does the per-group confinement free-energy cost F_conf(w) "
        "depend on protrusion width, and where do the curves diverge?"
    ),
    required_fields=("width_grid_um", "fconf_by_group", "ci_by_group"),
    optional_fields=("crossing_width_callout", "kT_units", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("force_length_characteristic",),
)


@register_recipe(
    metadata=_META,
    contract=ConfinementFreeEnergyInput,
    demo_contract=_demo,
)
def render(contract: ConfinementFreeEnergyInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    width = np.asarray(contract.width_grid_um, float)
    curves: dict[str, np.ndarray] = {}
    for group, vals in contract.fconf_by_group.items():
        f = np.asarray(vals, float)
        curves[group] = f
        ci = np.asarray(contract.ci_by_group.get(group, []), float)
        colour = _GROUP_COLOURS.get(group, "#333333")
        ax.plot(width, f, color=colour, lw=1.2, zorder=4, label=group)
        if ci.shape == (len(width), 2):
            ax.fill_between(width, ci[:, 0], ci[:, 1],
                            color=colour, alpha=0.18, linewidth=0,
                            zorder=2)

    # Crossing-width annotation: where do two groups diverge by >= 1 kT?
    crossing_w: float | None = None
    if contract.crossing_width_callout and len(curves) == 2:
        g0, g1 = list(curves.keys())
        diff = curves[g1] - curves[g0]
        threshold = 1.0
        idx = np.where(np.abs(diff) >= threshold)[0]
        if idx.size:
            crossing_w = float(width[idx[0]])
            ax.axvline(crossing_w, color="#444444", lw=0.7, ls=":",
                       zorder=3,
                       label=f"|Δ| ≥ 1 kT at w = {smart_fmt(crossing_w)} um")

    ax.set_xlabel("protrusion width w (um)")
    y_label = "F_conf (kT)" if contract.kT_units else "F_conf"
    ax.set_ylabel(y_label)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="upper right",
              handlelength=1.4)

    title_bits = [contract.title]
    if crossing_w is not None:
        title_bits.append(f"first divergence at w = {smart_fmt(crossing_w)} um")
    ax.set_title("  ·  ".join(title_bits), fontsize=8.4, pad=4)
    return ax
