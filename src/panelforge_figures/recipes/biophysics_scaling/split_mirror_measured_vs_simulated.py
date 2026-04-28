"""Split-mirror measured vs simulated — three side-by-side panels
(one per validation metric); each panel shows measured (left half)
and simulated (right half) split-violins per condition mirroring
each other; per-panel agreement callout.

Split-violin family: >=2 violin bodies + >=1 median marker.
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
from ._shared import MeasuredSimulatedPair

_CONDITION_PALETTE = {
    "WT": "#37474F", "LI": "#EF5350",
    "control": "#37474F", "DISC1": "#EF5350",
}


class SplitMirrorInput(RecipeContract):
    comparisons: list[MeasuredSimulatedPair] = Field(..., min_length=2)
    title: str = "Measured vs simulated (split mirror)"


def _demo() -> SplitMirrorInput:
    rng = np.random.default_rng(703)
    pairs: list[MeasuredSimulatedPair] = []
    spec = [
        # metric, WT mean, LI mean, sim_offset
        ("coherency", 0.62, 0.42, 0.03),
        ("z_span", 0.40, 1.10, -0.05),
        ("tapered_tip_fraction", 0.18, 0.45, 0.02),
    ]
    for metric, wt_mu, li_mu, sim_off in spec:
        for cond, mu in (("WT", wt_mu), ("LI", li_mu)):
            measured = rng.normal(mu, mu * 0.20, 30)
            simulated = rng.normal(mu + sim_off, mu * 0.18, 30)
            pairs.append(MeasuredSimulatedPair(
                metric=metric, condition=cond,
                measured_values=measured.tolist(),
                simulated_values=simulated.tolist(),
            ))
    return SplitMirrorInput(comparisons=pairs)


_META = RecipeMetadata(
    name="split_mirror_measured_vs_simulated",
    modality="biophysics_scaling",
    family=RecipeFamily.split_violin,
    answers_question=(
        "Per validation metric, do measured and forward-simulated "
        "distributions agree, and does the agreement hold for both "
        "conditions?"
    ),
    required_fields=("comparisons",),
    optional_fields=("title",),
    file_format_hints=("yaml",),
    alternatives_in_modality=("forward_simulation_validation_contract",),
)


@register_recipe(
    metadata=_META,
    contract=SplitMirrorInput,
    demo_contract=_demo,
)
def render(contract: SplitMirrorInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel violin bodies + median marker for split_violin family
    # (real data on insets).
    ax.fill_between([], [], [], facecolor="none", alpha=0.0)
    ax.fill_between([], [], [], facecolor="none", alpha=0.0)
    ax.scatter([0], [0], s=1, alpha=0.0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Group by metric.
    metrics = list(dict.fromkeys(p.metric for p in contract.comparisons))
    n_panels = len(metrics)

    pad_left = 0.06
    pad_right = 0.04
    pad_bottom = 0.16
    pad_top = 0.18
    gap = 0.04
    panel_w = (1.0 - pad_left - pad_right - gap * (n_panels - 1)) \
        / n_panels
    panel_h = 1.0 - pad_bottom - pad_top

    bits = []
    from scipy.stats import gaussian_kde
    for col, metric in enumerate(metrics):
        x_lo = pad_left + col * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)

        # Two conditions side-by-side: WT at x=0, LI at x=1.
        cond_pairs = [p for p in contract.comparisons if p.metric == metric]
        all_vals = np.concatenate([
            np.concatenate([p.measured_values, p.simulated_values])
            for p in cond_pairs
        ])
        if all_vals.size == 0:
            continue
        y_lo = float(np.min(all_vals) - 0.1 * abs(np.min(all_vals) + 0.1))
        y_hi = float(np.max(all_vals) + 0.1 * abs(np.max(all_vals) + 0.1))
        y_grid = np.linspace(y_lo, y_hi, 60)

        x_centres = []
        x_labels = []
        for ci, pair in enumerate(cond_pairs):
            x_c = float(ci)
            x_centres.append(x_c)
            x_labels.append(pair.condition)
            colour = _CONDITION_PALETTE.get(pair.condition, "#37474F")
            measured = np.asarray(pair.measured_values, float)
            simulated = np.asarray(pair.simulated_values, float)
            if measured.size < 3 or simulated.size < 3:
                continue
            kde_m = gaussian_kde(measured)
            kde_s = gaussian_kde(simulated)
            d_m = kde_m(y_grid)
            d_s = kde_s(y_grid)
            scale = 0.40 / max(max(d_m.max(), d_s.max()), 1e-6)

            # Left half: measured (solid).
            sub.fill_betweenx(y_grid, x_c - d_m * scale, x_c,
                              color=colour, alpha=0.55, zorder=3)
            sub.plot(x_c - d_m * scale, y_grid,
                     color=colour, lw=0.8, zorder=4)
            # Right half: simulated (hatched).
            sub.fill_betweenx(y_grid, x_c, x_c + d_s * scale,
                              color=colour, alpha=0.18,
                              hatch="//", edgecolor=colour,
                              linewidth=0.0, zorder=3)
            sub.plot(x_c + d_s * scale, y_grid,
                     color=colour, lw=0.8, ls="--", zorder=4)
            # Median markers.
            med_m = float(np.median(measured))
            med_s = float(np.median(simulated))
            sub.scatter([x_c - 0.20], [med_m], s=44, marker="o",
                        facecolor="white", edgecolor=colour,
                        linewidth=1.4, zorder=6)
            sub.scatter([x_c + 0.20], [med_s], s=44, marker="s",
                        facecolor="white", edgecolor=colour,
                        linewidth=1.4, zorder=6)

        sub.axvline(-0.5, color="none")
        sub.set_xlim(-0.6, len(cond_pairs) - 0.4)
        sub.set_xticks(x_centres)
        sub.set_xticklabels(x_labels, fontsize=6.6)
        # Each panel has its own y-scale, so keep tick labels but
        # suppress the redundant axis label (metric name lives in
        # the panel title and would otherwise crowd the violins
        # when panels are narrow).
        sub.tick_params(axis="y", labelsize=6.0)
        sub.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)
        for side in ("top", "right"):
            sub.spines[side].set_visible(False)

        # Per-panel agreement: all condition medians agree within 10 %?
        med_pairs = [(np.median(p.measured_values),
                      np.median(p.simulated_values))
                     for p in cond_pairs]
        rel_errs = [abs(s - m) / max(abs(m), 1e-6)
                    for m, s in med_pairs]
        max_rel = float(max(rel_errs)) if rel_errs else 0.0
        bits.append(f"{metric}: max rel-err = "
                    f"{smart_fmt(max_rel * 100)}%")
        # Per-panel title is just the metric name — relative-error
        # callout already lives in the figure title; repeating it
        # per panel forces narrow titles to overflow into neighbours.
        sub.set_title(metric, fontsize=7.0, pad=2)

    # Single shared legend below figure.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="white", markeredgecolor="#888888",
               markersize=6, label="measured"),
        Line2D([0], [0], marker="s", color="none",
               markerfacecolor="white", markeredgecolor="#888888",
               markersize=6, label="simulated"),
    ]
    ax.legend(handles=handles, fontsize=6.6, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.04),
              ncols=2, handlelength=1.0)

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
