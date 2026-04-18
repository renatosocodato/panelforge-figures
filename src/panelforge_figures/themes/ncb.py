"""Nature Cell Biology — Nature family overrides with a touch more contrast."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 8.0,
        "axes.titlesize": 9.0,
        "axes.titleweight": "bold",
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "legend.fontsize": 7.0,
        "figure.titlesize": 11.0,
        "axes.linewidth": 0.8,
    }


register_theme("ncb", _overrides)
