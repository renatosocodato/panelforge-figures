"""Tristable phase portrait — HOME, GATE, TRAP wells with coupled streamplot."""

from __future__ import annotations

import numpy as np

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    fixed_point_marker,
    get_palette,
    register_recipe,
)
from ._aesthetic import AESTHETIC


class TristablePortraitInput(RecipeContract):
    # Wells expressed as centers of the three attractors along x.
    home: float = -1.0
    gate: float = 0.0
    trap: float = 1.0
    coupling_lambda: float = 0.35
    condition: str = "basal"
    title: str = "RhoA tristable landscape"


def _demo() -> TristablePortraitInput:
    return TristablePortraitInput()


def _U(x: np.ndarray, home: float, gate: float, trap: float) -> np.ndarray:
    """Three-well potential: product of quadratics around the wells."""
    a, b, c = home, gate, trap
    return 0.18 * (x - a) ** 2 * (x - b) ** 2 * (x - c) ** 2 - 0.25 * x


_META = RecipeMetadata(
    name="phase_portrait_tristable",
    modality="rhogtpase_dynamics",
    family=RecipeFamily.phase_portrait,
    answers_question="What does the RhoA tristable landscape look like — where are HOME / GATE / TRAP and the saddles between them?",
    required_fields=("home", "gate", "trap"),
    optional_fields=("coupling_lambda", "condition", "title"),
    file_format_hints=("pickle", "npz"),
    alternatives_in_modality=("phase_portrait_bistable", "potential_landscape_1d"),
)


@register_recipe(metadata=_META, contract=TristablePortraitInput, demo_contract=_demo)
def render(contract: TristablePortraitInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(5.0, 3.6))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    # 2-D phase portrait: x = RhoA activity, y = slow driver (e.g. RhoGDI release).
    xg = np.linspace(-1.8, 1.8, 30)
    yg = np.linspace(-1.2, 1.2, 24)
    X, Y = np.meshgrid(xg, yg)
    lam = contract.coupling_lambda
    # dx/dt = -dU/dx + lam * (y - x), dy/dt = -0.4 * (y - x^2 * 0.5)
    dUdx = np.gradient(
        _U(xg, contract.home, contract.gate, contract.trap),
        xg,
    )[None, :] * np.ones_like(X)
    Vx = -dUdx + lam * (Y - X)
    Vy = -0.4 * (Y - 0.5 * X ** 2)

    # Backdrop: potential density (over x only, broadcast across y).
    Uflat = _U(xg, contract.home, contract.gate, contract.trap)
    U2D = np.tile(Uflat, (len(yg), 1))
    ax.pcolormesh(X, Y, U2D, cmap=AESTHETIC.continuous_cmap,
                  shading="auto", alpha=0.55, zorder=1)
    # Streamplot.
    ax.streamplot(X, Y, Vx, Vy, color="#EEEEEE", density=0.9,
                  linewidth=0.6, arrowsize=0.6, zorder=2)

    # Fixed points (wells as stable; saddles between them).
    home_c = palette.pick("HOME")
    gate_c = palette.pick("GATE")
    trap_c = palette.pick("TRAP")
    fixed_point_marker(ax, contract.home, 0.5 * contract.home ** 2, "stable",
                       label="HOME")
    fixed_point_marker(ax, contract.gate, 0.5 * contract.gate ** 2, "stable",
                       label="GATE")
    fixed_point_marker(ax, contract.trap, 0.5 * contract.trap ** 2, "stable",
                       label="TRAP")
    # Saddles between wells.
    s1 = 0.5 * (contract.home + contract.gate)
    s2 = 0.5 * (contract.gate + contract.trap)
    fixed_point_marker(ax, s1, 0.5 * s1 ** 2, "saddle")
    fixed_point_marker(ax, s2, 0.5 * s2 ** 2, "saddle")

    # Well-color highlights: thin vertical bands.
    for xc, col in ((contract.home, home_c), (contract.gate, gate_c),
                    (contract.trap, trap_c)):
        ax.axvline(xc, color=col, lw=0.6, ls=":", alpha=0.7, zorder=3)

    ax.set_xlabel("RhoA activity")
    ax.set_ylabel("slow driver")
    ax.set_title(f"{contract.title} · {contract.condition}",
                 fontsize=9.0, pad=4)
    ax.set_xlim(xg.min(), xg.max())
    ax.set_ylim(yg.min(), yg.max())

    # Condition tag.
    ax.text(0.99, 0.02,
            f"λ = {contract.coupling_lambda:.2f}",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.22", fc="white",
                      ec="#BBBBBB", lw=0.5, alpha=0.92),
            zorder=6)
    return ax
