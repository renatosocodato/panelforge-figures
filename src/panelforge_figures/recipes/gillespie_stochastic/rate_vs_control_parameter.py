"""Rate vs control parameter — transition rate with error ribbons across conditions."""

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


class RateVsControlInput(RecipeContract):
    control: list[float] = Field(...)
    rates_by_transition: dict[str, dict[str, list[float]]] = Field(
        ..., description="transition → {mean, lo, hi} arrays aligned to control"
    )
    control_label: str = "control parameter"
    rate_label: str = "transition rate (1/s)"
    title: str = "Transition rates"


def _demo() -> RateVsControlInput:
    x = np.linspace(0.1, 2.0, 20)
    rng = np.random.default_rng(119)
    rates: dict[str, dict[str, list[float]]] = {}
    for name, k0, slope in [
        ("HOME to GATE", 0.08, 0.55),
        ("GATE to HOME", 0.30, -0.10),
        ("GATE to TRAP", 0.05, 0.40),
    ]:
        mean = k0 + slope * x + rng.normal(0, 0.02, x.size)
        mean = np.clip(mean, 0.001, None)
        lo = mean * 0.8
        hi = mean * 1.2
        rates[name] = {"mean": mean.tolist(), "lo": lo.tolist(), "hi": hi.tolist()}
    return RateVsControlInput(
        control=x.tolist(),
        rates_by_transition=rates,
        control_label="RhoGDI release",
    )


_META = RecipeMetadata(
    name="rate_vs_control_parameter",
    modality="gillespie_stochastic",
    family=RecipeFamily.timecourse_hierarchical_ci,
    answers_question="How do per-transition rates depend on a control parameter, with bootstrap uncertainty?",
    required_fields=("control", "rates_by_transition"),
    optional_fields=("control_label", "rate_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("trajectory_fan_with_fpt",),
)


@register_recipe(metadata=_META, contract=RateVsControlInput, demo_contract=_demo)
def render(contract: RateVsControlInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    x = np.array(contract.control, dtype=float)
    pal = [palette.pick("HOME"), palette.pick("GATE"), palette.pick("TRAP")]

    for i, (name, data) in enumerate(contract.rates_by_transition.items()):
        color = pal[i % len(pal)]
        mean = np.array(data["mean"], dtype=float)
        lo = np.array(data["lo"], dtype=float)
        hi = np.array(data["hi"], dtype=float)
        ax.fill_between(x, lo, hi, color=color, alpha=0.20,
                        linewidth=0, zorder=2)
        ax.plot(x, mean, color=color, lw=1.2, label=name, zorder=3)

    ax.set_xlabel(contract.control_label)
    ax.set_ylabel(contract.rate_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left",
              handlelength=1.8)

    # Max rate callout.
    max_name, max_val = max(
        ((n, np.max(d["mean"])) for n, d in contract.rates_by_transition.items()),
        key=lambda t: t[1],
    )
    ax.text(0.99, 0.02,
            f"peak: {max_name} = {smart_fmt(float(max_val))}/s",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.20", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
