"""G-function curves panel — empirical NN-distance survival curves per group."""

from __future__ import annotations

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class GFunctionCurve(RecipeContract):
    label: str
    radius_um: list[float]
    G_value: list[float]
    G_envelope_lo: list[float] | None = None
    G_envelope_hi: list[float] | None = None


class GFunctionCurvesInput(RecipeContract):
    curves: list[GFunctionCurve]
    title: str = "G-function (NN-distance CDF) per genotype"


def _demo() -> GFunctionCurvesInput:
    import math
    r = [0.05 * i for i in range(1, 41)]
    # CSR-like baselines
    def csr_g(r, lam):
        return [1 - math.exp(-lam * 3.14159 * x ** 2) for x in r]
    return GFunctionCurvesInput(
        curves=[
            GFunctionCurve(label="WT (actin)", radius_um=r, G_value=csr_g(r, 0.8)),
            GFunctionCurve(label="LI (actin)", radius_um=r, G_value=csr_g(r, 1.2)),
            GFunctionCurve(label="WT (MT)",    radius_um=r, G_value=csr_g(r, 0.5)),
            GFunctionCurve(label="LI (MT)",    radius_um=r, G_value=csr_g(r, 0.7)),
        ],
    )


_META = RecipeMetadata(
    name="g_function_curves_panel",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="What are the empirical nearest-neighbor distance CDFs per group?",
    required_fields=("curves",),
    optional_fields=("title",),
    file_format_hints=("csv", "json"),
)


_PALETTE = ["#1f6f8b", "#c0392b", "#5b8aa4", "#e58e7d", "#666", "#aaa"]


@register_recipe(metadata=_META, contract=GFunctionCurvesInput, demo_contract=_demo)
def render(contract: GFunctionCurvesInput, ax=None, **_):
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(7.5, 5.0))
    AESTHETIC.apply_to_ax(ax)

    for i, c in enumerate(contract.curves):
        color = _PALETTE[i % len(_PALETTE)]
        ax.plot(c.radius_um, c.G_value, lw=1.5, color=color, label=c.label)
        if c.G_envelope_lo and c.G_envelope_hi:
            ax.fill_between(c.radius_um, c.G_envelope_lo, c.G_envelope_hi,
                            color=color, alpha=0.15, edgecolor="none")
    ax.set_xlabel("radius r (μm)")
    ax.set_ylabel("G(r) — empirical CDF")
    ax.set_ylim(0, 1.05)
    ax.set_title(contract.title, fontsize=9.6, color="#2c3e50", pad=6)
    ax.legend(fontsize=9.0, frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    return ax
