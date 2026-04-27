"""Model calibration Brier forest — per-stratum Brier scores +/- 95 %
CI vs the perfect-calibration zero reference; reviewer-proof for
any P(commit) classifier surfaced earlier in the pack.

Coef-forest family: >=3 markers + >=1 reference line.
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


class CalibrationStratumRow(RecipeContract):
    stratum: str
    model: str
    brier: float
    brier_lo: float
    brier_hi: float
    reliability_intercept: float | None = None
    reliability_slope: float | None = None
    n: int


class CalibrationBrierForestInput(RecipeContract):
    rows: list[CalibrationStratumRow] = Field(..., min_length=3)
    perfect_calibration: float = 0.0
    title: str = "Model calibration Brier forest"


def _demo() -> CalibrationBrierForestInput:
    rng = np.random.default_rng(3291)
    strata = ["control · low age", "control · high age",
              "DISC1 · low age", "DISC1 · high age"]
    rows: list[CalibrationStratumRow] = []
    for st in strata:
        for model in ("logistic", "GAM"):
            base = 0.10 if "control" in st else 0.16
            base += rng.normal(0, 0.015)
            half = 0.025 + rng.uniform(0, 0.01)
            rows.append(CalibrationStratumRow(
                stratum=st, model=model,
                brier=float(base),
                brier_lo=float(base - half),
                brier_hi=float(base + half),
                reliability_intercept=float(rng.normal(0, 0.05)),
                reliability_slope=float(1.0 + rng.normal(0, 0.05)),
                n=120,
            ))
    return CalibrationBrierForestInput(rows=rows)


_META = RecipeMetadata(
    name="model_calibration_brier_forest",
    modality="intravital_imaging",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Per stratum and model, is the P(commit) classifier well "
        "calibrated (Brier score with 95 % CI; reliability slope "
        "near 1, intercept near 0)?"
    ),
    required_fields=("rows",),
    optional_fields=("perfect_calibration", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("commitment_phase_diagram",),
)


_MODEL_PALETTE = {
    "logistic": "#37474F",
    "GAM": "#26A69A",
    "HMM": "#AB47BC",
    "HSMM": "#FFA726",
}


@register_recipe(
    metadata=_META,
    contract=CalibrationBrierForestInput,
    demo_contract=_demo,
)
def render(contract: CalibrationBrierForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.0, 4.0))
    AESTHETIC.apply_to_ax(ax)

    n_rows = len(contract.rows)
    y = np.arange(n_rows)

    # Reference line at perfect calibration (Brier = 0).
    ax.axvline(contract.perfect_calibration, color="#888888", lw=0.7,
               ls="--", zorder=2,
               label=f"perfect (Brier = {smart_fmt(contract.perfect_calibration)})")

    for yi, r in zip(y, contract.rows):
        colour = _MODEL_PALETTE.get(r.model, "#37474F")
        marker = "o" if r.model == "logistic" else "s"
        ax.plot([r.brier_lo, r.brier_hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=3)
        ax.scatter([r.brier], [yi], s=44, marker=marker,
                   facecolor=colour, edgecolor="white", linewidth=0.5,
                   zorder=5)

    tick_labels = [f"{r.model}  ·  {r.stratum}" for r in contract.rows]
    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel("Brier score (lower = better calibration)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    from matplotlib.lines import Line2D
    handles = []
    for model, colour in _MODEL_PALETTE.items():
        if any(r.model == model for r in contract.rows):
            marker = "o" if model == "logistic" else "s"
            handles.append(Line2D(
                [0], [0], marker=marker, color="none",
                markerfacecolor=colour, markeredgecolor="white",
                markersize=6, label=model,
            ))
    handles.append(Line2D([0], [0], color="#888888", ls="--", lw=0.7,
                          label="perfect calibration"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.10),
              ncols=min(len(handles), 4), handlelength=1.0)

    # Median Brier per model in title.
    bits = []
    models = list(dict.fromkeys(r.model for r in contract.rows))
    for m in models:
        vals = [r.brier for r in contract.rows if r.model == m]
        bits.append(f"{m}: median = {smart_fmt(float(np.median(vals)))}")
    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
