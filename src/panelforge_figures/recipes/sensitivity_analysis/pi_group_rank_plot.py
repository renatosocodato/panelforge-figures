"""Rank candidate Pi-group formulations by fit quality (R² + AIC)."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    callout_box,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PiGroupRankInput(RecipeContract):
    formulations: list[str] = Field(..., min_length=2)
    r2: list[float] = Field(...)
    aic: list[float] = Field(...)
    winner_label: str | None = None


def _demo() -> PiGroupRankInput:
    forms = [
        r"$\Pi_1 = k_{on}\,L/D$",
        r"$\Pi_2 = (k_{on}/k_{off})\,L^{2}/D$",
        r"$\Pi_3 = V_{max}\,L/(K_m D)$",
        r"$\Pi_4 = k_{on}\,L^{1.5}$",
        r"$\Pi_5 = D/(k_{on}\,L)$",
    ]
    r2 = [0.41, 0.82, 0.96, 0.58, 0.12]
    aic = [118, 72, 32, 95, 180]
    return PiGroupRankInput(
        formulations=forms,
        r2=r2,
        aic=aic,
        winner_label=forms[2],
    )


_META = RecipeMetadata(
    name="pi_group_rank_plot",
    modality="sensitivity_analysis",
    family=RecipeFamily.ladder,
    answers_question="Among candidate dimensionless Pi-group formulations, which collapses the data best by R² and AIC?",
    required_fields=("formulations", "r2", "aic"),
    optional_fields=("winner_label",),
    file_format_hints=("csv",),
    alternatives_in_modality=("dimensionless_pi_group_collapse",),
)


@register_recipe(metadata=_META, contract=PiGroupRankInput, demo_contract=_demo)
def render(contract: PiGroupRankInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 3.4))
    AESTHETIC.apply_to_ax(ax)

    palette = get_palette(AESTHETIC.primary_palette)
    r2 = np.array(contract.r2)
    aic = np.array(contract.aic)
    # AIC normalized for visual comparison (lower is better).
    aic_norm = (aic.max() - aic) / max(aic.max() - aic.min(), 1e-9)
    order = np.argsort(-r2)
    forms = [contract.formulations[i] for i in order]
    r2 = r2[order]
    aic_norm = aic_norm[order]
    aic_raw = aic[order]

    y = np.arange(len(forms))
    bar_h = 0.35

    for yi, rr, an, ar in zip(y, r2, aic_norm, aic_raw):
        color = palette[1] if rr >= 0.9 else ("#888888" if rr < 0.5 else palette[2])
        ax.barh(yi - bar_h / 2, rr, height=bar_h, color=color, alpha=0.9,
                edgecolor="white", linewidth=0.6)
        ax.barh(yi + bar_h / 2, an, height=bar_h, color="#9E9E9E",
                alpha=0.85, edgecolor="white", linewidth=0.6)
        ax.text(rr + 0.015, yi - bar_h / 2, f"R²={smart_fmt(rr)}",
                va="center", ha="left", fontsize=6.8, color=color)
        ax.text(an + 0.015, yi + bar_h / 2, f"AIC={int(ar)}",
                va="center", ha="left", fontsize=6.8, color="#555555")

    ax.set_yticks(y)
    ax.set_yticklabels(forms, fontsize=7.4)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.25)
    ax.set_xlabel("R² / normalized AIC (higher is better)")
    ax.set_title("Pi-group formulations ranked", fontsize=9.0)
    ax.axvline(0.9, color="#D32F2F", ls="--", lw=0.8)

    if contract.winner_label is not None:
        callout_box(
            ax,
            0.03,
            0.03,
            f"Best collapse: {contract.winner_label}",
            accent="#388E3C",
            transform=ax.transAxes,
        )
    ax.grid(axis="x", color="#DDDDDD", lw=0.4)
    ax.set_axisbelow(True)
    return ax
