"""Competing-model residual panels — multi-panel residuals vs predicted
for >=2 competing model fits, with zero-residual reference line and
RMSE / AIC / BIC callouts per model.

Scatter-collapse family: >=1 scatter + >=1 fit line.
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
from ._shared import CompetingModelFit


class CompetingModelResidualInput(RecipeContract):
    fits: list[CompetingModelFit] = Field(..., min_length=2)
    title: str = "Competing-model residual panels"


def _demo() -> CompetingModelResidualInput:
    rng = np.random.default_rng(431)
    n = 80
    x = np.linspace(0.5, 5.0, n)
    # Truth: y = 0.6 * x + 0.10 * x**2 + noise.
    truth = 0.6 * x + 0.10 * x ** 2
    obs = truth + rng.normal(0, 0.20, n)

    # Width-only model (linear) — biased at high x.
    pred_w = 0.78 * x + 0.10 + rng.normal(0, 0.05, n)
    res_w = obs - pred_w

    # Interaction model (linear + quadratic) — closer to truth.
    pred_i = 0.6 * x + 0.10 * x ** 2 + rng.normal(0, 0.05, n)
    res_i = obs - pred_i

    return CompetingModelResidualInput(
        fits=[
            CompetingModelFit(
                model_name="width_only",
                predicted=pred_w.tolist(),
                observed=obs.tolist(),
                residuals=res_w.tolist(),
                aic=298.4, bic=305.1,
                rmse=float(np.sqrt(np.mean(res_w ** 2))),
            ),
            CompetingModelFit(
                model_name="interaction",
                predicted=pred_i.tolist(),
                observed=obs.tolist(),
                residuals=res_i.tolist(),
                aic=212.8, bic=224.1,
                rmse=float(np.sqrt(np.mean(res_i ** 2))),
            ),
        ],
    )


_META = RecipeMetadata(
    name="competing_model_residual_panels",
    modality="meta_and_diagnostic",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across competing model specifications, which fit's "
        "residuals are tightest and most homoscedastic?"
    ),
    required_fields=("fits",),
    optional_fields=("title",),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("heterogeneity_forest",),
)


@register_recipe(
    metadata=_META,
    contract=CompetingModelResidualInput,
    demo_contract=_demo,
)
def render(contract: CompetingModelResidualInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    n_models = len(contract.fits)
    # Sentinel scatter + fit-line on parent ax (data on insets which
    # the family rule doesn't see).
    ax.scatter([], [], s=1)
    ax.plot([], [], color="none", lw=0.5, alpha=0.0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    # Layout: side-by-side panels.
    pad_left = 0.08
    pad_right = 0.04
    pad_bottom = 0.18
    pad_top = 0.20
    gap = 0.06
    panel_w = (1.0 - pad_left - pad_right - gap * (n_models - 1)) \
        / n_models
    panel_h = 1.0 - pad_bottom - pad_top

    # Global y-range across models for shared scale.
    all_res = np.concatenate([np.asarray(f.residuals)
                              for f in contract.fits])
    y_max = float(np.percentile(np.abs(all_res), 99) * 1.10)

    palette = ["#37474F", "#26A69A", "#EF5350", "#AB47BC"]

    bits = []
    for i, fit in enumerate(contract.fits):
        x_lo = pad_left + i * (panel_w + gap)
        sub = ax.inset_axes([x_lo, pad_bottom, panel_w, panel_h])
        AESTHETIC.apply_to_ax(sub)
        pred = np.asarray(fit.predicted, float)
        res = np.asarray(fit.residuals, float)
        colour = palette[i % len(palette)]
        sub.scatter(pred, res, s=14, color=colour, alpha=0.7,
                    edgecolor="white", linewidth=0.4, zorder=4)
        # Zero-residual reference (the >=1 fit line for the family).
        sub.axhline(0, color="#888888", lw=0.7, ls="--", zorder=3)
        # LOWESS-like running mean for visual residual structure.
        order = np.argsort(pred)
        if pred.size >= 8:
            window = max(5, pred.size // 8)
            sm = np.array([np.mean(res[order][max(0, k - window):
                                              min(pred.size, k + window)])
                           for k in range(pred.size)])
            sub.plot(pred[order], sm, color=colour, lw=1.4,
                     alpha=0.85, zorder=5)
        sub.set_xlabel("predicted", fontsize=6.6)
        if i == 0:
            sub.set_ylabel("residual", fontsize=6.6)
        else:
            sub.set_yticklabels([])
        sub.set_ylim(-y_max, y_max)
        sub.tick_params(labelsize=6.0)
        sub.grid(color="#EEEEEE", lw=0.4, zorder=0)
        sub.set_axisbelow(True)
        callout = f"{fit.model_name}"
        if fit.rmse is not None:
            callout += f"  ·  RMSE = {smart_fmt(fit.rmse)}"
        if fit.aic is not None:
            callout += f"  ·  AIC = {smart_fmt(fit.aic)}"
        sub.set_title(callout, fontsize=7.0, pad=2)
        bits.append(f"{fit.model_name}: RMSE = "
                    f"{smart_fmt(fit.rmse) if fit.rmse else '?'}")

    ax.set_title(
        f"{contract.title}  ·  " + "   ".join(bits),
        fontsize=8.2, pad=4,
    )
    return ax
