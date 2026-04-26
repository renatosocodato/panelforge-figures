"""Latency-decomposition forest — the headline panel of any
chemotaxis figure.

Rows = latency type × condition. Marker = median latency, CI bars =
bootstrap 95%. Reference line at the median(tau_reorient) of the
control condition (the natural pacing benchmark). Bars colour-coded
by latency type so the bottleneck (which latency dominates) is
immediately readable.

Coef-forest family: >=3 markers + >=1 reference line. Satisfied by
3 latency types × 2 conditions = 6 markers + the median(tau_reorient,
control) reference.
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
from ._shared import LatencyDistribution

# Three latency types -> contemporary palette colours.
_LATENCY_PALETTE = {
    "tau_reorient": "#26A69A",   # teal
    "tau_commit":   "#EF5350",   # coral
    "tau_drift":    "#FFA726",   # amber
}


class LatencyDecompositionForestInput(RecipeContract):
    latencies: list[LatencyDistribution] = Field(..., min_length=4)
    summary: str = Field(
        "median",
        description="'median' | 'mean'",
    )
    n_bootstrap: int = 500
    title: str = "Latency decomposition"


def _demo() -> LatencyDecompositionForestInput:
    rng = np.random.default_rng(2821)
    out: list[LatencyDistribution] = []
    for cond, scale_factor in (("control", 1.0), ("DISC1", 1.7)):
        out.append(LatencyDistribution(
            label="tau_reorient", condition=cond,
            values_s=rng.gamma(shape=2.5,
                               scale=4.0 * scale_factor, size=70).tolist(),
            n_subjects=70,
        ))
        out.append(LatencyDistribution(
            label="tau_commit", condition=cond,
            values_s=rng.lognormal(mean=2.6 + 0.4 * (scale_factor - 1),
                                   sigma=0.45, size=70).tolist(),
            n_subjects=70,
        ))
        out.append(LatencyDistribution(
            label="tau_drift", condition=cond,
            values_s=rng.gamma(shape=3.0,
                               scale=6.0 * scale_factor, size=70).tolist(),
            n_subjects=70,
        ))
    return LatencyDecompositionForestInput(latencies=out)


_META = RecipeMetadata(
    name="latency_decomposition_forest",
    modality="intravital_imaging",
    family=RecipeFamily.coef_forest,
    answers_question=(
        "Across the three canonical latencies (tau_reorient, "
        "tau_commit, tau_drift) and conditions, which latency is "
        "the chemotaxis bottleneck?"
    ),
    required_fields=("latencies",),
    optional_fields=("summary", "n_bootstrap", "title"),
    file_format_hints=("yaml", "json"),
    alternatives_in_modality=("launch_to_commitment_latency",),
)


@register_recipe(
    metadata=_META,
    contract=LatencyDecompositionForestInput,
    demo_contract=_demo,
)
def render(contract: LatencyDecompositionForestInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.6, 3.8))
    AESTHETIC.apply_to_ax(ax)

    rng = np.random.default_rng(13)

    # Group by condition, ordering: control first, then others.
    conditions = []
    for lat in contract.latencies:
        if lat.condition not in conditions:
            conditions.append(lat.condition)
    if "control" in conditions:
        conditions = ["control"] + [c for c in conditions if c != "control"]

    rows: list[tuple[str, str, float, float, float]] = []  # cond, label, est, lo, hi
    for cond in conditions:
        for label in ("tau_reorient", "tau_commit", "tau_drift"):
            match = next(
                (lat for lat in contract.latencies
                 if lat.condition == cond and lat.label == label),
                None,
            )
            if match is None:
                continue
            vals = np.asarray(match.values_s, float)
            if vals.size == 0:
                continue
            estimator = (np.median if contract.summary == "median"
                         else np.mean)
            est = float(estimator(vals))
            # Bootstrap CI.
            boots = []
            for _ in range(contract.n_bootstrap):
                idx = rng.integers(0, vals.size, size=vals.size)
                boots.append(float(estimator(vals[idx])))
            lo = float(np.quantile(boots, 0.025))
            hi = float(np.quantile(boots, 0.975))
            rows.append((cond, label, est, lo, hi))

    n_rows = len(rows)
    y_positions = np.arange(n_rows)
    separators: list[float] = []
    last_cond = None
    for yi, (cond, _, _, _, _) in zip(y_positions, rows):
        if last_cond is not None and cond != last_cond:
            separators.append(yi - 0.5)
        last_cond = cond

    # Reference: median(tau_reorient) of control.
    ref = next(
        (e for cond, label, e, _, _ in rows
         if cond == "control" and label == "tau_reorient"),
        None,
    )
    if ref is not None:
        ax.axvline(ref, color="#888888", lw=0.7, ls="--", zorder=2,
                   label=f"control tau_reorient = {smart_fmt(ref)} s")

    # Per-row CI segment + marker.
    for yi, (_cond, label, est, lo, hi) in zip(y_positions, rows):
        colour = _LATENCY_PALETTE.get(label, "#37474F")
        ax.plot([lo, hi], [yi, yi],
                color=colour, lw=1.1, alpha=0.85, zorder=3)
    ax.scatter(
        [r[2] for r in rows], y_positions,
        s=44,
        c=[_LATENCY_PALETTE.get(r[1], "#37474F") for r in rows],
        edgecolor="white", linewidth=0.6, zorder=5,
    )

    # Group separator lines.
    for sep in separators:
        ax.axhline(sep, color="#DDDDDD", lw=0.5, zorder=1)

    # Y-tick labels: condition (left) + latency (inline).
    tick_labels = [f"{cond}  ·  {label}"
                   for cond, label, _, _, _ in rows]
    ax.set_yticks(y_positions)
    ax.set_yticklabels(tick_labels, fontsize=6.6)
    ax.invert_yaxis()
    ax.set_xlabel(f"{contract.summary} latency (s)")
    ax.grid(axis="x", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Legend (latency types + reference).
    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], marker="o", color="none",
               markerfacecolor=_LATENCY_PALETTE[k],
               markeredgecolor="white", markersize=6,
               label=k)
        for k in _LATENCY_PALETTE
    ]
    handles.append(Line2D([0], [0], color="#888888", ls="--", lw=0.7,
                          label="ctrl tau_reorient"))
    ax.legend(handles=handles, fontsize=6.4, frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.16),
              ncols=4, handlelength=1.2)

    # Bottleneck verdict in title: which latency has the largest
    # condition-vs-control ratio?
    ratio_bits = []
    if "control" in conditions and len(conditions) >= 2:
        for label in ("tau_reorient", "tau_commit", "tau_drift"):
            ctrl_est = next(
                (e for cond, lab, e, _, _ in rows
                 if cond == "control" and lab == label),
                None,
            )
            for cond in conditions:
                if cond == "control":
                    continue
                cond_est = next(
                    (e for c2, lab, e, _, _ in rows
                     if c2 == cond and lab == label),
                    None,
                )
                if ctrl_est and cond_est and ctrl_est > 0:
                    ratio_bits.append(
                        (label, cond, cond_est / ctrl_est)
                    )
    bottleneck = max(ratio_bits, key=lambda b: b[2]) if ratio_bits else None
    bot_text = ""
    if bottleneck is not None:
        bot_text = (f"bottleneck: {bottleneck[0]} "
                    f"({bottleneck[1]} / control = "
                    f"{smart_fmt(bottleneck[2])}x)")
    ax.set_title(
        f"{contract.title}  ·  {contract.summary} of "
        f"{len(rows)} latency-condition cells  ·  {bot_text}",
        fontsize=7.6, pad=4,
    )
    return ax
