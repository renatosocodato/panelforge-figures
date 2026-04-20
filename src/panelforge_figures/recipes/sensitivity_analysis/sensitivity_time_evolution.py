"""Time-resolved Sobol indices — S1(t) or ST(t) per parameter.

Rather than a scalar Sobol index per parameter (as in
`sobol_first_total_pair`), this recipe plots the Sobol index as a
function of the *output time* for a time-varying model. Each parameter
becomes one curve with an optional CI band; a stacked-ribbon secondary
view shows how the cumulative share of total variance is partitioned
over time.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class SensTimeInput(RecipeContract):
    time: list[float] = Field(..., min_length=3)
    parameter_names: list[str] = Field(..., min_length=2)
    indices: list[list[float]] = Field(
        ..., description="n_params × n_time sensitivity index curves"
    )
    ci_width: list[list[float]] | None = Field(
        None, description="optional per-param × per-t CI width"
    )
    index_label: str = r"$S_T$"
    time_label: str = "time (s)"
    title: str = "Time-resolved sensitivity"


def _demo() -> SensTimeInput:
    rng = np.random.default_rng(1019)
    t = np.linspace(0, 60, 60).tolist()
    tau = np.asarray(t)
    names = ["k_on", "V_max", "Km", "k_off", "D"]
    # Each parameter dominates at different output times.
    idx = np.zeros((len(names), tau.size))
    idx[0] = 0.5 * np.exp(-((tau - 8) / 4) ** 2)
    idx[1] = 0.55 / (1 + np.exp(-(tau - 30) / 5))
    idx[2] = 0.30 * np.exp(-((tau - 40) / 10) ** 2)
    idx[3] = 0.15 + 0.05 * np.sin(tau / 8)
    idx[4] = 0.08 + 0.02 * np.cos(tau / 12)
    idx = np.clip(idx + rng.normal(0, 0.015, idx.shape), 0, None)
    # Normalize per-t so they approximately sum to ≤1 (sensitivity-share).
    s = idx.sum(axis=0)
    scale = np.where(s > 1.0, s, 1.0)
    idx = idx / scale
    ci = 0.05 * np.ones_like(idx)
    return SensTimeInput(
        time=t,
        parameter_names=names,
        indices=idx.tolist(),
        ci_width=ci.tolist(),
    )


_META = RecipeMetadata(
    name="sensitivity_time_evolution",
    modality="sensitivity_analysis",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question=(
        "For a time-resolved output, how do the Sobol indices of each "
        "parameter evolve over the output time axis?"
    ),
    required_fields=("time", "parameter_names", "indices"),
    optional_fields=("ci_width", "index_label", "time_label", "title"),
    file_format_hints=("parquet", "npz"),
    alternatives_in_modality=(
        "sobol_first_total_pair",
        "convergence_diagnostic_sobol",
    ),
)


@register_recipe(
    metadata=_META,
    contract=SensTimeInput,
    demo_contract=_demo,
)
def render(contract: SensTimeInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.8, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    t = np.asarray(contract.time, float)
    idx = np.asarray(contract.indices, float)
    widths = (np.asarray(contract.ci_width, float)
              if contract.ci_width is not None else None)
    names = contract.parameter_names

    # Curves with CI bands.
    for i, name in enumerate(names):
        color = palette[i % len(palette.colors)]
        if widths is not None:
            ax.fill_between(t, np.clip(idx[i] - widths[i] / 2, 0, 1),
                            np.clip(idx[i] + widths[i] / 2, 0, 1),
                            color=color, alpha=0.18, linewidth=0, zorder=2)
        ax.plot(t, idx[i], color=color, lw=1.2, zorder=3, label=name)

    # Peak-time callouts.
    for i, name in enumerate(names):
        k = int(np.argmax(idx[i]))
        ax.scatter([t[k]], [idx[i, k]], s=18, marker="o",
                   color=palette[i % len(palette.colors)],
                   edgecolor="white", linewidth=0.7, zorder=4)

    ax.set_xlabel(contract.time_label)
    ax.set_ylabel(contract.index_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(t.min(), t.max())
    ax.set_ylim(0, max(idx.max() * 1.12, 0.05))
    ax.legend(fontsize=6.6, frameon=False, loc="center left",
              bbox_to_anchor=(1.02, 0.5), handlelength=1.6)
    ax.grid(color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Below-axis callout: dominant driver per time window.
    edges = [t.min(), 0.5 * (t.min() + t.max()), t.max()]
    windows = []
    for a, b in zip(edges[:-1], edges[1:]):
        mask = (t >= a) & (t <= b)
        share = idx[:, mask].mean(axis=1)
        top_i = int(np.argmax(share))
        windows.append(
            f"[{smart_fmt(a)}, {smart_fmt(b)}]: "
            f"{names[top_i]} ({smart_fmt(share[top_i])})"
        )
    fig = ax.figure
    fig.text(
        0.5, -0.18,
        "   ·   ".join(windows),
        ha="center", va="top", fontsize=6.6, color="#333333",
        transform=ax.transAxes,
        bbox=dict(boxstyle="round,pad=0.24", fc="white",
                  ec=AESTHETIC.annotation_style.callout_accent, lw=0.5),
    )
    return ax
