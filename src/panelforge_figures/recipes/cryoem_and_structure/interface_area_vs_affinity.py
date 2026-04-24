"""Interface buried-surface-area vs binding affinity — BSA × Kd log-log
scatter with trend line and high-affinity quadrant shading.
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


class InterfaceAffinityInput(RecipeContract):
    complex_names: list[str] = Field(..., min_length=5)
    bsa: list[float] = Field(..., description="buried surface area (Å²)")
    kd: list[float] = Field(...,
                            description="dissociation constant Kd (M)")
    complex_class: list[str] | None = Field(
        None, description="optional class per complex (e.g. 'PPI', 'enzyme')"
    )
    title: str = "BSA vs binding affinity"


def _demo() -> InterfaceAffinityInput:
    rng = np.random.default_rng(3231)
    n = 36
    names = [f"C{i + 1:02d}" for i in range(n)]
    # BSA 400 - 4500 Å².
    bsa = 10 ** rng.uniform(2.8, 3.7, n)
    # Kd log-log correlates negatively with BSA (larger interface =
    # tighter binding).
    log_kd = -6 + (-1.6) * (np.log10(bsa) - 3.2) + rng.normal(0, 0.5, n)
    kd = 10 ** log_kd
    classes = rng.choice(["PPI", "enzyme-substrate", "receptor-ligand"],
                         n, p=[0.5, 0.25, 0.25]).tolist()
    return InterfaceAffinityInput(
        complex_names=names,
        bsa=bsa.tolist(),
        kd=kd.tolist(),
        complex_class=classes,
    )


_META = RecipeMetadata(
    name="interface_area_vs_affinity",
    modality="cryoem_and_structure",
    family=RecipeFamily.scatter_collapse,
    answers_question=(
        "Across complexes, does buried surface area (BSA) correlate "
        "with binding affinity (Kd)?"
    ),
    required_fields=("complex_names", "bsa", "kd"),
    optional_fields=("complex_class", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("docking_pose_score_vs_rmsd",),
)


@register_recipe(
    metadata=_META,
    contract=InterfaceAffinityInput,
    demo_contract=_demo,
)
def render(contract: InterfaceAffinityInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.8))
    AESTHETIC.apply_to_ax(ax)

    bsa = np.asarray(contract.bsa, float)
    kd = np.asarray(contract.kd, float)
    classes = (contract.complex_class
               if contract.complex_class is not None
               else ["complex"] * len(bsa))

    # Use tight y-limits around the actual Kd range so the plot isn't
    # dominated by empty low-Kd decades. Keep a 0.5-decade margin.
    kd_lo = 10 ** (np.log10(kd.min()) - 0.5)
    kd_hi = 10 ** (np.log10(kd.max()) + 0.5)
    ax.set_ylim(kd_lo, kd_hi)
    # High-affinity shading: tightest-observed decade + BSA > 1500.
    ax.axhspan(kd_lo, kd.min() * 3, color="#2E7D32", alpha=0.08,
               linewidth=0, zorder=1)
    ax.axvspan(1500, bsa.max() * 1.2, color="#2E7D32", alpha=0.05,
               linewidth=0, zorder=1)

    unique = list(dict.fromkeys(classes))
    class_colors = ["#1565C0", "#E65100", "#6A1B9A", "#C2185B"]
    cmap = {c: class_colors[i % len(class_colors)]
            for i, c in enumerate(unique)}

    for c in unique:
        mask = np.array([cl == c for cl in classes])
        ax.scatter(bsa[mask], kd[mask], s=34,
                   color=cmap[c], edgecolor="white", linewidth=0.5,
                   alpha=0.85, zorder=5,
                   label=f"{c} (n = {int(mask.sum())})")

    # Fit log-log trend.
    log_bsa = np.log10(bsa)
    log_kd = np.log10(kd)
    slope, intercept = np.polyfit(log_bsa, log_kd, 1)
    b_fit = np.logspace(np.log10(bsa.min()), np.log10(bsa.max()), 80)
    k_fit = 10 ** (slope * np.log10(b_fit) + intercept)
    ax.plot(b_fit, k_fit, color="#222222", lw=1.1, ls="--", zorder=4,
            label=f"trend (slope {smart_fmt(float(slope))})")

    # Pearson r on log-transformed.
    r = float(np.corrcoef(log_bsa, log_kd)[0, 1])

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("buried surface area BSA (Å²)")
    ax.set_ylabel(r"K$_d$ (M, lower = tighter)")
    ax.legend(fontsize=6.6, frameon=False, loc="upper right",
              handlelength=1.2)
    ax.grid(axis="both", which="both", color="#EEEEEE", lw=0.4,
            zorder=0)
    ax.set_axisbelow(True)

    ax.set_title(
        f"{contract.title}  ·  r (log BSA, log Kd) = {smart_fmt(r)}",
        fontsize=8.6, pad=4,
    )
    return ax
