"""Cell family (Cell, Cell Reports, Dev Cell upstream) — slightly larger labels."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 9.0,
        "axes.titlesize": 10.0,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
        "figure.titlesize": 12.0,
    }


register_theme("cell", _overrides)
