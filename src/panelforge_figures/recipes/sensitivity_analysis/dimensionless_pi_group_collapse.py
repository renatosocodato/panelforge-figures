"""Collapse multiple experiments onto one master curve via a Pi-group."""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    bootstrap_ci,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class PiGroupCollapseInput(RecipeContract):
    experiments: dict[str, tuple[list[float], list[float]]] = Field(
        ..., description="label → (pi_group_values, output_values)"
    )
    pi_label: str = r"Π"
    output_label: str = "output"
    fit_line: bool = True


def _demo() -> PiGroupCollapseInput:
    rng = np.random.default_rng(19)
    experiments: dict[str, tuple[list[float], list[float]]] = {}
    for name, shift in zip(["Exp A", "Exp B", "Exp C", "Exp D"], [0, 0, 0, 0]):
        x = np.logspace(-1, 1.5, 30)
        y = 0.8 * np.log(x + 0.5) + 1.0 + rng.normal(0, 0.08, x.size) + shift
        experiments[name] = (x.tolist(), y.tolist())
    return PiGroupCollapseInput(
        experiments=experiments,
        pi_label=r"$\Pi = k_{on}\, L / D$",
        output_label="dimensionless gain",
    )


_META = RecipeMetadata(
    name="dimensionless_pi_group_collapse",
    modality="sensitivity_analysis",
    family=RecipeFamily.scatter_collapse,
    answers_question="Do multiple experiments collapse onto one master curve when plotted against a dimensionless Pi group?",
    required_fields=("experiments",),
    optional_fields=("pi_label", "output_label", "fit_line"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("pi_group_rank_plot", "fast_subspace_detection"),
)


@register_recipe(metadata=_META, contract=PiGroupCollapseInput, demo_contract=_demo)
def render(contract: PiGroupCollapseInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    all_x: list[float] = []
    all_y: list[float] = []
    for i, (label, (x, y)) in enumerate(contract.experiments.items()):
        color = palette[i]
        ax.scatter(x, y, color=color, s=26, edgecolor="white", linewidth=0.5,
                   label=label, alpha=0.9, zorder=3)
        all_x.extend(x)
        all_y.extend(y)

    xs = np.array(all_x)
    ys = np.array(all_y)
    if contract.fit_line and xs.size > 6:
        xg, mean, lo, hi = bootstrap_ci(np.log(xs + 1e-9), ys, fit="linear", n_resamples=250)
        ax.fill_between(np.exp(xg), lo, hi, color="#999999", alpha=0.18, zorder=2)
        ax.plot(np.exp(xg), mean, color="#333333", lw=1.6, zorder=4)
        r2 = _r2(np.log(xs + 1e-9), ys)
        add_halo_label(
            ax,
            xs.mean(),
            ys.mean(),
            f"R² = {smart_fmt(r2)}",
            color="#333333",
            fontsize=7.4,
            fontweight="bold",
            halo_width=2.6,
        )
    ax.set_xscale("log")
    ax.set_xlabel(contract.pi_label)
    ax.set_ylabel(contract.output_label)
    ax.set_title("Master-curve collapse", fontsize=9.0, fontweight="bold")
    ax.legend(fontsize=7.0, frameon=False, ncol=2, loc="lower right")
    ax.grid(axis="both", color="#DDDDDD", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax


def _r2(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 2 or np.nanstd(x) == 0:
        return 0.0
    m, b = np.polyfit(x, y, 1)
    yhat = m * x + b
    ss_res = np.nansum((y - yhat) ** 2)
    ss_tot = np.nansum((y - np.nanmean(y)) ** 2)
    return float(1 - ss_res / max(ss_tot, 1e-12))
