"""Bootstrap stability of validation-contract empirical medians.

For each (metric × group), bootstrap the per-cell cohort with replacement,
recompute the empirical median per bootstrap iteration. Render the bootstrap
distribution of medians as a horizontal violin/strip with optional simulated-
CI band overlay. Annotates pass-rate (% of bootstraps with median in CI).

This is a single-cohort sensitivity check that does NOT need multi-seed
simulation re-runs — it stresses the empirical side of the validation contract
by resampling the observed cohort.
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


class BootstrapValidationStabilityInput(RecipeContract):
    bootstrap_medians: dict[str, dict[str, list[float]]] = Field(
        description="metric_name → {group: list of N bootstrap-resampled medians}"
    )
    simulated_ci_by_metric_by_group: dict[str, dict[str, tuple[float, float]]] | None = Field(
        default=None,
        description="Optional metric → {group: (CI_lo, CI_hi)} from sim — when present, pass-rate annotated"
    )
    metric_order: list[str] | None = None
    title: str = "Bootstrap stability of validation-contract medians"


def _demo() -> BootstrapValidationStabilityInput:
    import random
    rng = random.Random(42)
    metrics = ["coherency", "z-span", "tapered-tip-fraction"]
    medians_by_metric = {}
    cis_by_metric = {}
    for m in metrics:
        wt_med = rng.uniform(0.3, 0.5)
        li_med = wt_med + rng.uniform(-0.1, 0.1)
        medians_by_metric[m] = {
            "WT": [rng.gauss(wt_med, 0.04) for _ in range(500)],
            "LI": [rng.gauss(li_med, 0.05) for _ in range(500)],
        }
        cis_by_metric[m] = {
            "WT": (wt_med - 0.12, wt_med + 0.12),
            "LI": (li_med - 0.13, li_med + 0.13),
        }
    return BootstrapValidationStabilityInput(
        bootstrap_medians=medians_by_metric,
        simulated_ci_by_metric_by_group=cis_by_metric,
        title="Bootstrap stability of 3-metric × 2-group validation contract (500 resamples)",
    )


_META = RecipeMetadata(
    name="bootstrap_validation_stability",
    modality="sensitivity_analysis",
    family=RecipeFamily.split_violin,
    answers_question="How stable are the empirical medians underlying a validation contract under cohort resampling?",
    required_fields=("bootstrap_medians",),
    optional_fields=("simulated_ci_by_metric_by_group", "metric_order", "title"),
    file_format_hints=("csv", "json"),
    alternatives_in_modality=("sobol_bootstrap_convergence", "sensitivity_leave_one_out"),
)


@register_recipe(metadata=_META, contract=BootstrapValidationStabilityInput, demo_contract=_demo)
def render(contract: BootstrapValidationStabilityInput, ax=None, **_):
    import matplotlib.pyplot as plt
    import numpy as np

    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5.5))
    AESTHETIC.apply_to_ax(ax)

    metrics = contract.metric_order or list(contract.bootstrap_medians.keys())
    groups = sorted({g for d in contract.bootstrap_medians.values() for g in d})
    group_colors = {g: c for g, c in zip(groups, ["#1f6f8b", "#c0392b", "#5b8aa4", "#e58e7d"])}

    y_positions = []
    y_labels = []
    cis = contract.simulated_ci_by_metric_by_group or {}
    pass_rates = []

    for mi, metric in enumerate(metrics):
        for gi, group in enumerate(groups):
            vals = np.asarray(contract.bootstrap_medians[metric].get(group, []), dtype=float)
            vals = vals[np.isfinite(vals)]
            if len(vals) == 0:
                continue
            y = mi * (len(groups) + 0.6) + gi  # vertical position
            y_positions.append(y)
            y_labels.append(f"{metric} · {group}")

            # Horizontal violin (KDE via histogram approximation)
            color = group_colors.get(group, "#999")
            parts = ax.violinplot([vals], positions=[y], orientation="horizontal", widths=0.8,
                                   showmeans=False, showmedians=True, showextrema=False)
            for body in parts["bodies"]:
                body.set_facecolor(color)
                body.set_edgecolor(color)
                body.set_alpha(0.45)
            if "cmedians" in parts:
                parts["cmedians"].set_color("#222")
                parts["cmedians"].set_linewidth(1.5)
            # Median marker for the split_violin family rule
            ax.scatter([float(np.median(vals))], [y], s=24, color="#222",
                       edgecolor="white", linewidth=0.5, zorder=4)

            # Optional simulated CI band
            ci = cis.get(metric, {}).get(group)
            if ci is not None:
                ci_lo, ci_hi = ci
                ax.axvspan(ci_lo, ci_hi, ymin=(y - 0.4) / (len(metrics) * (len(groups) + 0.6)),
                           ymax=(y + 0.4) / (len(metrics) * (len(groups) + 0.6)),
                           color=color, alpha=0.08, zorder=0)
                ax.plot([ci_lo, ci_hi], [y, y], color=color, lw=2.2, alpha=0.55, zorder=2)
                # Pass-rate
                in_ci = ((vals >= ci_lo) & (vals <= ci_hi)).sum()
                pass_rate = 100.0 * in_ci / len(vals)
                pass_rates.append(pass_rate)
                ax.text(ci_hi + 0.005, y, f"{pass_rate:.1f}% in CI",
                        ha="left", va="center", fontsize=8.4, color="#333")

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels, fontsize=9.0)
    ax.set_xlabel("empirical median (bootstrap distribution)")
    title = contract.title
    if pass_rates:
        title = f"{title}  · mean pass-rate = {np.mean(pass_rates):.1f}%"
    ax.set_title(title, fontsize=9.6, color="#2c3e50", pad=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#eee", lw=0.5)
    ax.set_axisbelow(True)
    return ax
