"""Trends journals — review-friendly, extra breathing room, thicker lines."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 9.0,
        "axes.titlesize": 10.0,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 8.0,
        "lines.linewidth": 1.4,
        "figure.titlesize": 12.0,
    }


register_theme("trends", _overrides)
