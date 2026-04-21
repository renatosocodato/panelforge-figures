"""Bliss vs Loewe synergy-score scatter across drug pairs."""

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


class BlissLoeweInput(RecipeContract):
    pair_names: list[str] = Field(..., min_length=3)
    bliss_score: list[float] = Field(...)
    loewe_score: list[float] = Field(...)
    synergy_threshold: float = Field(default=0.1)
    title: str = "Bliss vs Loewe synergy"


def _demo() -> BlissLoeweInput:
    rng = np.random.default_rng(409)
    n = 22
    pairs = [f"P{i+1:02d}" for i in range(n)]
    # Most agree near 0; a few agree positive (synergy), a few disagree.
    bliss = rng.normal(0.0, 0.08, n)
    loewe = 0.85 * bliss + rng.normal(0.0, 0.06, n)
    # Inject known synergies.
    idx = rng.choice(n, 4, replace=False)
    bliss[idx] += rng.uniform(0.2, 0.5, 4)
    loewe[idx] += rng.uniform(0.2, 0.5, 4)
    # Inject disagreement pair.
    disagree = rng.choice(n, 2, replace=False)
    bliss[disagree] = 0.3
    loewe[disagree] = -0.2
    return BlissLoeweInput(
        pair_names=pairs,
        bliss_score=bliss.tolist(),
        loewe_score=loewe.tolist(),
        synergy_threshold=0.1,
    )


_META = RecipeMetadata(
    name="synergy_score_bliss_loewe",
    modality="dose_response_pharmacology",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "For a panel of drug pairs, how do Bliss and Loewe synergy "
        "scores compare — do the two models agree on which pairs are "
        "synergistic?"
    ),
    required_fields=("pair_names", "bliss_score", "loewe_score"),
    optional_fields=("synergy_threshold", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("isobologram_combination", "drug_combo_heatmap"),
)


@register_recipe(
    metadata=_META,
    contract=BlissLoeweInput,
    demo_contract=_demo,
)
def render(contract: BlissLoeweInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 4.0))
    AESTHETIC.apply_to_ax(ax)

    pairs = contract.pair_names
    b = np.asarray(contract.bliss_score, float)
    lo = np.asarray(contract.loewe_score, float)
    thr = contract.synergy_threshold

    # Colour by agreement / disagreement.
    agree_syn = (b > thr) & (lo > thr)
    agree_ant = (b < -thr) & (lo < -thr)
    disagree = np.logical_xor(b > thr, lo > thr) | np.logical_xor(b < -thr, lo < -thr)
    neutral = ~(agree_syn | agree_ant | disagree)

    ax.scatter(b[neutral], lo[neutral], s=22, color="#888888",
               edgecolor="white", linewidth=0.3, alpha=0.80, zorder=3,
               label=f"neutral (n={int(neutral.sum())})")
    ax.scatter(b[agree_syn], lo[agree_syn], s=36, color="#2E7D32",
               edgecolor="white", linewidth=0.5, zorder=4,
               label=f"synergy (n={int(agree_syn.sum())})")
    ax.scatter(b[agree_ant], lo[agree_ant], s=36, color="#C62828",
               edgecolor="white", linewidth=0.5, zorder=4,
               label=f"antagonism (n={int(agree_ant.sum())})")
    ax.scatter(b[disagree], lo[disagree], s=36, color="#F9A825",
               edgecolor="white", linewidth=0.5, zorder=5,
               label=f"disagree (n={int(disagree.sum())})")

    # Agreement diagonal.
    lim = max(np.max(np.abs(b)), np.max(np.abs(lo))) * 1.15
    ax.plot([-lim, lim], [-lim, lim], color="#111111", lw=0.8, ls="--",
            zorder=2, label="Bliss = Loewe")

    # Threshold band.
    ax.axvline(thr, color="#2E7D32", lw=0.6, ls=":", zorder=1)
    ax.axvline(-thr, color="#C62828", lw=0.6, ls=":", zorder=1)
    ax.axhline(thr, color="#2E7D32", lw=0.6, ls=":", zorder=1)
    ax.axhline(-thr, color="#C62828", lw=0.6, ls=":", zorder=1)

    # Label top agreeing synergies.
    top_idx = np.argsort(-(b + lo))[:3]
    for i in top_idx:
        ax.text(b[i], lo[i], f"  {pairs[i]}", ha="left", va="center",
                fontsize=6.2, color="#2E7D32", zorder=6)

    r = float(np.corrcoef(b, lo)[0, 1]) if b.std() > 0 else 0.0
    ax.set_xlabel("Bliss score")
    ax.set_ylabel("Loewe score")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_title(
        f"{contract.title}  ·  r = {smart_fmt(r)}, n pairs = {int(b.size)}",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.2, frameon=False, loc="upper left",
              handlelength=1.2)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
