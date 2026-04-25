"""Euler critical-length crossing distribution — per-group ECDF of
supported segment lengths, with L_crit vertical reference.

The biophysical question: how often do supported actin/MT segments
exceed the Euler buckling length L_crit per genotype? Higher
crossing fraction in LI implies more unstable supported segments.

Diagnostic-curve family: >=2 lines + >=1 legend. Satisfied by
per-group ECDF curves + the L_crit reference (still drawn as a
line) plus a legend.
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


class EulerCrossingInput(RecipeContract):
    supported_lengths_by_group: dict[str, list[float]] = Field(...)
    l_crit_um: float = Field(..., gt=0.0)
    title: str = "Euler critical-length crossing"


def _demo() -> EulerCrossingInput:
    rng = np.random.default_rng(7711)
    # WT supported segments distributed mostly below L_crit; LI shifted
    # toward longer lengths so a higher fraction crosses.
    wt = rng.lognormal(mean=np.log(7.0), sigma=0.45, size=80)
    li = rng.lognormal(mean=np.log(11.0), sigma=0.55, size=80)
    return EulerCrossingInput(
        supported_lengths_by_group={
            "WT": wt.tolist(),
            "LI": li.tolist(),
        },
        l_crit_um=12.0,
    )


_META = RecipeMetadata(
    name="euler_critical_length_crossing_distribution",
    modality="biophysics_scaling",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "Per genotype, what fraction of supported filament segments "
        "exceed the Euler buckling length L_crit?"
    ),
    required_fields=("supported_lengths_by_group", "l_crit_um"),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("buckling_critical_force_plot",),
)


@register_recipe(
    metadata=_META,
    contract=EulerCrossingInput,
    demo_contract=_demo,
)
def render(contract: EulerCrossingInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    fractions: dict[str, float] = {}
    for group, vals in contract.supported_lengths_by_group.items():
        v = np.sort(np.asarray(vals, float))
        if v.size == 0:
            continue
        ecdf_y = np.arange(1, v.size + 1) / v.size
        colour = _GROUP_COLOURS.get(group, "#333333")
        ax.plot(v, ecdf_y, color=colour, lw=1.2, zorder=4,
                label=group)
        # DKW 95 % band.
        eps = np.sqrt(np.log(2 / 0.05) / (2 * v.size))
        ax.fill_between(v, np.clip(ecdf_y - eps, 0, 1),
                        np.clip(ecdf_y + eps, 0, 1),
                        color=colour, alpha=0.15, linewidth=0,
                        zorder=2)
        # Crossing fraction.
        cross = float(np.mean(v >= contract.l_crit_um))
        fractions[group] = cross

    # L_crit vertical reference.
    ax.axvline(contract.l_crit_um, color="#444444", lw=0.8, ls="--",
               zorder=3, label=f"L_crit = {smart_fmt(contract.l_crit_um)} um")

    ax.set_xlabel("supported segment length (um)")
    ax.set_ylabel("ECDF")
    ax.set_ylim(0, 1.02)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)

    bits = [f"{g}: {smart_fmt(f * 100)} % >= L_crit"
            for g, f in fractions.items()]
    ax.set_title(
        f"{contract.title}  ·  " + "  ·  ".join(bits),
        fontsize=8.4, pad=4,
    )
    return ax
