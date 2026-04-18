"""MSD by condition — log-log mean-squared-displacement with α exponent annotation."""

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


class MSDInput(RecipeContract):
    lag_s: list[float] = Field(...)
    msd_by_condition: dict[str, dict[str, list[float]]] = Field(
        ..., description="condition → {'mean', 'sem'} MSD values in μm²"
    )
    title: str = "MSD by condition"


def _demo() -> MSDInput:
    rng = np.random.default_rng(359)
    lags = np.logspace(-1, 2, 30)       # 0.1-100 s
    data: dict[str, dict[str, list[float]]] = {}
    for name, alpha, D in [
        ("free",        1.00, 0.06),
        ("confined",    0.55, 0.04),
        ("directed",    1.80, 0.10),
    ]:
        msd = 4 * D * lags ** alpha * np.exp(rng.normal(0, 0.05, lags.size))
        sem = msd * 0.10
        data[name] = {"mean": msd.tolist(), "sem": sem.tolist()}
    return MSDInput(
        lag_s=lags.tolist(),
        msd_by_condition=data,
    )


_META = RecipeMetadata(
    name="msd_by_condition",
    modality="diffusion_and_tracking",
    family=RecipeFamily.diagnostic_curve,
    answers_question="How does mean-squared-displacement scale with lag-time across conditions, and what is each condition's exponent α?",
    required_fields=("lag_s", "msd_by_condition"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("step_size_distribution",),
)


@register_recipe(metadata=_META, contract=MSDInput, demo_contract=_demo)
def render(contract: MSDInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    lags = np.array(contract.lag_s, dtype=float)

    for i, (name, data) in enumerate(contract.msd_by_condition.items()):
        color = palette[i % len(palette.colors)]
        mean = np.array(data["mean"], dtype=float)
        sem = np.array(data["sem"], dtype=float)
        ax.fill_between(lags, np.maximum(mean - sem, 1e-6), mean + sem,
                        color=color, alpha=0.18, linewidth=0, zorder=2)
        # Fit exponent.
        slope, intercept = np.polyfit(np.log(lags), np.log(mean), 1)
        ax.plot(lags, mean, color=color, lw=1.2, zorder=3,
                label=rf"{name} ($\alpha$={smart_fmt(float(slope))})")

    # Reference slopes.
    ax.loglog(lags, 0.01 * lags ** 1.0, color="#888888", lw=0.6, ls="--",
              zorder=1)
    ax.text(lags[-1], 0.01 * lags[-1] ** 1.0 * 1.05,
            r"$\alpha$=1 (Brownian)",
            ha="right", va="bottom", fontsize=6.2, color="#666666")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"lag time $\tau$ (s)")
    ax.set_ylabel(r"MSD ($\mu$m$^2$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.8)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
