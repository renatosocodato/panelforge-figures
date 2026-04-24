"""Forward-simulation validation contract — empirical vs simulated,
n metrics x m groups with a contract verdict per (metric, group).

Generic parameter-sufficiency pattern: the contract is satisfied iff
every empirical group-median lies inside the simulated group-specific
CI. Reusable for any future biophysics_scaling manuscript with a
forward-simulation layer.

The render normalizes within each metric so that the simulated CI
spans x = [-1, +1] (zero = sim median). Empirical medians plot in
those normalized units, so rows across metrics are directly
comparable. The contract verdict glyph (+/-) per (metric, group)
sits at the right margin.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
>=3 (metric, group) rows + the normalized-zero null reference +
the +/-1 sim-CI bounds.
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
from ._shared import ValidationMetric


class ValidationContractInput(RecipeContract):
    metrics: list[ValidationMetric] = Field(..., min_length=1)
    criterion: str = Field(
        "median_in_ci",
        description="'median_in_ci' (default) | 'mean_in_ci'",
    )
    show_overall_verdict: bool = True
    n_replicates_per_group: dict[str, int] | None = None
    title: str = "Forward-simulation validation contract"


def _demo() -> ValidationContractInput:
    """Manuscript-anchored demo: 3 metrics x 2 groups, n_reps=256."""
    metrics = [
        ValidationMetric(
            metric_label="in-plane ordering (alpha)",
            sim_median_by_group={"WT": 0.42, "LI": 0.64},
            sim_ci_by_group={"WT": (0.34, 0.50), "LI": (0.56, 0.73)},
            emp_median_by_group={"WT": 0.44, "LI": 0.61},
            emp_ci_by_group={"WT": (0.38, 0.51), "LI": (0.52, 0.70)},
            units="dimensionless",
            higher_is="ordered",
        ),
        ValidationMetric(
            metric_label="z-span analogue (um)",
            sim_median_by_group={"WT": 2.1, "LI": 3.4},
            sim_ci_by_group={"WT": (1.8, 2.4), "LI": (2.9, 3.9)},
            emp_median_by_group={"WT": 2.2, "LI": 3.2},
            emp_ci_by_group={"WT": (1.9, 2.5), "LI": (2.7, 3.7)},
            units="um",
        ),
        ValidationMetric(
            metric_label="tapered-tip fraction",
            sim_median_by_group={"WT": 0.72, "LI": 0.38},
            sim_ci_by_group={"WT": (0.64, 0.79), "LI": (0.29, 0.47)},
            emp_median_by_group={"WT": 0.70, "LI": 0.41},
            emp_ci_by_group={"WT": (0.62, 0.77), "LI": (0.33, 0.49)},
            units="fraction",
        ),
    ]
    return ValidationContractInput(
        metrics=metrics,
        n_replicates_per_group={"WT": 256, "LI": 256},
    )


_META = RecipeMetadata(
    name="forward_simulation_validation_contract",
    modality="biophysics_scaling",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across n metrics x m groups, does each empirical median lie "
        "inside its forward-simulation CI (parameter-sufficiency "
        "contract)?"
    ),
    required_fields=("metrics",),
    optional_fields=(
        "criterion", "show_overall_verdict",
        "n_replicates_per_group", "title",
    ),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("scaling_exponent_ci_forest",),
)


def _normalize(value: float, sim_med: float, sim_lo: float, sim_hi: float) -> float:
    half = max((sim_hi - sim_lo) / 2.0, 1e-9)
    return (value - sim_med) / half


def _verdict(emp_median: float, sim_lo: float, sim_hi: float) -> bool:
    return sim_lo <= emp_median <= sim_hi


@register_recipe(
    metadata=_META,
    contract=ValidationContractInput,
    demo_contract=_demo,
)
def render(contract: ValidationContractInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    # Collect (metric, group) rows in display order — metrics top-to-bottom,
    # groups alphabetical-within-metric.
    rows: list[tuple[ValidationMetric, str]] = []
    metric_separators: list[float] = []
    for m in contract.metrics:
        groups = sorted(m.sim_median_by_group.keys())
        for g in groups:
            rows.append((m, g))
        metric_separators.append(len(rows) - 0.5)

    y = np.arange(len(rows))

    # Draw sim CI as a shaded band per row (normalized: x spans -1..1).
    for yi, (_, _) in zip(y, rows):
        ax.fill_betweenx(
            [yi - 0.35, yi + 0.35], -1.0, 1.0,
            color="#1565C0", alpha=0.12, linewidth=0, zorder=2,
        )

    # Sim-CI edges at x=+/-1 (reference lines).
    ax.axvline(-1.0, color="#1565C0", lw=0.5, ls=":", zorder=3)
    ax.axvline(1.0, color="#1565C0", lw=0.5, ls=":", zorder=3)
    ax.axvline(0.0, color="#888888", lw=0.5, ls="--", zorder=3)

    # Empirical marker + CI whisker per row.
    pass_count = 0
    total_rows = len(rows)
    row_labels: list[str] = []
    verdicts: list[bool] = []
    for yi, (m, g) in zip(y, rows):
        sim_med = m.sim_median_by_group[g]
        sim_lo, sim_hi = m.sim_ci_by_group[g]
        emp_med = m.emp_median_by_group[g]
        emp_lo, emp_hi = m.emp_ci_by_group[g]
        # Normalize empirical values.
        n_med = _normalize(emp_med, sim_med, sim_lo, sim_hi)
        n_lo = _normalize(emp_lo, sim_med, sim_lo, sim_hi)
        n_hi = _normalize(emp_hi, sim_med, sim_lo, sim_hi)
        passes = _verdict(emp_med, sim_lo, sim_hi)
        if passes:
            pass_count += 1
        verdicts.append(passes)
        colour = "#2E7D32" if passes else "#C62828"
        ax.plot([n_lo, n_hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=5)
        ax.scatter([n_med], [yi], s=42, marker="o",
                   color=colour, edgecolor="white", linewidth=0.6,
                   zorder=6)
        row_labels.append(f"{m.metric_label}  ({g})")

    # Row labels on left.
    ax.set_yticks(y)
    ax.set_yticklabels(row_labels, fontsize=6.8)
    ax.invert_yaxis()

    # Metric-group separator lines.
    for sep in metric_separators[:-1]:
        ax.axhline(sep, color="#DDDDDD", lw=0.5, zorder=1)

    # Verdict glyph column — place at x_right. No separate header label
    # (it would escape the axis above the top row and collide with the
    # title); the legend's pass / fail entries already identify the
    # column.
    x_right = 1.9
    for yi, passes in zip(y, verdicts):
        glyph = "+" if passes else "x"
        colour = "#2E7D32" if passes else "#C62828"
        ax.text(x_right, yi, glyph,
                ha="center", va="center", fontsize=8.4,
                color=colour, fontweight="bold", zorder=6,
                clip_on=True)

    ax.set_xlim(-2.2, 2.3)
    ax.set_xlabel("empirical - sim median (in sim-CI half-width units)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Contract verdict in title.
    n_reps = ""
    if contract.n_replicates_per_group:
        reps = " / ".join(
            f"n_{g}={v}" for g, v in contract.n_replicates_per_group.items()
        )
        n_reps = f"  ·  {reps}"
    overall = "SATISFIED" if pass_count == total_rows else "FAILED"
    ax.set_title(
        f"{contract.title}  ·  contract "
        f"{overall if contract.show_overall_verdict else 'verdict'}: "
        f"{pass_count}/{total_rows} passes{n_reps}",
        fontsize=8.2, pad=4,
    )

    # Legend (pass / fail + sim CI band + sim-CI edges).
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#2E7D32", markeredgecolor="white",
               markersize=6, label=f"pass ({pass_count})"),
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor="#C62828", markeredgecolor="white",
               markersize=6, label=f"fail ({total_rows - pass_count})"),
        Patch(facecolor="#1565C0", alpha=0.22, label="sim 95 % CI"),
    ]
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=3, handlelength=1.2)

    _ = smart_fmt  # reserved for future per-row value annotations
    return ax
