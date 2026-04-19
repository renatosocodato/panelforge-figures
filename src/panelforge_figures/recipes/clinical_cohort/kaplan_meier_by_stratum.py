"""Kaplan-Meier survival curves by stratum with at-risk counts."""

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


class KMStratum(RecipeContract):
    name: str
    time_months: list[float]
    event: list[int] = Field(..., description="1 = event, 0 = censored")


class KMInput(RecipeContract):
    strata: list[KMStratum] = Field(..., min_length=1)
    logrank_p: float | None = None
    title: str = "Overall survival by stratum"


def _demo() -> KMInput:
    rng = np.random.default_rng(421)
    strata = []
    for name, lam in [("low-risk", 0.015), ("mid-risk", 0.028), ("high-risk", 0.055)]:
        n = 90
        t = rng.exponential(1.0 / lam, n)
        ev = (t < 48).astype(int)  # censor at 48 months
        t = np.minimum(t, 48.0)
        strata.append(KMStratum(
            name=name,
            time_months=t.tolist(),
            event=ev.tolist(),
        ))
    return KMInput(strata=strata, logrank_p=2.1e-4)


_META = RecipeMetadata(
    name="kaplan_meier_by_stratum",
    modality="clinical_cohort",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How does survival differ between risk strata, and is the separation statistically significant?",
    required_fields=("strata",),
    optional_fields=("logrank_p", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("cox_forest_hazard_ratios",),
)


def _km_estimator(t: np.ndarray, e: np.ndarray):
    order = np.argsort(t)
    t, e = t[order], e[order]
    times_event = np.unique(t[e == 1])
    S = 1.0
    S_curve = [1.0]
    t_curve = [0.0]
    for tj in times_event:
        at_risk = int(np.sum(t >= tj))
        d_j = int(np.sum((t == tj) & (e == 1)))
        if at_risk > 0:
            S *= (1 - d_j / at_risk)
        S_curve.append(S)
        t_curve.append(float(tj))
    return np.array(t_curve), np.array(S_curve)


@register_recipe(metadata=_META, contract=KMInput, demo_contract=_demo)
def render(contract: KMInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    for i, s in enumerate(contract.strata):
        t = np.array(s.time_months, dtype=float)
        e = np.array(s.event, dtype=int)
        tc, sc = _km_estimator(t, e)
        color = palette[i % len(palette.colors)]
        ax.step(tc, sc, where="post", color=color, lw=1.3, zorder=3,
                label=f"{s.name} (n={len(t)})")
        # Tick marks for censoring events.
        cens_t = t[e == 0]
        for ct in cens_t[:80]:
            # Survival probability at censoring time.
            idx = int(np.searchsorted(tc, ct, side="right") - 1)
            s_at_c = sc[max(0, idx)]
            ax.plot([ct, ct], [s_at_c - 0.01, s_at_c + 0.01],
                    color=color, lw=0.7, zorder=4, alpha=0.7)

    ax.set_xlabel("time (months)")
    ax.set_ylabel("survival probability")
    ax.set_ylim(0, 1.02)
    ax.set_xlim(left=0)

    title = contract.title
    if contract.logrank_p is not None:
        title = f"{title}  ·  log-rank p = {smart_fmt(contract.logrank_p)}"
    ax.set_title(title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower left", handlelength=1.8)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
