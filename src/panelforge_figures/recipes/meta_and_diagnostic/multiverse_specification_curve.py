"""Multiverse specification curve — per-specification effect-size
scatter sorted by magnitude with shaded ROPE band, zero-effect
reference, and per-spec ROBUST / FRAGILE / NON_SIG colouring.

Scatter-collapse family: >=1 scatter + >=1 fit line.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import MultiverseSpec

_CLASS_COLOR = {
    "ROBUST": "#2E7D32",
    "FRAGILE": "#FB8C00",
    "NON_SIG": "#9E9E9E",
}


class MultiverseSpecCurveInput(RecipeContract):
    specs: list[MultiverseSpec] = Field(..., min_length=4)
    rope_lo: float = -0.10
    rope_hi: float = 0.10
    title: str = "Multiverse specification curve"


def _demo() -> MultiverseSpecCurveInput:
    rng = np.random.default_rng(805)
    specs: list[MultiverseSpec] = []
    # Mix of effect sizes to produce a sorted curve crossing the ROPE band.
    base_effects = np.concatenate([
        rng.normal(-0.05, 0.03, 5),     # NON_SIG cluster around 0
        rng.normal(0.20, 0.06, 10),     # FRAGILE / ROBUST around 0.20
        rng.normal(0.40, 0.06, 10),     # ROBUST around 0.40
    ])
    for k, eff in enumerate(base_effects):
        ci_half = 0.12 + abs(rng.normal(0, 0.02))
        if abs(eff) <= 0.10:
            cls = "NON_SIG"
        elif eff - ci_half <= 0.10:
            cls = "FRAGILE"
        else:
            cls = "ROBUST"
        specs.append(MultiverseSpec(
            spec_id=f"S{k:02d}",
            spec_label=f"spec {k:02d}",
            effect_size=float(eff),
            ci_lo=float(eff - ci_half),
            ci_hi=float(eff + ci_half),
            classification=cls,
        ))
    return MultiverseSpecCurveInput(specs=specs)


_META = RecipeMetadata(
    name="multiverse_specification_curve",
    modality="meta_and_diagnostic",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across analytical specifications, how does the per-spec "
        "effect-size estimate evolve when sorted by magnitude, and "
        "where does the curve cross the ROPE band?"
    ),
    required_fields=("specs",),
    optional_fields=("rope_lo", "rope_hi", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("multiverse_robustness_classification_bar",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=MultiverseSpecCurveInput,
    demo_contract=_demo,
)
def render(contract: MultiverseSpecCurveInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 3.8))
    AESTHETIC.apply_to_ax(ax)

    specs = list(contract.specs)
    # Sort by effect size ascending.
    specs.sort(key=lambda s: s.effect_size)
    n = len(specs)
    x = np.arange(n)
    eff = np.array([s.effect_size for s in specs])

    # ROPE shading.
    ax.axhspan(contract.rope_lo, contract.rope_hi,
               color="#888888", alpha=0.10, zorder=1,
               label=f"ROPE [{smart_fmt(contract.rope_lo)}, "
                     f"{smart_fmt(contract.rope_hi)}]")

    # Zero-effect reference line.
    ax.axhline(0, color="#888888", lw=0.7, ls="--", zorder=2,
               label="zero effect")

    # Sorted-effect envelope (the >=1 fit line for the family).
    ax.plot(x, eff, color="#37474F", lw=1.2, alpha=0.85,
            zorder=4)

    # Per-spec scatter coloured by classification.
    for i, s in enumerate(specs):
        colour = _CLASS_COLOR.get(s.classification, "#888888")
        ax.scatter([x[i]], [s.effect_size],
                   s=44, color=colour, edgecolor="white",
                   linewidth=0.5, alpha=0.9, zorder=5)
        # CI segment.
        if s.ci_lo is not None and s.ci_hi is not None:
            ax.plot([x[i], x[i]], [s.ci_lo, s.ci_hi],
                    color=colour, lw=0.9, alpha=0.65, zorder=3)

    ax.set_xlabel("specification (sorted by effect size)")
    ax.set_ylabel("effect size")
    ax.set_xticks([])
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Per-class tally.
    tally = {"ROBUST": 0, "FRAGILE": 0, "NON_SIG": 0}
    for s in specs:
        if s.classification in tally:
            tally[s.classification] += 1

    # Class-colour legend handles.
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=_CLASS_COLOR[c],
               markeredgecolor="white", markersize=6,
               label=f"{c} ({tally[c]})")
        for c in ("ROBUST", "FRAGILE", "NON_SIG")
    ]
    handles.append(Line2D([0], [0], color="#888888", ls="--", lw=0.7,
                          label="zero effect"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper left", handlelength=1.2)

    bits = "  ".join(
        f"{c}: {tally[c]}" for c in ("ROBUST", "FRAGILE", "NON_SIG")
    )
    ax.set_title(
        f"{contract.title}  ·  n = {n} specs  ·  {bits}",
        fontsize=8.2, pad=4,
    )
    return ax
