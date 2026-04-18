"""Horizon Europe — dense compact with slightly thicker axes."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 7.8,
        "axes.titlesize": 8.8,
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "legend.fontsize": 7.0,
        "figure.titlesize": 10.5,
        "axes.linewidth": 0.8,
    }


register_theme("horizon", _overrides)
