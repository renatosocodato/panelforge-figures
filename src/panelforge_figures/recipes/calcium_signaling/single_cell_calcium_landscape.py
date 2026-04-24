"""Per-cell (event frequency, event amplitude) scatter with density + hulls.

Two-dimensional per-cell scatter summarising activity: x = event
frequency (Hz), y = event amplitude (ΔF/F), coloured by condition,
with per-condition convex hulls and an overall density contour.
"""

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


class CalciumLandscapeInput(RecipeContract):
    cell_id: list[str] = Field(...)
    event_frequency_hz: list[float] = Field(...)
    event_amplitude: list[float] = Field(...)
    condition: list[str] = Field(...)
    title: str = "Single-cell Ca2+ landscape"


def _demo() -> CalciumLandscapeInput:
    rng = np.random.default_rng(337)
    conds = []
    freqs = []
    amps = []
    ids = []
    profiles = {
        "baseline":  (0.12, 0.03, 0.25, 0.08),
        "KCl":       (0.45, 0.10, 0.55, 0.15),
        "TTX":       (0.04, 0.015, 0.20, 0.06),
    }
    idx = 0
    for cond, (f_mu, f_sd, a_mu, a_sd) in profiles.items():
        n = 60
        f = np.clip(rng.normal(f_mu, f_sd, n), 0.01, None)
        a = np.clip(rng.normal(a_mu, a_sd, n), 0.05, None)
        freqs.extend(f.tolist())
        amps.extend(a.tolist())
        conds.extend([cond] * n)
        for _ in range(n):
            ids.append(f"c{idx:04d}")
            idx += 1
    return CalciumLandscapeInput(
        cell_id=ids,
        event_frequency_hz=freqs,
        event_amplitude=amps,
        condition=conds,
    )


_META = RecipeMetadata(
    name="single_cell_calcium_landscape",
    modality="calcium_signaling",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Per cell, how does event frequency relate to event amplitude?"
    ),
    required_fields=("cell_id", "event_frequency_hz", "event_amplitude", "condition"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=(
        "event_frequency_by_condition",
        "calcium_event_amplitude_distribution",
    ),
)


@register_recipe(
    metadata=_META,
    contract=CalciumLandscapeInput,
    demo_contract=_demo,
)
def render(contract: CalciumLandscapeInput, ax=None, **_):
    from scipy.spatial import ConvexHull
    from scipy.stats import gaussian_kde

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.8))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    f = np.asarray(contract.event_frequency_hz, float)
    a = np.asarray(contract.event_amplitude, float)
    cond = np.asarray(contract.condition)
    uniques = list(dict.fromkeys(cond.tolist()))

    # Whole-population density contour (Gaussian KDE on log-freq vs amp).
    mask = np.isfinite(f) & np.isfinite(a) & (f > 0) & (a > 0)
    if mask.sum() >= 10:
        lf = np.log10(f[mask])
        la = a[mask]
        try:
            kde = gaussian_kde(np.vstack([lf, la]))
            xs_log = np.linspace(lf.min(), lf.max(), 80)
            ys = np.linspace(la.min(), la.max(), 80)
            XX, YY = np.meshgrid(xs_log, ys)
            Z = kde(np.vstack([XX.ravel(), YY.ravel()])).reshape(XX.shape)
            ax.contour(10 ** XX, YY, Z, levels=5, colors="#BBBBBB",
                       linewidths=0.5, alpha=0.55, zorder=2)
        except (np.linalg.LinAlgError, ValueError):
            pass

    # Per-condition scatter + convex hull.
    for i, name in enumerate(uniques):
        m = cond == name
        color = (palette.pick(name) if name in palette.semantic
                 else palette[i % len(palette.colors)])
        ax.scatter(f[m], a[m], s=18, color=color, alpha=0.75,
                   edgecolor="white", linewidth=0.3, zorder=3,
                   label=f"{name} (n={int(m.sum())})")
        pts = np.column_stack([f[m], a[m]])
        if pts.shape[0] >= 3:
            try:
                hull = ConvexHull(pts)
                verts = pts[hull.vertices]
                verts = np.vstack([verts, verts[0]])
                ax.plot(verts[:, 0], verts[:, 1], color=color,
                        lw=0.9, alpha=0.6, zorder=4)
            except Exception:
                pass

    ax.set_xscale("log")
    ax.set_xlabel("event frequency (Hz)")
    ax.set_ylabel(r"event amplitude ($\Delta F/F$)")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left",
              handlelength=1.4)
    ax.grid(which="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Medoid annotations per condition.
    for i, name in enumerate(uniques):
        m = cond == name
        if m.sum() == 0:
            continue
        f_med = float(np.median(f[m]))
        a_med = float(np.median(a[m]))
        ax.text(0.98, 0.98 - 0.06 * i,
                f"{name}: f={smart_fmt(f_med)}, a={smart_fmt(a_med)}",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=6.2, color=(palette.pick(name)
                                     if name in palette.semantic
                                     else palette[i % len(palette.colors)]),
                zorder=6)
    return ax
