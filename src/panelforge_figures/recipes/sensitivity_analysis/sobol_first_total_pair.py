"""Paired Sobol S1 / ST bars with confidence intervals, sorted by ST."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    callout_box,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SobolIndicesInput(RecipeContract):
    parameter_names: list[str] = Field(..., min_length=2)
    S1: list[float] = Field(..., description="first-order Sobol index")
    ST: list[float] = Field(..., description="total-order Sobol index")
    S1_ci: list[tuple[float, float]] | None = None
    ST_ci: list[tuple[float, float]] | None = None
    output_label: str = "target output"


def _demo() -> SobolIndicesInput:
    rng = np.random.default_rng(7)
    params = ["k_on", "k_off", "V_max", "Km", "D", "alpha", "beta", "gamma"]
    s1 = np.array([0.42, 0.05, 0.18, 0.08, 0.01, 0.12, 0.003, 0.02])
    st = s1 + rng.uniform(0.02, 0.15, s1.size) + np.array([0.0, 0.08, 0.05, 0.22, 0.01, 0.06, 0.01, 0.03])
    s1_ci = [(v - 0.015, v + 0.02) for v in s1]
    st_ci = [(v - 0.02, v + 0.03) for v in st]
    return SobolIndicesInput(
        parameter_names=params,
        S1=s1.tolist(),
        ST=st.tolist(),
        S1_ci=s1_ci,
        ST_ci=st_ci,
        output_label="steady-state activity",
    )


_META = RecipeMetadata(
    name="sobol_first_total_pair",
    modality="sensitivity_analysis",
    family=RecipeFamily.sobol_bar,
    answers_question="Which parameters carry most of the variance in the output directly (S1) and via interactions (ST)?",
    required_fields=("parameter_names", "S1", "ST"),
    optional_fields=("S1_ci", "ST_ci", "output_label"),
    file_format_hints=("parquet", "csv", "pickle"),
    n_points_typical="8-30 parameters",
    alternatives_in_modality=("morris_elementary_effects", "interaction_matrix_sobol"),
    example_manifest="skill/example_manifests/sensitivity_analysis_manuscript.yaml",
)


@register_recipe(metadata=_META, contract=SobolIndicesInput, demo_contract=_demo)
def render(contract: SobolIndicesInput, ax=None, **_):
    """Horizontal paired bars: S1 (lighter) + ST (darker), sorted by ST."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)
    import matplotlib as mpl

    s1 = np.array(contract.S1, dtype=float)
    st = np.array(contract.ST, dtype=float)
    names = list(contract.parameter_names)
    order = np.argsort(-st)            # highest ST at top
    s1 = s1[order]
    st = st[order]
    names = [names[i] for i in order]
    s1_ci = [contract.S1_ci[i] for i in order] if contract.S1_ci else None
    st_ci = [contract.ST_ci[i] for i in order] if contract.ST_ci else None

    cmap = mpl.colormaps[AESTHETIC.continuous_cmap]
    ypos = np.arange(len(names))
    bar_h = 0.36

    for y, v_s1, v_st in zip(ypos, s1, st):
        col_s1 = cmap(0.25 + 0.5 * v_s1 / max(st.max(), 1e-9))
        col_st = cmap(0.55 + 0.4 * v_st / max(st.max(), 1e-9))
        ax.barh(y + bar_h / 2, v_st, height=bar_h, color=col_st,
                edgecolor="white", linewidth=0.6, zorder=3)
        ax.barh(y - bar_h / 2, v_s1, height=bar_h, color=col_s1,
                edgecolor="white", linewidth=0.6, zorder=3)

    # CI whiskers.
    if s1_ci is not None:
        for y, (lo, hi) in zip(ypos - bar_h / 2, s1_ci):
            ax.plot([lo, hi], [y, y], color="#333333", lw=1.0, zorder=4)
            ax.plot([lo, lo], [y - 0.07, y + 0.07], color="#333333", lw=1.0)
            ax.plot([hi, hi], [y - 0.07, y + 0.07], color="#333333", lw=1.0)
    if st_ci is not None:
        for y, (lo, hi) in zip(ypos + bar_h / 2, st_ci):
            ax.plot([lo, hi], [y, y], color="#333333", lw=1.0, zorder=4)
            ax.plot([lo, lo], [y - 0.07, y + 0.07], color="#333333", lw=1.0)
            ax.plot([hi, hi], [y - 0.07, y + 0.07], color="#333333", lw=1.0)

    # Value labels right of each ST bar.
    for y, v_st in zip(ypos, st):
        ax.text(v_st + max(st.max() * 0.02, 0.01), y + bar_h / 2,
                rf"$S_T$={smart_fmt(v_st)}", va="center", ha="left",
                fontsize=6.8, color="#222222", fontweight="bold")
    for y, v_s1 in zip(ypos, s1):
        ax.text(v_s1 + max(s1.max() * 0.02, 0.01), y - bar_h / 2,
                rf"$S_1$={smart_fmt(v_s1)}", va="center", ha="left",
                fontsize=6.4, color="#555555")

    ax.set_yticks(ypos)
    ax.set_yticklabels(names, fontsize=7.6)
    ax.invert_yaxis()
    xmax = max(st.max(), s1.max()) * 1.25
    ax.set_xlim(0, xmax)
    ax.set_xlabel("Sobol index")
    ax.set_title(
        f"Global sensitivity — {contract.output_label}",
        fontsize=9.0,
        fontweight="bold",
    )

    # Top-drivers callout — inside lower-right, after ensuring xmax has headroom.
    share_top3 = st[:3].sum() / max(st.sum(), 1e-9)
    callout_box(
        ax,
        0.98,
        0.02,
        f"Top 3 drivers ({', '.join(names[:3])})\n"
        f"account for {share_top3*100:.0f}% of total variance.",
        accent=AESTHETIC.annotation_style.callout_accent,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
    )
    ax.grid(axis="x", color="#DDDDDD", lw=0.4)
    ax.set_axisbelow(True)
    return ax
