"""Seed stability + geometric-orthogonal support panel.

Two-column composite:
  Left:  per-seed dot plot per output (typically 4–6 outputs × 3–10 seeds)
  Right: CV vs target CV ceiling bar
"""

from __future__ import annotations

from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class SeedStabilityInput(RecipeContract):
    outputs: list[str] = Field(description="Output names, e.g. ['stand-off', 'MT alignment']")
    seeds: list[int]
    seed_values: list[list[float]] = Field(
        description="seed_values[seed_idx][output_idx]"
    )
    target_cv: list[float] | None = Field(
        default=None, description="Target CV per output (same length as outputs)"
    )
    cv_ceiling: float = 0.10
    title: str = "Seed stability + geometric-orthogonal support"


def _demo() -> SeedStabilityInput:
    import random
    rng = random.Random(42)
    seeds = [42, 17, 99, 256, 1337]
    outputs = ["stand-off", "MT alignment", "buckling λ_c", "confinement ratio"]
    base = [0.42, 0.55, 1.8, 1.1]
    seed_values = [
        [b * (1 + rng.gauss(0, 0.025)) for b in base]
        for _ in seeds
    ]
    return SeedStabilityInput(
        outputs=outputs, seeds=seeds, seed_values=seed_values,
        target_cv=[0.04, 0.05, 0.07, 0.06], cv_ceiling=0.10,
        title="Seed stability + geometric-only orthogonal support (CV<0.10)",
    )


_META = RecipeMetadata(
    name="seed_stability_orthogonal_panel",
    modality="meta_and_diagnostic",
    family=RecipeFamily.coef_forest,
    answers_question="How stable are the model outputs across random seeds?",
    required_fields=("outputs", "seeds", "seed_values"),
    optional_fields=("target_cv", "cv_ceiling", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("sensitivity_leave_one_out",),
)


@register_recipe(metadata=_META, contract=SeedStabilityInput, demo_contract=_demo)
def render(contract: SeedStabilityInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        fig, ax = plt.subplots(figsize=(11, 4.5))
    else:
        fig = ax.figure
    AESTHETIC.apply_to_ax(ax)
    ax.axis("off")

    n_seeds = len(contract.seeds)
    n_outputs = len(contract.outputs)
    sv = np.asarray(contract.seed_values)  # (n_seeds, n_outputs)
    cvs = sv.std(0) / (np.abs(sv.mean(0)) + 1e-12)
    bases = sv.mean(0)

    gs = fig.add_gridspec(1, 2, wspace=0.30, left=0.08, right=0.97,
                          top=0.86, bottom=0.12)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    AESTHETIC.apply_to_ax(ax1)
    AESTHETIC.apply_to_ax(ax2)

    rng = np.random.default_rng(42)
    for j in range(n_outputs):
        for i in range(n_seeds):
            ax1.scatter(j + rng.uniform(-0.12, 0.12, 1), sv[i, j],
                        s=44, color="#5b8aa4", edgecolor="white", alpha=0.85)
        ax1.hlines(bases[j], j - 0.22, j + 0.22, colors="#1f6f8b", linewidth=2)
    ax1.set_xticks(range(n_outputs))
    ax1.set_xticklabels(contract.outputs, rotation=12, fontsize=8.4)
    ax1.set_ylabel("Output value (per seed)")
    ax1.set_title(f"Per-seed stability (n={n_seeds} seeds)", fontsize=9.6, color="#2c3e50")
    ax1.spines[["top", "right"]].set_visible(False)

    y = np.arange(n_outputs)[::-1]
    ax2.barh(y, cvs, color="#aaa", edgecolor="#666",
             linewidth=0.5, label="observed CV")
    if contract.target_cv:
        ax2.scatter(contract.target_cv, y, color="#c0392b", s=60,
                    label="target CV", zorder=3)
    ax2.axvline(contract.cv_ceiling, ls="--", color="#888", lw=1.0,
                label=f"CV={contract.cv_ceiling} ceiling")
    ax2.set_yticks(y)
    ax2.set_yticklabels(contract.outputs, fontsize=8.4)
    ax2.set_xlabel("Coefficient of variation")
    ax2.set_title("Seed CV vs target", fontsize=9.6, color="#2c3e50")
    ax2.legend(fontsize=8.4, frameon=False, loc="lower right")
    ax2.spines[["top", "right"]].set_visible(False)

    fig.suptitle(contract.title, fontsize=9.6, color="#2c3e50", y=0.97)
    return ax
