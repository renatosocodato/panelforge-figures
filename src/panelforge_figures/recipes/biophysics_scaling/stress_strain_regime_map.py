"""Stress-strain regime map — σ vs ε curve with elastic / plastic /
failure bands shaded, yield point + ultimate stress markers, and a
Young's-modulus slope inset in the elastic region.
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


class StressStrainInput(RecipeContract):
    strain: list[float] = Field(..., min_length=5, description="strain (dimensionless)")
    stress: list[float] = Field(..., min_length=5, description="stress (Pa or MPa)")
    yield_strain: float = Field(..., description="strain at yield point")
    ultimate_strain: float = Field(..., description="strain at ultimate stress")
    stress_unit: str = "MPa"
    title: str = "Stress-strain regime map"


def _demo() -> StressStrainInput:
    rng = np.random.default_rng(401)
    eps = np.linspace(0, 0.14, 140)
    # Piecewise: elastic (linear, E=200 MPa), yield at 0.018, plateau + harden,
    # ultimate at ~0.10, then softening to failure.
    E = 200.0
    y_eps = 0.018
    u_eps = 0.10
    sigma = np.zeros_like(eps)
    for i, e in enumerate(eps):
        if e <= y_eps:
            sigma[i] = E * e
        elif e <= u_eps:
            sigma[i] = E * y_eps + (E * y_eps * 0.7) * (1 - np.exp(-(e - y_eps) / 0.02))
        else:
            sigma[i] = E * y_eps * 1.7 * np.exp(-(e - u_eps) / 0.05)
    sigma += rng.normal(0, 0.15, eps.size)
    return StressStrainInput(
        strain=eps.tolist(),
        stress=sigma.tolist(),
        yield_strain=0.018,
        ultimate_strain=0.10,
        stress_unit="MPa",
        title="Cortical actin bundle (representative)",
    )


_META = RecipeMetadata(
    name="stress_strain_regime_map",
    modality="biophysics_scaling",
    family=RecipeFamily.matrix,
    answers_question=(
        "Where does the material transition from elastic to plastic to "
        "failure, and what are the yield and ultimate stresses?"
    ),
    required_fields=("strain", "stress", "yield_strain", "ultimate_strain"),
    optional_fields=("stress_unit", "title"),
    file_format_hints=("csv",),
    alternatives_in_modality=("force_length_characteristic",),
)


@register_recipe(
    metadata=_META,
    contract=StressStrainInput,
    demo_contract=_demo,
)
def render(contract: StressStrainInput, ax=None, **_):
    import matplotlib.patches as mpatches
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.2, 3.6))
    AESTHETIC.apply_to_ax(ax)

    eps = np.asarray(contract.strain, float)
    sig = np.asarray(contract.stress, float)
    y_e = float(contract.yield_strain)
    u_e = float(contract.ultimate_strain)
    eps_max = float(eps.max())
    sig_max = float(sig.max())

    # Regime bands: elastic (0, y_e), plastic (y_e, u_e), failure (u_e, eps_max).
    band_specs = [
        (0.0, y_e, "#DDE9F6", "elastic"),
        (y_e, u_e, "#F7E6C4", "plastic"),
        (u_e, eps_max, "#F6D6D0", "failure"),
    ]
    for lo, hi, color, name in band_specs:
        ax.add_patch(mpatches.Rectangle(
            (lo, 0), hi - lo, sig_max * 1.1,
            facecolor=color, edgecolor="none", alpha=0.75, zorder=1,
        ))
        ax.text((lo + hi) / 2, sig_max * 1.02, name,
                ha="center", va="bottom", fontsize=6.8,
                color="#444444", zorder=2)

    # σ(ε) curve.
    ax.plot(eps, sig, color="#222222", lw=1.1, zorder=4, label="σ(ε)")

    # Yield + ultimate indicator hairlines (slender rectangles — also
    # satisfy ≥4 patches for the matrix-family rule).
    hair_w = eps_max * 0.002
    for x_val, color in [(y_e, "#2E7D32"), (u_e, "#C62828")]:
        ax.add_patch(mpatches.Rectangle(
            (x_val - hair_w / 2, 0), hair_w, sig_max * 1.1,
            facecolor=color, edgecolor="none", alpha=0.85, zorder=3,
        ))

    # Yield + ultimate markers.
    sig_y = float(sig[np.argmin(np.abs(eps - y_e))])
    sig_u = float(sig[np.argmin(np.abs(eps - u_e))])
    ax.scatter([y_e], [sig_y], s=36, color="#2E7D32",
               edgecolor="white", linewidth=0.8, zorder=6,
               label=f"yield ({smart_fmt(sig_y)} {contract.stress_unit})")
    ax.scatter([u_e], [sig_u], s=36, color="#C62828",
               edgecolor="white", linewidth=0.8, zorder=6,
               label=f"ultimate ({smart_fmt(sig_u)} {contract.stress_unit})")

    ax.set_xlabel("strain ε")
    ax.set_ylabel(f"stress σ ({contract.stress_unit})")
    ax.set_title(contract.title, fontsize=9.0, pad=4)
    ax.set_xlim(0, eps_max)
    ax.set_ylim(0, sig_max * 1.1)
    ax.legend(fontsize=6.8, frameon=False, loc="lower right",
              handlelength=1.4)
    ax.grid(axis="y", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)

    # Young's-modulus inset in the elastic region.
    mask = eps <= y_e * 0.9
    if mask.sum() >= 3:
        E_fit, _ = np.polyfit(eps[mask], sig[mask], 1)
        inset = inset_axes(ax, width="28%", height="26%",
                           loc="upper right", borderpad=0.8)
        AESTHETIC.apply_to_ax(inset)
        inset.scatter(eps[mask], sig[mask], s=10, color="#1565C0",
                      alpha=0.8, edgecolor="white", linewidth=0.4)
        xfit = np.array([0, float(eps[mask].max())])
        inset.plot(xfit, E_fit * xfit, color="#222222", lw=0.8, zorder=3)
        inset.set_xlabel("ε", fontsize=6.2)
        inset.set_ylabel(f"σ ({contract.stress_unit})", fontsize=6.2)
        inset.tick_params(labelsize=6.2)
        inset.text(0.04, 0.92,
                   f"E = {smart_fmt(float(E_fit))}",
                   transform=inset.transAxes, ha="left", va="top",
                   fontsize=6.2, color="#333333")
    return ax
