"""FCT (Fundação para a Ciência e a Tecnologia) grant — compact, dense."""

from . import register_theme


def _overrides() -> dict:
    return {
        "axes.labelsize": 7.5,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.8,
        "legend.fontsize": 6.8,
        "figure.titlesize": 10.0,
    }


register_theme("fct_grant", _overrides)
