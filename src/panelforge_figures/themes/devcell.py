"""Dev Cell — warmer, still in the Cell family."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 8.8,
        "axes.titlesize": 9.8,
        "xtick.labelsize": 7.8,
        "ytick.labelsize": 7.8,
        "legend.fontsize": 7.8,
        "figure.titlesize": 11.8,
    }


register_theme("devcell", _overrides)
