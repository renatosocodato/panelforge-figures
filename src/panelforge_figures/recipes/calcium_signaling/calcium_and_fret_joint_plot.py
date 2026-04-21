"""Joint Ca²⁺ × FRET activity scatter with marginal histograms.

For cells recorded simultaneously in Ca²⁺ and FRET, plots per-cell
(event rate, FRET ratio) as a central scatter with marginal histograms
on the top and right, fitted OLS line, Pearson r.
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


class CaFretJointInput(RecipeContract):
    cell_id: list[str] = Field(..., min_length=3)
    ca_event_rate_hz: list[float] = Field(...)
    fret_ratio: list[float] = Field(...)
    condition: list[str] | None = None
    title: str = "Ca²⁺ × FRET joint"


def _demo() -> CaFretJointInput:
    rng = np.random.default_rng(401)
    n = 120
    ca = np.clip(rng.gamma(2.0, 0.15, n), 0.01, None)
    fret = 1.0 + 0.45 * (ca - ca.mean()) / ca.std() + rng.normal(0, 0.08, n)
    conds = rng.choice(["baseline", "KCl", "TTX"], n,
                       p=[0.45, 0.35, 0.20])
    return CaFretJointInput(
        cell_id=[f"c{i:03d}" for i in range(n)],
        ca_event_rate_hz=ca.tolist(),
        fret_ratio=fret.tolist(),
        condition=conds.tolist(),
    )


_META = RecipeMetadata(
    name="calcium_and_fret_joint_plot",
    modality="calcium_signaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "For cells recorded simultaneously in Ca²⁺ and FRET, how do "
        "the two activity measures covary?"
    ),
    required_fields=("cell_id", "ca_event_rate_hz", "fret_ratio"),
    optional_fields=("condition", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("single_cell_calcium_landscape",),
)


@register_recipe(
    metadata=_META,
    contract=CaFretJointInput,
    demo_contract=_demo,
)
def render(contract: CaFretJointInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        fig = plt.figure(figsize=(5.0, 4.2))
        gs = fig.add_gridspec(2, 2,
                              width_ratios=[4, 1], height_ratios=[1, 4],
                              wspace=0.06, hspace=0.06)
        ax_top = fig.add_subplot(gs[0, 0])
        ax_right = fig.add_subplot(gs[1, 1])
        ax_main = fig.add_subplot(gs[1, 0], sharex=ax_top, sharey=ax_right)
    else:
        fig = ax.figure
        pos = ax.get_subplotspec()
        ax.remove()
        sub = pos.subgridspec(2, 2,
                              width_ratios=[4, 1], height_ratios=[1, 4],
                              wspace=0.06, hspace=0.06)
        ax_top = fig.add_subplot(sub[0, 0])
        ax_right = fig.add_subplot(sub[1, 1])
        ax_main = fig.add_subplot(sub[1, 0], sharex=ax_top, sharey=ax_right)

    for a in (ax_top, ax_right, ax_main):
        AESTHETIC.apply_to_ax(a)

    ca = np.asarray(contract.ca_event_rate_hz, float)
    fr = np.asarray(contract.fret_ratio, float)
    mask = np.isfinite(ca) & np.isfinite(fr)
    ca = ca[mask]
    fr = fr[mask]

    conds = (np.asarray(contract.condition)
             if contract.condition is not None else None)
    if conds is not None:
        conds = conds[mask]
        unique = list(dict.fromkeys(conds.tolist()))
        colors = ["#43A047", "#E65100", "#6A1B9A", "#1565C0"][: len(unique)]
        for c, col in zip(unique, colors):
            m = conds == c
            ax_main.scatter(ca[m], fr[m], s=16, color=col, alpha=0.75,
                            edgecolor="white", linewidth=0.3, zorder=3,
                            label=f"{c} (n={int(m.sum())})")
    else:
        ax_main.scatter(ca, fr, s=16, color="#43A047", alpha=0.75,
                        edgecolor="white", linewidth=0.3, zorder=3,
                        label=f"cells (n={ca.size})")

    # OLS fit.
    if ca.std() > 0:
        slope, intercept = np.polyfit(ca, fr, 1)
        xs = np.linspace(ca.min(), ca.max(), 100)
        ax_main.plot(xs, slope * xs + intercept,
                     color="#111111", lw=1.0, zorder=4,
                     label=f"OLS slope={smart_fmt(float(slope))}")

    r = float(np.corrcoef(ca, fr)[0, 1]) if ca.std() > 0 else 0.0
    ax_main.set_xlabel("Ca²⁺ event rate (Hz)")
    ax_main.set_ylabel("FRET ratio")
    ax_main.legend(fontsize=6.4, frameon=False, loc="lower right",
                   handlelength=1.4)
    ax_main.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax_main.set_axisbelow(True)

    # Marginal histograms.
    ax_top.hist(ca, bins=24, color="#888888", alpha=0.75,
                edgecolor="white", linewidth=0.4)
    ax_top.set_ylabel("n", fontsize=6.4)
    ax_top.tick_params(labelbottom=False, labelsize=6.0)
    ax_top.set_title(
        f"{contract.title}  ·  r = {smart_fmt(r)}",
        fontsize=9.0, pad=4,
    )

    ax_right.hist(fr, bins=24, orientation="horizontal",
                  color="#888888", alpha=0.75,
                  edgecolor="white", linewidth=0.4)
    ax_right.set_xlabel("n", fontsize=6.4)
    ax_right.tick_params(labelleft=False, labelsize=6.0)

    return ax_main
