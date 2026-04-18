"""Biophysical Journal — compact, restrained, neutral palette-friendly."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 8.0,
        "axes.titlesize": 9.0,
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "legend.fontsize": 7.0,
        "figure.titlesize": 11.0,
        "lines.linewidth": 1.2,
    }


register_theme("bpj", _overrides)
