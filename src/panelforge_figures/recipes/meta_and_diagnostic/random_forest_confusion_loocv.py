"""Random-forest LOOCV confusion matrix — square heatmap with diagonal
accuracy + off-diagonal misclassification annotations and global
accuracy / macro-F1 callouts.

Matrix family: >=1 imshow OR >=4 cell patches.
"""

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


class RandomForestConfusionInput(RecipeContract):
    confusion_matrix: list[list[int]] = Field(
        ..., description="n_classes × n_classes count matrix",
    )
    class_labels: list[str]
    cv_label: str = "LOOCV"
    title: str = "Random-forest confusion matrix"


def _demo() -> RandomForestConfusionInput:
    rng = np.random.default_rng(441)
    classes = ["WT", "LI", "het"]
    n_per = [40, 35, 22]
    M = np.zeros((3, 3), int)
    # Diagonal-dominant with realistic off-diagonal structure.
    M[0, 0] = int(round(0.92 * n_per[0]))
    M[0, 1] = int(round(0.06 * n_per[0]))
    M[0, 2] = n_per[0] - M[0, 0] - M[0, 1]
    M[1, 0] = int(round(0.05 * n_per[1]))
    M[1, 1] = int(round(0.86 * n_per[1]))
    M[1, 2] = n_per[1] - M[1, 0] - M[1, 1]
    M[2, 0] = int(round(0.10 * n_per[2]))
    M[2, 1] = int(round(0.13 * n_per[2]))
    M[2, 2] = n_per[2] - M[2, 0] - M[2, 1]
    # Add small jitter while preserving row sums.
    _ = rng.normal(0, 0.5, 9)
    return RandomForestConfusionInput(
        confusion_matrix=M.tolist(),
        class_labels=classes,
        cv_label="LOOCV",
    )


_META = RecipeMetadata(
    name="random_forest_confusion_loocv",
    modality="meta_and_diagnostic",
    family=RecipeFamily.matrix,
    answers_question=(
        "Under leave-one-out cross-validation, which classes does "
        "the random-forest classifier confuse, and what is the "
        "macro-F1 / accuracy?"
    ),
    required_fields=("confusion_matrix", "class_labels"),
    optional_fields=("cv_label", "title"),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("replication_retrospective_matrix",),
)


@register_recipe(
    metadata=_META,
    contract=RandomForestConfusionInput,
    demo_contract=_demo,
)
def render(contract: RandomForestConfusionInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.4, 4.2))
    AESTHETIC.apply_to_ax(ax)

    M = np.asarray(contract.confusion_matrix, int)
    n = M.shape[0]
    classes = contract.class_labels

    row_sums = M.sum(axis=1, keepdims=True)
    row_norm = M / np.maximum(row_sums, 1)

    im = ax.imshow(row_norm, cmap="cividis",
                   vmin=0.0, vmax=1.0,
                   aspect="equal", interpolation="nearest", zorder=2)

    cbar = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("row-normalised fraction", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    # Annotate counts (and row-fraction in parentheses).
    for i in range(n):
        for j in range(n):
            count = int(M[i, j])
            frac = float(row_norm[i, j])
            text_color = "white" if frac > 0.55 else "#222222"
            ax.text(j, i,
                    f"{count}\n({smart_fmt(frac * 100)}%)",
                    ha="center", va="center", fontsize=6.6,
                    color=text_color,
                    fontweight="bold" if i == j else "normal",
                    zorder=4)

    ax.set_xticks(range(n))
    ax.set_xticklabels(classes, fontsize=7.0)
    ax.set_yticks(range(n))
    ax.set_yticklabels(classes, fontsize=7.0)
    ax.set_xlabel("predicted", fontsize=7.0)
    ax.set_ylabel("true", fontsize=7.0)

    # Accuracy + macro-F1.
    total = int(M.sum())
    correct = int(np.trace(M))
    accuracy = correct / max(total, 1)
    f1s = []
    for i in range(n):
        tp = int(M[i, i])
        fp = int(M[:, i].sum() - tp)
        fn = int(M[i, :].sum() - tp)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        if precision + recall > 0:
            f1s.append(2 * precision * recall / (precision + recall))
        else:
            f1s.append(0.0)
    macro_f1 = float(np.mean(f1s)) if f1s else 0.0

    ax.set_title(
        f"{contract.title}  ·  {contract.cv_label}  ·  "
        f"acc = {smart_fmt(accuracy * 100)}%  ·  "
        f"macro-F1 = {smart_fmt(macro_f1)}",
        fontsize=8.2, pad=6,
    )
    return ax
