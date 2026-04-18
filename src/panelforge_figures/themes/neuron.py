"""Neuron — neuroscience staple; slightly heavier axes."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.linewidth": 0.9,
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.5,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
    }


register_theme("neuron", _overrides)
