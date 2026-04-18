"""Master-curve collapse — different conditions fall onto one curve when rescaled."""

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


class MasterCurveInput(RecipeContract):
    conditions: dict[str, dict[str, list[float]]] = Field(
        ..., description="condition -> {'x': [...], 'y': [...]}"
    )
    x_scale: dict[str, float] = Field(
        ..., description="condition -> scaling factor applied to x"
    )
    y_scale: dict[str, float] = Field(
        ..., description="condition -> scaling factor applied to y"
    )
    x_label: str = "x / x₀"
    y_label: str = "y / y₀"
    title: str = "Master-curve collapse"


def _demo() -> MasterCurveInput:
    rng = np.random.default_rng(83)
    x_master = np.logspace(-1, 1.5, 50)
    conditions: dict[str, dict[str, list[float]]] = {}
    xs: dict[str, float] = {}
    ys: dict[str, float] = {}
    for i, label in enumerate(["T = 20°C", "T = 30°C", "T = 40°C", "T = 50°C"]):
        x_sc = (i + 1) * 0.75
        y_sc = (i + 1) * 1.2
        x = x_master * x_sc
        y = (0.8 * np.log1p(x_master * 2) + 0.5) * y_sc * np.exp(rng.normal(0, 0.05, x_master.size))
        conditions[label] = {"x": x.tolist(), "y": y.tolist()}
        xs[label] = x_sc
        ys[label] = y_sc
    return MasterCurveInput(
        conditions=conditions,
        x_scale=xs,
        y_scale=ys,
        x_label=r"x / x$_0$",
        y_label=r"y / y$_0$",
    )


_META = RecipeMetadata(
    name="master_curve_collapse",
    modality="biophysics_scaling",
    family=RecipeFamily.scatter_collapse,
    answers_question="When rescaled by the proposed laws, do experiments under different conditions collapse onto a single master curve?",
    required_fields=("conditions", "x_scale", "y_scale"),
    optional_fields=("x_label", "y_label", "title"),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("log_log_scaling_with_slope_box",),
)


@register_recipe(metadata=_META, contract=MasterCurveInput, demo_contract=_demo)
def render(contract: MasterCurveInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.4))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    for i, (label, data) in enumerate(contract.conditions.items()):
        x = np.array(data["x"], dtype=float) / contract.x_scale[label]
        y = np.array(data["y"], dtype=float) / contract.y_scale[label]
        color = palette[i % len(palette.colors)]
        ax.scatter(x, y, s=22, color=color, alpha=0.7,
                   edgecolor="white", linewidth=0.5, label=label,
                   zorder=3)

    # Quality metric: compute per-x variance across conditions after rescaling.
    # Small inter-condition scatter = successful collapse.
    x_pooled = np.sort(
        np.concatenate([
            np.array(d["x"]) / contract.x_scale[lbl]
            for lbl, d in contract.conditions.items()
        ])
    )
    bins = np.logspace(np.log10(x_pooled.min()), np.log10(x_pooled.max()), 20)
    cvs = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        ys_in_bin = []
        for lbl, d in contract.conditions.items():
            x = np.array(d["x"]) / contract.x_scale[lbl]
            y = np.array(d["y"]) / contract.y_scale[lbl]
            mask = (x >= lo) & (x < hi)
            if mask.any():
                ys_in_bin.append(np.mean(y[mask]))
        if len(ys_in_bin) >= 2:
            ys_in_bin = np.array(ys_in_bin)
            cv = np.std(ys_in_bin) / max(abs(np.mean(ys_in_bin)), 1e-9)
            cvs.append(cv)
    cv_mean = float(np.mean(cvs)) if cvs else np.nan

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(contract.x_label)
    ax.set_ylabel(contract.y_label)
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              ncol=2, handlelength=1.6, columnspacing=1.0)

    ax.text(0.02, 0.97,
            f"collapse CV = {smart_fmt(cv_mean)}",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=6.8, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=5)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
