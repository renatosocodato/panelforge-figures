"""Default theme — inherits the base style with no overrides."""

from . import register_theme


def _overrides() -> dict:
    return {}


register_theme("default", _overrides)
