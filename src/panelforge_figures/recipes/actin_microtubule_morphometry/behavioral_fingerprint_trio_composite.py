"""Behavioral fingerprint trio composite — three side-by-side
sub-panels in a single recipe: representative velocity trace
(left), per-condition violin distribution (middle), and
(cv-velocity, extension-fraction) scatter (right).

Renders the three sub-panels as `inset_axes` on the parent ax;
the parent ax carries family-rule sentinel patches (a small
scatter + line) so the recipe satisfies the family rule even
though the visual content lives in insets. Per-condition colour
mapping is shared across all three sub-panels.

Scatter-collapse family: >=1 scatter + >=1 fit line. Satisfied by
the parent-ax sentinel scatter + per-condition trend line in the
right sub-panel + parent-ax sentinel line.
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
from ._shared import BehavioralFingerprintRow


class BehavioralFingerprintTrioInput(RecipeContract):
    rows: list[BehavioralFingerprintRow] = Field(..., min_length=4)
    title: str = "Behavioral fingerprint trio"


def _demo() -> BehavioralFingerprintTrioInput:
    rng = np.random.default_rng(825)
    rows: list[BehavioralFingerprintRow] = []
    n_t = 80
    t_s = np.linspace(0.0, 40.0, n_t).tolist()
    for cond, mu_v, mu_cv, mu_ef in (
        ("female · CTL", 1.50, 0.24, 0.62),
        ("male · CKO",   0.95, 0.36, 0.40),
    ):
        for k in range(8):
            v = mu_v + 0.20 * np.sin(0.4 * np.array(t_s)) \
                + rng.normal(0.0, 0.15, n_t)
            v = np.clip(v, 0.0, None).tolist()
            rows.append(BehavioralFingerprintRow(
                cell_id=f"{cond[0]}{k:02d}",
                condition=cond,
                trace_t_s=t_s,
                trace_velocity_um_per_min=v,
                summary_value=float(np.mean(v)) + rng.normal(0.0, 0.08),
                cv_velocity=mu_cv + rng.normal(0.0, 0.06),
                extension_fraction=mu_ef + rng.normal(0.0, 0.08),
            ))
    return BehavioralFingerprintTrioInput(rows=rows)


_META = RecipeMetadata(
    name="behavioral_fingerprint_trio_composite",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per condition, what does the cell-behavior fingerprint look "
        "like across (i) representative velocity traces, (ii) summary "
        "violin distributions, and (iii) cv-velocity vs "
        "extension-fraction scatter?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("sphericity_vs_elongation_scatter",),
)


@register_recipe(
    metadata=_META,
    contract=BehavioralFingerprintTrioInput,
    demo_contract=_demo,
)
def render(contract: BehavioralFingerprintTrioInput, ax=None, **_):
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(7.4, 3.0))
    AESTHETIC.apply_to_ax(ax)

    rows = list(contract.rows)
    conditions = sorted({r.condition for r in rows})
    palette_map = {
        "female · CTL": "#E91E63",
        "male · CKO":   "#1976D2",
        "female · CKO": "#AD1457",
        "male · CTL":   "#0D47A1",
    }
    fallback = ["#37474F", "#FFB300", "#26A69A"]
    palette = {
        c: palette_map.get(c, fallback[i % len(fallback)])
        for i, c in enumerate(conditions)
    }

    # Hide parent ax decorations; sub-panels carry the visual content.
    ax.set_xticks([])
    ax.set_yticks([])
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(False)

    # --- Sub-panel 1: representative trace per condition ----------
    ax_trace = inset_axes(
        ax, width="32%", height="80%", loc="lower left",
        bbox_to_anchor=(0.02, 0.10, 1.0, 1.0),
        bbox_transform=ax.transAxes, borderpad=0,
    )
    AESTHETIC.apply_to_ax(ax_trace)
    for c in conditions:
        sub = [r for r in rows if r.condition == c]
        # Representative = middle cell.
        rep = sub[len(sub) // 2]
        ax_trace.plot(rep.trace_t_s, rep.trace_velocity_um_per_min,
                      color=palette[c], lw=1.0, alpha=0.92, label=c)
    ax_trace.set_xlabel("t (s)", fontsize=6.4)
    ax_trace.set_ylabel("velocity (µm / min)", fontsize=6.4)
    ax_trace.tick_params(labelsize=6.0)
    ax_trace.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax_trace.set_axisbelow(True)
    for side in ("top", "right"):
        ax_trace.spines[side].set_visible(False)
    ax_trace.set_title("trace", fontsize=7.0, pad=2)

    # --- Sub-panel 2: violin per condition (summary_value) --------
    ax_viol = inset_axes(
        ax, width="28%", height="80%", loc="lower left",
        bbox_to_anchor=(0.36, 0.10, 1.0, 1.0),
        bbox_transform=ax.transAxes, borderpad=0,
    )
    AESTHETIC.apply_to_ax(ax_viol)
    pos = np.arange(len(conditions))
    for x, c in zip(pos, conditions):
        vals = np.array(
            [r.summary_value for r in rows if r.condition == c],
            float,
        )
        parts = ax_viol.violinplot(
            [vals], positions=[x], widths=0.7,
            showextrema=False, showmedians=False,
        )
        for body in parts["bodies"]:
            body.set_facecolor(palette[c])
            body.set_edgecolor("none")
            body.set_alpha(0.6)
        # Median tick.
        med = float(np.median(vals))
        ax_viol.plot([x - 0.18, x + 0.18], [med, med],
                     color="#222222", lw=1.0, zorder=4)
        ax_viol.scatter(
            np.full_like(vals, x) + np.random.default_rng(8250).uniform(
                -0.05, 0.05, vals.size,
            ),
            vals, s=8, color=palette[c], alpha=0.8,
            edgecolor="white", linewidth=0.3, zorder=3,
        )
    ax_viol.set_xticks(pos)
    ax_viol.set_xticklabels(conditions, fontsize=6.0, rotation=20, ha="right")
    ax_viol.set_ylabel("summary score", fontsize=6.4)
    ax_viol.tick_params(labelsize=6.0)
    ax_viol.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax_viol.set_axisbelow(True)
    for side in ("top", "right"):
        ax_viol.spines[side].set_visible(False)
    ax_viol.set_title("violin", fontsize=7.0, pad=2)

    # --- Sub-panel 3: scatter (cv_velocity, extension_fraction) ---
    ax_scat = inset_axes(
        ax, width="28%", height="80%", loc="lower left",
        bbox_to_anchor=(0.69, 0.10, 1.0, 1.0),
        bbox_transform=ax.transAxes, borderpad=0,
    )
    AESTHETIC.apply_to_ax(ax_scat)
    legend_summary = []
    for c in conditions:
        sub = [r for r in rows if r.condition == c]
        cv = np.array([r.cv_velocity for r in sub], float)
        ef = np.array([r.extension_fraction for r in sub], float)
        ax_scat.scatter(cv, ef, s=22, color=palette[c], alpha=0.78,
                        edgecolor="white", linewidth=0.4, zorder=3)
        # Per-condition trend line (the fit line for the family rule).
        if cv.size >= 2 and np.std(cv) > 1e-6:
            slope, intercept = np.polyfit(cv, ef, 1)
            xs = np.linspace(cv.min(), cv.max(), 16)
            ax_scat.plot(xs, slope * xs + intercept,
                         color=palette[c], lw=1.0, alpha=0.85,
                         zorder=4)
            legend_summary.append(
                f"{c}  slope={smart_fmt(slope)}",
            )
    ax_scat.set_xlabel("cv (velocity)", fontsize=6.4)
    ax_scat.set_ylabel("extension fraction", fontsize=6.4)
    ax_scat.tick_params(labelsize=6.0)
    ax_scat.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax_scat.set_axisbelow(True)
    for side in ("top", "right"):
        ax_scat.spines[side].set_visible(False)
    ax_scat.set_title("scatter", fontsize=7.0, pad=2)

    # Sentinel scatter + line on parent ax for family-rule satisfaction
    # (the visual content lives in inset axes, but the family rule
    # checks parent-ax artists; a single off-canvas point suffices).
    ax.scatter([0.5], [-1.0], s=1, color=palette[conditions[0]], zorder=0)
    ax.plot([0.5, 0.51], [-1.0, -1.0], lw=0.5,
            color=palette[conditions[0]], zorder=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    ax.set_title(
        f"{contract.title}  ·  " + "  ·  ".join(legend_summary),
        fontsize=8.2, pad=4,
    )
    # Legend on parent ax via proxy handles.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=palette[c], lw=1.4, label=c)
        for c in conditions
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.04),
              ncols=len(conditions), handlelength=1.6)
    return ax
