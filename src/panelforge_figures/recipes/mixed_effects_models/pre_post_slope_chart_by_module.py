"""Pre/post slope chart by module — paired pre/post score per module
× condition with connecting slope lines.

Renders a parallel-coordinate-style chart with two columns
(`pre` and `post`); each module is a horizontal slope line
connecting its pre value to its post value. Modules are coloured
by condition (e.g. female · CTL vs male · CKO), and significant
modules (per `is_significant`) are drawn at higher line weight to
surface the per-module response to intervention.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by the
pre + post markers per module + the per-module connecting slope line.
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
from ._shared import PrePostSlopeRow


class PrePostSlopeInput(RecipeContract):
    rows: list[PrePostSlopeRow] = Field(..., min_length=4)
    pre_label: str = "pre"
    post_label: str = "post"
    title: str = "Pre/post slope by module"


def _demo() -> PrePostSlopeInput:
    rng = np.random.default_rng(823)
    modules = [
        "GEF · Vav1", "GEF · Tiam1", "GEF · Trio",
        "GAP · Cdc42-GAP", "GAP · ARHGAP1",
        "Effector · WASP", "Effector · PAK1", "Effector · IQGAP1",
        "Effector · MRCK", "Effector · ROCK",
        "Lipid · PIP3", "Lipid · PA",
    ]
    rows: list[PrePostSlopeRow] = []
    for cond, base, slope_mu in (
        ("female · CTL",  0.20, 0.42),
        ("male · CKO",   -0.10, 0.18),
    ):
        for m in modules:
            pre = base + rng.normal(0.0, 0.10)
            post = pre + slope_mu + rng.normal(0.0, 0.18)
            sig = abs(post - pre) > 0.45
            rows.append(PrePostSlopeRow(
                module=m, condition=cond,
                pre_score=pre, post_score=post,
                is_significant=sig,
            ))
    return PrePostSlopeInput(rows=rows,
                             pre_label="baseline",
                             post_label="post-CDC42 perturbation")


_META = RecipeMetadata(
    name="pre_post_slope_chart_by_module",
    modality="mixed_effects_models",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across pathway modules, which respond strongly to the "
        "intervention (pre vs post), and how does the response "
        "differ between strata?"
    ),
    required_fields=("rows",),
    optional_fields=("pre_label", "post_label", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=(
        "mediation_decomposition_slope_chart",
        "emmeans_contrast_grid",
    ),
)


@register_recipe(
    metadata=_META,
    contract=PrePostSlopeInput,
    demo_contract=_demo,
)
def render(contract: PrePostSlopeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.0))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    conditions = sorted({r.condition for r in rows})
    palette = {
        "female · CTL": "#E91E63",
        "female · CKO": "#AD1457",
        "male · CTL":   "#1976D2",
        "male · CKO":   "#0D47A1",
    }
    fallback = ["#37474F", "#FFB300", "#26A69A", "#9C27B0"]
    for i, c in enumerate(conditions):
        palette.setdefault(c, fallback[i % len(fallback)])

    x_pre, x_post = 0.0, 1.0

    # Reference: dashed zero line on the y-axis.
    all_y = [r.pre_score for r in rows] + [r.post_score for r in rows]
    if min(all_y) < 0 < max(all_y):
        ax.axhline(0.0, color="#888888", lw=0.7, ls="--", zorder=1,
                   label="zero score")

    # Per-module slope lines + endpoint markers.
    for r in rows:
        colour = palette[r.condition]
        lw = 1.4 if r.is_significant else 0.6
        alpha = 0.92 if r.is_significant else 0.42
        ax.plot([x_pre, x_post], [r.pre_score, r.post_score],
                color=colour, lw=lw, alpha=alpha, zorder=3)
        ax.scatter([x_pre], [r.pre_score], s=22 if r.is_significant else 14,
                   facecolor=colour, edgecolor="white",
                   linewidth=0.4, alpha=alpha, zorder=4)
        ax.scatter([x_post], [r.post_score],
                   s=22 if r.is_significant else 14,
                   facecolor=colour, edgecolor="white",
                   linewidth=0.4, alpha=alpha, zorder=4)

    # Right-margin labels for significant modules — staggered with
    # leader lines to avoid overlap. Sort by post_score (top-down)
    # and force minimum vertical separation.
    sig_rows = sorted(
        [r for r in rows if r.is_significant],
        key=lambda r: -r.post_score,
    )
    if sig_rows:
        y_min, y_max = min(all_y), max(all_y)
        y_span = max(y_max - y_min, 0.10)
        min_gap = 0.045 * y_span                 # min vertical separation
        label_y = [r.post_score for r in sig_rows]
        # Greedy top-down adjustment so adjacent labels don't overlap.
        for i in range(1, len(label_y)):
            if label_y[i-1] - label_y[i] < min_gap:
                label_y[i] = label_y[i-1] - min_gap
        x_label = x_post + 0.10
        for r, ly in zip(sig_rows, label_y):
            colour = palette[r.condition]
            # Leader line: marker → label anchor.
            ax.plot([x_post + 0.01, x_label - 0.01],
                    [r.post_score, ly],
                    color=colour, lw=0.5, alpha=0.55, zorder=4)
            ax.text(x_label, ly, r.module,
                    ha="left", va="center", fontsize=6.0,
                    color=colour, zorder=5)

    # Per-condition mean slope as a thicker overlay (the headline fit line).
    for c in conditions:
        sub = [r for r in rows if r.condition == c]
        mean_pre = float(np.mean([r.pre_score for r in sub]))
        mean_post = float(np.mean([r.post_score for r in sub]))
        ax.plot([x_pre, x_post], [mean_pre, mean_post],
                color=palette[c], lw=2.2, alpha=0.95, zorder=6,
                label=f"{c}  ·  Δ={smart_fmt(mean_post - mean_pre)}")

    ax.set_xticks([x_pre, x_post])
    ax.set_xticklabels([contract.pre_label, contract.post_label],
                       fontsize=7.4)
    ax.set_xlim(-0.15, x_post + 0.65)
    ax.set_ylabel("module score")
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ax.legend(fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=len(conditions), handlelength=1.6)

    n_sig = sum(1 for r in rows if r.is_significant)
    ax.set_title(
        f"{contract.title}  ·  {n_sig}/{len(rows)} significant modules",
        fontsize=8.2, pad=4,
    )
    return ax
