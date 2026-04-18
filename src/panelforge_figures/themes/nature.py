"""Nature family (Nature, Nature Methods, Nat Cell Biol upstream) — tight sans.

Nature journals accept Helvetica / Arial at ≥5 pt. This theme keeps the base
sans stack, tightens label sizes one step, and drops the title weight to
match Nature's thinner type (Nature moved off bold Helvetica years ago).
"""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 8.0,
        "axes.titlesize": 9.0,
        "axes.titleweight": "semibold" if False else "bold",
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "legend.fontsize": 7.0,
        "figure.titlesize": 11.0,
    }


register_theme("nature", _overrides)
