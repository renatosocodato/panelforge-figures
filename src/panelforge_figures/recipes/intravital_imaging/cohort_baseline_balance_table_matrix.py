"""Cohort baseline balance table matrix — per-feature standardised
mean differences (SMD) between cohorts; cell colour is signed SMD;
|SMD| > 0.1 (and 0.2) reference circles drawn on the colour bar.

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


class BalanceFeatureRow(RecipeContract):
    feature: str
    cohort_a_mean: float
    cohort_a_sd: float
    cohort_a_n: int
    cohort_b_mean: float
    cohort_b_sd: float
    cohort_b_n: int


class CohortBalanceMatrixInput(RecipeContract):
    rows: list[BalanceFeatureRow] = Field(..., min_length=4)
    cohort_a_label: str = "control"
    cohort_b_label: str = "DISC1"
    smd_warn: float = 0.1
    smd_strong: float = 0.2
    title: str = "Cohort baseline balance"


def _demo() -> CohortBalanceMatrixInput:
    rng = np.random.default_rng(3281)
    feats = [
        "age (weeks)", "weight (g)", "sex (% female)",
        "baseline velocity (um/min)", "baseline length (um)",
        "branch order", "imaging depth (um)", "frame rate (Hz)",
        "field of view (mm)", "session number",
        "n cells per field", "background intensity",
    ]
    rows: list[BalanceFeatureRow] = []
    # 12 features; 3 of them have |SMD| > 0.1.
    for i, f in enumerate(feats):
        a_mu = float(rng.normal(0, 1.0))
        a_sd = float(0.6 + rng.uniform(0, 0.4))
        if i in (3, 5, 9):
            # Imbalanced — flag with SMD ~ 0.3.
            b_mu = a_mu + 0.3 * a_sd
        elif i == 7:
            b_mu = a_mu + 0.15 * a_sd
        else:
            b_mu = a_mu + rng.normal(0, 0.05)
        b_sd = float(0.6 + rng.uniform(0, 0.4))
        rows.append(BalanceFeatureRow(
            feature=f,
            cohort_a_mean=a_mu, cohort_a_sd=a_sd, cohort_a_n=30,
            cohort_b_mean=float(b_mu), cohort_b_sd=b_sd, cohort_b_n=30,
        ))
    return CohortBalanceMatrixInput(rows=rows)


_META = RecipeMetadata(
    name="cohort_baseline_balance_table_matrix",
    modality="intravital_imaging",
    family=RecipeFamily.matrix,
    answers_question=(
        "Are imaging cohorts balanced on baseline characteristics, "
        "and on which features does standardised mean difference "
        "(SMD) cross the 0.1 / 0.2 reviewer-proof thresholds?"
    ),
    required_fields=("rows",),
    optional_fields=(
        "cohort_a_label", "cohort_b_label", "smd_warn", "smd_strong", "title",
    ),
    file_format_hints=("csv", "yaml"),
    alternatives_in_modality=("commitment_vs_chemotaxis_contingency",),
)


@register_recipe(
    metadata=_META,
    contract=CohortBalanceMatrixInput,
    demo_contract=_demo,
)
def render(contract: CohortBalanceMatrixInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.4))
    AESTHETIC.apply_to_ax(ax)

    n = len(contract.rows)
    feats = [r.feature for r in contract.rows]
    a_mu = np.array([r.cohort_a_mean for r in contract.rows])
    a_sd = np.array([r.cohort_a_sd for r in contract.rows])
    b_mu = np.array([r.cohort_b_mean for r in contract.rows])
    b_sd = np.array([r.cohort_b_sd for r in contract.rows])

    pooled_sd = np.sqrt(0.5 * (a_sd ** 2 + b_sd ** 2)) + 1e-9
    smd = (b_mu - a_mu) / pooled_sd

    # Build a 4-column matrix: [cohort_a_mean ± sd, cohort_b_mean ± sd, SMD].
    # Display SMD column as the heat (the only signed column).
    fig = ax.figure
    n_cols = 4
    col_labels = [
        f"{contract.cohort_a_label}\nmean ± sd",
        f"{contract.cohort_b_label}\nmean ± sd",
        "SMD",
        "TOST flag",
    ]

    # Background cells via pcolormesh (smd column heat).
    smd_max = max(0.3, float(np.max(np.abs(smd))) * 1.1)
    smd_grid = np.zeros((n, n_cols))
    smd_grid[:, 2] = smd
    # Mask everything except SMD column.
    mask = np.ones((n, n_cols), dtype=bool)
    mask[:, 2] = False
    smd_show = np.ma.masked_array(smd_grid, mask=mask)

    X = np.arange(n_cols + 1) - 0.5
    Y = np.arange(n + 1) - 0.5
    mesh = ax.pcolormesh(X, Y, smd_show, cmap="RdBu_r",
                         vmin=-smd_max, vmax=smd_max,
                         shading="auto", zorder=2)

    # Annotate cells.
    for i, r in enumerate(contract.rows):
        ax.text(0, i, f"{smart_fmt(r.cohort_a_mean)} ± "
                      f"{smart_fmt(r.cohort_a_sd)}",
                ha="center", va="center", fontsize=6.4,
                color="#222222", zorder=4)
        ax.text(1, i, f"{smart_fmt(r.cohort_b_mean)} ± "
                      f"{smart_fmt(r.cohort_b_sd)}",
                ha="center", va="center", fontsize=6.4,
                color="#222222", zorder=4)
        smd_val = smd[i]
        smd_text_color = "white" if abs(smd_val) > smd_max * 0.55 \
            else "#222222"
        ax.text(2, i, f"{smart_fmt(smd_val)}",
                ha="center", va="center", fontsize=6.6,
                color=smd_text_color, fontweight="bold", zorder=4)
        # TOST flag.
        if abs(smd_val) > contract.smd_strong:
            flag = "imbalanced"
            flag_color = "#C62828"
        elif abs(smd_val) > contract.smd_warn:
            flag = "borderline"
            flag_color = "#FB8C00"
        else:
            flag = "balanced"
            flag_color = "#2E7D32"
        ax.text(3, i, flag, ha="center", va="center", fontsize=6.4,
                color=flag_color, fontweight="bold", zorder=4)

    ax.set_yticks(range(n))
    ax.set_yticklabels(feats, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(col_labels, fontsize=6.6)
    ax.tick_params(axis="x", which="major", pad=4)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Colour bar for the SMD column.
    cbar = fig.colorbar(mesh, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("SMD (b - a) / pooled sd", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)
    # Reference ticks on the colour bar at the 0.1 / 0.2 thresholds.
    for thr in (-contract.smd_strong, -contract.smd_warn,
                contract.smd_warn, contract.smd_strong):
        cbar.ax.axhline(thr, color="#222222", lw=0.6, ls="--",
                        zorder=5)

    n_imbal = int((np.abs(smd) > contract.smd_strong).sum())
    n_warn = int(((np.abs(smd) > contract.smd_warn)
                  & (np.abs(smd) <= contract.smd_strong)).sum())
    ax.set_title(
        f"{contract.title}  ·  {contract.cohort_a_label} vs "
        f"{contract.cohort_b_label}  ·  {n_imbal} imbalanced "
        f"(|SMD| > {contract.smd_strong}), {n_warn} borderline",
        fontsize=8.2, pad=4,
    )
    return ax
