"""Ripley's L(r) — clustering diagnostic with complete-spatial-randomness envelope."""

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


class RipleyLInput(RecipeContract):
    r_um: list[float] = Field(...)
    l_observed: list[float] = Field(..., description="observed L(r) - r")
    csr_envelope_lo: list[float] = Field(...)
    csr_envelope_hi: list[float] = Field(...)
    n_points: int
    title: str = "Ripley's $L(r) - r$"


def _demo() -> RipleyLInput:
    rng = np.random.default_rng(401)
    r = np.linspace(0, 40, 60)
    # Clustered pattern: positive L(r)-r up to ~20 μm.
    obs = 4.0 * np.exp(-((r - 12) ** 2) / 120.0) + rng.normal(0, 0.08, r.size)
    env = 0.6 + 0.01 * r
    return RipleyLInput(
        r_um=r.tolist(),
        l_observed=obs.tolist(),
        csr_envelope_lo=(-env).tolist(),
        csr_envelope_hi=env.tolist(),
        n_points=240,
    )


_META = RecipeMetadata(
    name="ripley_l_function",
    modality="spatial_statistics",
    family=RecipeFamily.diagnostic_curve,
    answers_question="At what spatial scales does a point pattern cluster or inhibit, relative to complete spatial randomness?",
    required_fields=("r_um", "l_observed", "csr_envelope_lo", "csr_envelope_hi", "n_points"),
    optional_fields=("title",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("pair_correlation_function",),
)


@register_recipe(metadata=_META, contract=RipleyLInput, demo_contract=_demo)
def render(contract: RipleyLInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.8, 3.2))
    AESTHETIC.apply_to_ax(ax)
    palette = get_palette(AESTHETIC.primary_palette)

    r = np.array(contract.r_um, dtype=float)
    obs = np.array(contract.l_observed, dtype=float)
    lo = np.array(contract.csr_envelope_lo, dtype=float)
    hi = np.array(contract.csr_envelope_hi, dtype=float)

    ax.fill_between(r, lo, hi, color="#BBBBBB", alpha=0.35,
                    linewidth=0, zorder=1, label="CSR envelope")
    ax.axhline(0, color="#888888", lw=0.6, ls="--", zorder=1)
    ax.plot(r, obs, color=palette[1], lw=1.3, zorder=3, label="observed")

    # Peak of clustering.
    peak_idx = int(np.argmax(obs))
    ax.scatter([r[peak_idx]], [obs[peak_idx]], s=34, color=palette[5],
               edgecolor="white", linewidth=0.9, zorder=4)
    ax.annotate(
        f"peak at r={smart_fmt(float(r[peak_idx]))} $\\mu$m",
        xy=(r[peak_idx], obs[peak_idx]),
        xytext=(8, 6), textcoords="offset points",
        fontsize=6.4, color="#333333",
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.9),
    )

    ax.set_xlabel(r"radius $r$ ($\mu$m)")
    ax.set_ylabel(r"$L(r) - r$")
    ax.set_title(
        f"{contract.title}  ·  N = {contract.n_points} points",
        fontsize=9.0, pad=4,
    )
    ax.legend(fontsize=6.6, frameon=False, loc="lower right",
              handlelength=1.6)
    ax.grid(axis="both", color="#EEEEEE", lw=0.4, zorder=0)
    ax.set_axisbelow(True)
    return ax
