"""Drug-combination heatmap — effect surface over dose_A × dose_B with Bliss overlay."""

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


class DrugComboInput(RecipeContract):
    doses_A: list[float]
    doses_B: list[float]
    effect: list[list[float]] = Field(
        ..., description="effect[j][i] = fractional inhibition at (doses_A[i], doses_B[j])"
    )
    drug_a_name: str = "Drug A"
    drug_b_name: str = "Drug B"
    title: str = "Combination effect surface"


def _demo() -> DrugComboInput:
    a = np.array([0, 10, 30, 100, 300, 1000], dtype=float)
    b = np.array([0, 10, 30, 100, 300, 1000], dtype=float)
    A, B = np.meshgrid(a, b)
    # Fractional inhibition surface with synergy bias in the middle.
    Ea = A / (A + 150)
    Eb = B / (B + 400)
    Ebliss = Ea + Eb - Ea * Eb
    synergy_bias = 0.12 * np.exp(-((A - 150) ** 2 / 30000 + (B - 200) ** 2 / 60000))
    E = np.clip(Ebliss + synergy_bias, 0, 1)
    return DrugComboInput(
        doses_A=a.tolist(),
        doses_B=b.tolist(),
        effect=E.tolist(),
        drug_a_name="CompoundA",
        drug_b_name="CompoundB",
    )


_META = RecipeMetadata(
    name="drug_combo_heatmap",
    modality="dose_response_pharmacology",
    family=RecipeFamily.heatmap,
    answers_question="Where in the 2D dose-combination plane is the effect strongest, and where does the combination produce synergy?",
    required_fields=("doses_A", "doses_B", "effect"),
    optional_fields=("drug_a_name", "drug_b_name", "title"),
    file_format_hints=("csv", "npz"),
    alternatives_in_modality=("isobologram_combination",),
)


@register_recipe(metadata=_META, contract=DrugComboInput, demo_contract=_demo)
def render(contract: DrugComboInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.6, 3.6))
    AESTHETIC.apply_to_ax(ax)

    a = np.array(contract.doses_A, dtype=float)
    b = np.array(contract.doses_B, dtype=float)
    E = np.array(contract.effect, dtype=float)
    im = ax.imshow(E, origin="lower", cmap=AESTHETIC.continuous_cmap,
                   vmin=0, vmax=1, aspect="auto", interpolation="nearest")

    # Cell value labels for readability.
    for (j, i), v in np.ndenumerate(E):
        text_color = "white" if v < 0.35 or v > 0.65 else "#1a1a1a"
        ax.text(i, j, smart_fmt(float(v)),
                ha="center", va="center",
                fontsize=5.8, color=text_color)

    ax.set_xticks(range(len(a)))
    ax.set_xticklabels([int(v) if v >= 1 else 0 for v in a], fontsize=6.6)
    ax.set_yticks(range(len(b)))
    ax.set_yticklabels([int(v) if v >= 1 else 0 for v in b], fontsize=6.6)
    ax.set_xlabel(f"{contract.drug_a_name} (nM)")
    ax.set_ylabel(f"{contract.drug_b_name} (nM)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("fractional inhibition", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.2)

    # Bliss-expectation label at Emax corner.
    j_best, i_best = np.unravel_index(np.argmax(E), E.shape)
    ax.text(i_best, j_best,
            f"{smart_fmt(E[j_best, i_best])}",
            ha="center", va="center",
            color="white", fontsize=6.4,
            bbox=dict(boxstyle="round,pad=0.16", fc="#C62828",
                      ec="none", alpha=0.82),
            zorder=5)
    return ax
