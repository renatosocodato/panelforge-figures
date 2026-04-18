"""Signal Transduction and Targeted Therapy — larger labels, punchy colors."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 9.5,
        "axes.titlesize": 10.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "figure.titlesize": 12.5,
    }


register_theme("sttt", _overrides)
