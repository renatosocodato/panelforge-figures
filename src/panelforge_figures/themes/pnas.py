"""PNAS — conservative serif titles, compact two-column layout."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.5,
        "axes.titleweight": "bold",
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "figure.titlesize": 11.5,
        "legend.fontsize": 7.5,
    }


register_theme("pnas", _overrides)
