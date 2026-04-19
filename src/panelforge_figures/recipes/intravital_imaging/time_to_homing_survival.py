"""Time-to-homing survival — KM-style curve showing cumulative fraction arriving at target site."""

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


class HomingStratum(RecipeContract):
    name: str
    time_to_home_min: list[float]
    homed: list[int] = Field(..., description="1 = homed, 0 = did not home by end of imaging")


class HomingSurvivalInput(RecipeContract):
    strata: list[HomingStratum] = Field(..., min_length=1)
    logrank_p: float | None = None
    title: str = "Time to target-site homing"


def _demo() -> HomingSurvivalInput:
    rng = np.random.default_rng(473)
    strata = []
    for name, scale, frac in [
        ("WT", 22.0, 0.85),
        ("KO", 38.0, 0.60),
        ("KO + rescue", 26.0, 0.78),
    ]:
        n = 70
        tto = rng.exponential(scale, n)
        ev = (rng.uniform(0, 1, n) < frac).astype(int)
        tto = np.minimum(tto, 180.0)
        strata.append(HomingStratum(
            name=name,
            time_to_home_min=tto.tolist(),
            homed=ev.tolist(),
        ))
    return HomingSurvivalInput(strata=strata, logrank_p=1.8e-3)


_META = RecipeMetadata(
    name="time_to_homing_survival",
    modality="intravital_imaging",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How quickly do cells reach their target tissue site, stratified by genotype or treatment?",
    required_fields=("strata",),
    optional_fields=("logrank_p", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cell_track_trajectory_field",),
)


@register_recipe(metadata=_META, contract=HomingSurvivalInput, demo_contract=_demo)
def render(contract: HomingSurvivalInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    for i, s in enumerate(contract.strata):
        t = np.array(s.time_to_home_min, dtype=float)
        e = np.array(s.homed, dtype=int)
        order = np.argsort(t)
        t, e = t[order], e[order]
        n = t.size
        curve_t = [0.0]
        curve_f = [0.0]
        homed_so_far = 0
        for tj, ej in zip(t, e):
            if ej == 1:
                homed_so_far += 1
                curve_t.append(float(tj))
                curve_f.append(homed_so_far / n)
        color = palette[i % len(palette.colors)]
        ax.step(curve_t, curve_f, where="post", color=color, lw=1.3,
                zorder=3, label=f"{s.name} (n={n})")

    ax.set_xlabel("time (min)")
    ax.set_ylabel("fraction homed")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(left=0)

    title = contract.title
    if contract.logrank_p is not None:
        title = f"{title}  ·  log-rank p = {smart_fmt(contract.logrank_p)}"
    ax.set_title(title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
