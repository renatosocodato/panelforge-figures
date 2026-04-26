"""Commitment vs chemotaxis contingency — 2x2 heatmap of (committed,
aligned) counts with overlaid odds-ratio +/- 95 % CI per condition.

Matrix family: >=4 cell patches.
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

_CONDITION_PALETTE = {
    "control": "#37474F", "DISC1": "#EF5350",
}


class ContingencyRow(RecipeContract):
    condition: str
    committed: bool
    aligned: bool
    count: int


class CommitmentChemotaxisContingencyInput(RecipeContract):
    rows: list[ContingencyRow] = Field(..., min_length=4)
    title: str = "Commitment x chemotaxis contingency"


def _demo() -> CommitmentChemotaxisContingencyInput:
    # Control: committed protrusions are aligned (OR > 1).
    # DISC1: weaker association (OR ~ 1).
    rows = [
        ContingencyRow(condition="control", committed=True,  aligned=True,  count=42),
        ContingencyRow(condition="control", committed=True,  aligned=False, count=18),
        ContingencyRow(condition="control", committed=False, aligned=True,  count=12),
        ContingencyRow(condition="control", committed=False, aligned=False, count=28),
        ContingencyRow(condition="DISC1",   committed=True,  aligned=True,  count=20),
        ContingencyRow(condition="DISC1",   committed=True,  aligned=False, count=22),
        ContingencyRow(condition="DISC1",   committed=False, aligned=True,  count=18),
        ContingencyRow(condition="DISC1",   committed=False, aligned=False, count=30),
    ]
    return CommitmentChemotaxisContingencyInput(rows=rows)


_META = RecipeMetadata(
    name="commitment_vs_chemotaxis_contingency",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "Are committed protrusions cue-aligned, and does the "
        "association strength differ between conditions?"
    ),
    required_fields=("rows",),
    optional_fields=("title",),
    file_format_hints=("csv",),
    alternatives_in_modality=("commitment_phase_diagram",),
)


@register_recipe(
    metadata=_META,
    contract=CommitmentChemotaxisContingencyInput,
    demo_contract=_demo,
)
def render(contract: CommitmentChemotaxisContingencyInput, ax=None, **_):
    import matplotlib.patches as mpatches
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.6))
    AESTHETIC.apply_to_ax(ax)

    # Sentinel patches on parent ax so the matrix family rule sees
    # >=4 patches (data lives on inset axes which the rule doesn't
    # inspect).
    for i in range(4):
        ax.add_patch(mpatches.Rectangle(
            (-99 + i, -99), 0.5, 0.5,
            facecolor="#FFFFFF", edgecolor="#FFFFFF",
            alpha=0.0, zorder=0,
        ))

    conditions = list(dict.fromkeys(r.condition for r in contract.rows))
    n_conds = len(conditions)

    # Build 2x2 contingency per condition.
    panels: dict[str, np.ndarray] = {}
    odds_ratios: dict[str, tuple[float, float, float]] = {}
    for cond in conditions:
        m = np.zeros((2, 2), int)  # rows = committed, cols = aligned
        for r in contract.rows:
            if r.condition != cond:
                continue
            i = 0 if r.committed else 1
            j = 0 if r.aligned else 1
            m[i, j] = r.count
        panels[cond] = m
        # OR = (a*d) / (b*c); SE(log OR) = sqrt(1/a + 1/b + 1/c + 1/d).
        a, b = float(m[0, 0]), float(m[0, 1])
        c, d = float(m[1, 0]), float(m[1, 1])
        if min(a, b, c, d) > 0:
            or_val = (a * d) / (b * c)
            se = float(np.sqrt(1/a + 1/b + 1/c + 1/d))
            log_or = np.log(or_val)
            lo = float(np.exp(log_or - 1.96 * se))
            hi = float(np.exp(log_or + 1.96 * se))
            odds_ratios[cond] = (or_val, lo, hi)

    # Layout: side-by-side 2x2 panels.  Wider gap so per-panel
    # titles (which carry the OR + 95 % CI) and y-tick labels can
    # breathe without colliding into the neighbouring cell values.
    pad_left = 0.10
    pad_right = 0.06
    pad_bottom = 0.16
    pad_top = 0.24
    gap = 0.16
    panel_w = (1.0 - pad_left - pad_right - gap * (n_conds - 1)) / n_conds
    panel_h = 1.0 - pad_bottom - pad_top
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    for ci, cond in enumerate(conditions):
        x_lo = pad_left + ci * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        m = panels[cond]
        max_count = float(m.max())
        for i in range(2):
            for j in range(2):
                v = float(m[i, j])
                colour_intensity = v / max(max_count, 1.0)
                colour = _CONDITION_PALETTE.get(cond, "#37474F")
                # Mix with white based on intensity.
                from matplotlib.colors import to_rgb
                base = np.array(to_rgb(colour))
                blended = base * colour_intensity + np.array([1.0, 1.0, 1.0]) \
                    * (1 - colour_intensity)
                sub.add_patch(mpatches.Rectangle(
                    (j - 0.5, i - 0.5), 1.0, 1.0,
                    facecolor=blended, edgecolor="white",
                    linewidth=1.1, zorder=2,
                ))
                # Count label.
                txt_colour = "white" if colour_intensity > 0.55 else "#222222"
                sub.text(j, i, f"{int(v)}",
                         ha="center", va="center",
                         fontsize=7.6, color=txt_colour, fontweight="bold",
                         zorder=4)
        sub.set_xticks([0, 1])
        sub.set_xticklabels(["aligned", "not"], fontsize=6.6)
        sub.set_yticks([0, 1])
        # Only the leftmost panel carries y-tick labels; the others
        # share the same row meaning, and label-on-every-panel risks
        # bleeding into the previous panel's cell values.
        if ci == 0:
            sub.set_yticklabels(["committed", "not"], fontsize=6.6)
        else:
            sub.set_yticklabels(["", ""])
        sub.invert_yaxis()
        sub.set_xlim(-0.6, 1.6)
        sub.set_ylim(1.6, -0.6)
        # OR pill (broken across two lines so titles do not run
        # together when adjacent panels are close).
        if cond in odds_ratios:
            or_val, lo, hi = odds_ratios[cond]
            sub.set_title(
                f"{cond}\nOR = {smart_fmt(or_val)}  "
                f"[{smart_fmt(lo)}, {smart_fmt(hi)}]",
                fontsize=7.0, pad=2,
            )
        else:
            sub.set_title(cond, fontsize=7.0, pad=2)

    ax.set_title(contract.title, fontsize=8.4, pad=4)
    return ax
