"""Ensemble RMSF per residue — RMS fluctuation across an MD / NMR
ensemble with secondary-structure tracks.

Distinct from `bfactor_vs_residue` (static B-factor from a single
structure): RMSF comes from an ensemble and reports dynamics.
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


class RMSFInput(RecipeContract):
    residue_index: list[int] = Field(..., min_length=5)
    rmsf: list[float] = Field(..., description="RMSF in Å per residue")
    secondary_structure: list[str] | None = Field(
        None,
        description="per-residue SS code: 'H' / 'E' / '-' (helix / sheet / coil)",
    )
    title: str = "Ensemble RMSF per residue"


def _demo() -> RMSFInput:
    rng = np.random.default_rng(2811)
    n = 220
    idx = list(range(1, n + 1))
    # Low RMSF in core regions, higher in loops.
    rmsf = np.zeros(n)
    rmsf += 0.35
    for start, end in [(30, 60), (110, 140), (170, 200)]:
        rmsf[start:end] = 0.2 + rng.uniform(0.0, 0.1, end - start)
    # Loop / terminal bumps.
    rmsf[:20] = 1.0 + rng.uniform(0, 0.5, 20)
    rmsf[60:80] = 0.8 + rng.uniform(0, 0.3, 20)
    rmsf[140:170] = 0.7 + rng.uniform(0, 0.25, 30)
    rmsf[200:] = 1.2 + rng.uniform(0, 0.6, n - 200)
    rmsf += rng.normal(0, 0.03, n)
    rmsf = np.clip(rmsf, 0.05, None)
    # SS codes.
    ss = ["-"] * n
    for start, end in [(30, 60), (110, 140)]:
        for i in range(start, end):
            ss[i] = "H"
    for start, end in [(170, 200)]:
        for i in range(start, end):
            ss[i] = "E"
    return RMSFInput(
        residue_index=idx,
        rmsf=rmsf.tolist(),
        secondary_structure=ss,
    )


_META = RecipeMetadata(
    name="conformational_ensemble_rmsf",
    modality="cryoem_and_structure",
    family=RecipeFamily.diagnostic_curve,
    answers_question=(
        "From an MD or NMR ensemble, which residues have the highest "
        "RMS fluctuation?"
    ),
    required_fields=("residue_index", "rmsf"),
    optional_fields=("secondary_structure", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("bfactor_vs_residue",),
)


@register_recipe(metadata=_META, contract=RMSFInput, demo_contract=_demo)
def render(contract: RMSFInput, ax=None, **_):
    import matplotlib.patches as mpatches

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.2, 3.4))
    AESTHETIC.apply_to_ax(ax)

    idx = np.asarray(contract.residue_index, float)
    rmsf = np.asarray(contract.rmsf, float)

    # RMSF trace with filled baseline.
    ax.fill_between(idx, 0, rmsf, color="#1565C0", alpha=0.18,
                    linewidth=0, zorder=2)
    ax.plot(idx, rmsf, color="#0D47A1", lw=1.2, zorder=4,
            label="RMSF")
    # Median-RMSF reference line.
    rmsf_med = float(np.median(rmsf))
    ax.axhline(rmsf_med, color="#888888", lw=0.8, ls="--", zorder=3,
               label=f"median = {smart_fmt(rmsf_med)} Å")

    # Secondary-structure track along the top of the axes.
    if contract.secondary_structure is not None:
        ss = contract.secondary_structure
        # Find contiguous runs.
        track_y = rmsf.max() * 1.08
        track_h = rmsf.max() * 0.06
        i = 0
        while i < len(ss):
            j = i
            while j < len(ss) and ss[j] == ss[i]:
                j += 1
            if ss[i] == "H":
                color = "#C62828"
            elif ss[i] == "E":
                color = "#2E7D32"
            else:
                color = "#BDBDBD"
            ax.add_patch(mpatches.Rectangle(
                (idx[i] - 0.5, track_y), idx[j - 1] - idx[i] + 1, track_h,
                facecolor=color, edgecolor="none", alpha=0.8, zorder=3,
            ))
            i = j
        # Track legend — below axes so it can't overlap the top SS
        # strip.
        proxies = [
            mpatches.Patch(facecolor="#C62828", label="α-helix"),
            mpatches.Patch(facecolor="#2E7D32", label="β-strand"),
            mpatches.Patch(facecolor="#BDBDBD", label="loop / coil"),
        ]
        ax.legend(handles=proxies, fontsize=6.8, frameon=False,
                  loc="upper center", bbox_to_anchor=(0.5, -0.14),
                  handlelength=1.0, ncols=3)

    # Mark top-5 most flexible residues.
    top_k = 5
    top_idx = np.argsort(-rmsf)[:top_k]
    ax.scatter(idx[top_idx], rmsf[top_idx], s=34, marker="o",
               color="#C62828", edgecolor="white", linewidth=0.7,
               zorder=6)

    ax.set_xlabel("residue index")
    ax.set_ylabel("RMSF (Å)")
    ax.set_xlim(idx.min(), idx.max())
    ax.set_ylim(0, rmsf.max() * 1.22)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.set_title(
        f"{contract.title}  ·  median RMSF "
        f"{smart_fmt(float(np.median(rmsf)))} Å  ·  max "
        f"{smart_fmt(float(rmsf.max()))} Å at res {int(idx[int(rmsf.argmax())])}",
        fontsize=8.4, pad=4,
    )
    return ax
