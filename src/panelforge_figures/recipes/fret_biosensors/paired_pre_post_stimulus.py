"""Paired pre / post-stimulus FRET-ratio comparison with connecting lines."""

from __future__ import annotations

import numpy as np
from pydantic import Field
from scipy import stats

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PairedPrePostInput(RecipeContract):
    pre_values: list[float] = Field(..., description="per-cell FRET ratio before stimulus")
    post_values: list[float] = Field(..., description="per-cell FRET ratio after stimulus")
    cell_ids: list[str] | None = None
    paired_pvalue: float | None = Field(
        None, description="override the p-value; otherwise computed via Wilcoxon"
    )
    mean_delta: float | None = None
    title: str = "Paired FRET ratio · pre vs post"


def _demo() -> PairedPrePostInput:
    rng = np.random.default_rng(605)
    n = 42
    pre = rng.normal(1.02, 0.07, n)
    # Most cells respond positively; a few decline.
    delta = rng.normal(0.22, 0.08, n)
    delta[:6] = rng.normal(-0.05, 0.04, 6)
    post = pre + delta
    return PairedPrePostInput(
        pre_values=pre.tolist(),
        post_values=post.tolist(),
        cell_ids=[f"c{i:02d}" for i in range(n)],
    )


_META = RecipeMetadata(
    name="paired_pre_post_stimulus",
    modality="fret_biosensors",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "For each cell, does the FRET ratio change significantly from "
        "pre-stimulus to post-stimulus, and how large is the per-cell shift?"
    ),
    required_fields=("pre_values", "post_values"),
    optional_fields=("cell_ids", "paired_pvalue", "mean_delta", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("ratio_distribution_by_condition",),
)


@register_recipe(
    metadata=_META,
    contract=PairedPrePostInput,
    demo_contract=_demo,
)
def render(contract: PairedPrePostInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    pre = np.asarray(contract.pre_values, dtype=float)
    post = np.asarray(contract.post_values, dtype=float)
    mask = np.isfinite(pre) & np.isfinite(post)
    pre, post = pre[mask], post[mask]

    # Per-cell connecting lines — thin grey so the reader can see individual
    # trajectories without the lines dominating.
    x_pre, x_post = 0.0, 1.0
    for p_i, q_i in zip(pre, post):
        # Responders up, decliners down: color the line faintly accordingly.
        line_color = ("#C62828" if q_i > p_i else "#1565C0")
        ax.plot([x_pre, x_post], [p_i, q_i],
                color=line_color, lw=0.5, alpha=0.35, zorder=2)

    # Per-cell dots.
    pre_color = (palette.pick("donor") if "donor" in palette.semantic
                 else palette[0])
    post_color = (palette.pick("acceptor") if "acceptor" in palette.semantic
                  else palette[1])
    ax.scatter([x_pre] * pre.size, pre, s=26, color=pre_color,
               edgecolor="white", linewidth=0.6, zorder=4, label="pre")
    ax.scatter([x_post] * post.size, post, s=26, color=post_color,
               edgecolor="white", linewidth=0.6, zorder=4, label="post")

    # Mean ± SEM markers, pushed outside the scatter columns — pre marker
    # to the LEFT of x_pre, post marker to the RIGHT of x_post — so the
    # markers and their numeric labels never touch the per-cell dots.
    mean_pre, sem_pre = float(pre.mean()), float(pre.std(ddof=1) / np.sqrt(pre.size))
    mean_post, sem_post = float(post.mean()), float(post.std(ddof=1) / np.sqrt(post.size))
    marker_offsets = [(x_pre - 0.22, mean_pre, sem_pre, "right"),
                      (x_post + 0.22, mean_post, sem_post, "left")]
    for x_pos, mu, se, label_side in marker_offsets:
        ax.errorbar([x_pos], [mu], yerr=[se],
                    fmt="s", color="#111111", ecolor="#111111",
                    markersize=6, markerfacecolor="white",
                    markeredgewidth=1.1, capsize=3.0, zorder=6)
        dx = -6 if label_side == "right" else 6
        ax.annotate(
            f"{smart_fmt(mu)}",
            xy=(x_pos, mu),
            xytext=(dx, 0), textcoords="offset points",
            ha=label_side, va="center",
            fontsize=6.2, color="#111111",
        )

    # Paired statistics.
    if contract.paired_pvalue is not None:
        p_val = contract.paired_pvalue
    else:
        try:
            _, p_val = stats.wilcoxon(pre, post)
            p_val = float(p_val)
        except Exception:
            p_val = float("nan")
    mean_delta = (float(contract.mean_delta)
                  if contract.mean_delta is not None
                  else float(np.mean(post - pre)))
    stars = "***" if p_val < 1e-3 else ("**" if p_val < 1e-2
                                         else ("*" if p_val < 5e-2 else "ns"))

    # Bracket + stars at the top.
    y_top = float(max(pre.max(), post.max())) + 0.06 * (
        float(max(pre.max(), post.max())) - float(min(pre.min(), post.min())))
    ax.plot([x_pre, x_pre, x_post, x_post],
            [y_top - 0.01, y_top, y_top, y_top - 0.01],
            color="#111111", lw=0.9, zorder=5)
    ax.text(0.5 * (x_pre + x_post), y_top + 0.01,
            f"{stars}  p = {smart_fmt(p_val)}",
            ha="center", va="bottom", fontsize=7.0, color="#111111")

    ax.set_xticks([x_pre, x_post])
    ax.set_xticklabels(["pre", "post"], fontsize=8.4)
    ax.set_xlim(-0.55, 1.85)
    ax.set_ylabel(r"FRET ratio  $F_A / F_D$")
    ax.set_title(
        f"{contract.title}  ·  N = {pre.size},  $\\Delta$ = {smart_fmt(mean_delta)}",
        fontsize=9.0, pad=8,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=0.8, handletextpad=0.4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
