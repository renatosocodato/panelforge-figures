"""Named palettes: ordered lists + semantic lookups. Registry is extensible."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Palette:
    """A named palette: ordered colors + optional semantic mapping."""

    name: str
    colors: tuple[str, ...]
    semantic: dict[str, str] = field(default_factory=dict)
    description: str = ""

    def __iter__(self):
        return iter(self.colors)

    def __getitem__(self, i: int) -> str:
        return self.colors[i % len(self.colors)]

    def pick(self, key: str) -> str:
        """Semantic lookup; raises KeyError if `key` is not registered."""
        return self.semantic[key]

    def take(self, n: int) -> tuple[str, ...]:
        """Cycle through colors to take `n` values."""
        if n <= 0:
            return ()
        return tuple(self[i] for i in range(n))


_REGISTRY: dict[str, Palette] = {}


def register_palette(p: Palette, overwrite: bool = False) -> None:
    if p.name in _REGISTRY and not overwrite:
        raise ValueError(f"palette {p.name!r} already registered")
    _REGISTRY[p.name] = p
    log.debug("registered palette %s (%d colors)", p.name, len(p.colors))


def get_palette(name: str) -> Palette:
    if name not in _REGISTRY:
        raise KeyError(f"unknown palette {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_palettes() -> list[str]:
    return sorted(_REGISTRY)


def palettes() -> Iterable[Palette]:
    return _REGISTRY.values()


# ──────────────────────────── built-in palettes ────────────────────────────

_OKABE_ITO = (
    "#000000",  # black
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
)

register_palette(
    Palette(
        name="okabe_ito",
        colors=_OKABE_ITO,
        description="Okabe & Ito color-universal design palette (8 colors).",
    )
)

register_palette(
    Palette(
        name="sex_dimorphic",
        colors=("#C73E7F", "#1F77B4", "#666666"),
        semantic={"F": "#C73E7F", "M": "#1F77B4", "pooled": "#666666"},
        description="Magenta female / blue male / grey pooled.",
    )
)

register_palette(
    Palette(
        name="home_gate_trap",
        colors=("#2E7D32", "#F9A825", "#C62828"),
        semantic={"HOME": "#2E7D32", "GATE": "#F9A825", "TRAP": "#C62828"},
        description="Tristability well palette (green/amber/red).",
    )
)

register_palette(
    Palette(
        name="wt_ko",
        colors=("#222222", "#D81B60"),
        semantic={"WT": "#222222", "KO": "#D81B60"},
        description="Wild-type vs. knockout.",
    )
)

register_palette(
    Palette(
        name="redox_bistable",
        colors=("#1565C0", "#E53935", "#8E24AA"),
        semantic={"reduced": "#1565C0", "oxidized": "#E53935", "intermediate": "#8E24AA"},
        description="Reduced / oxidized / intermediate for redox bistability.",
    )
)

register_palette(
    Palette(
        name="fret_donor_acceptor",
        colors=("#00BFA5", "#FFB300"),
        semantic={"donor": "#00BFA5", "acceptor": "#FFB300", "ratio_up": "#D84315", "ratio_down": "#1565C0"},
        description="Teal donor / amber acceptor with ratio accents.",
    )
)

register_palette(
    Palette(
        name="sex_x_genotype",
        colors=("#C73E7F", "#1F77B4", "#F48FB1", "#7FB3D5"),
        semantic={
            "F_WT": "#C73E7F",
            "M_WT": "#1F77B4",
            "F_KO": "#F48FB1",
            "M_KO": "#7FB3D5",
        },
        description="Saturated = WT, pastel = KO; magenta = female, blue = male.",
    )
)

register_palette(
    Palette(
        name="timepoint_gradient",
        colors=("#EDF8B1", "#7FCDBB", "#2C7FB8", "#253494"),
        description="4-step cool gradient for time-series overlays.",
    )
)

register_palette(
    Palette(
        name="mechanism_class",
        colors=("#5E35B1", "#00897B", "#F4511E", "#546E7A"),
        semantic={
            "signaling": "#5E35B1",
            "metabolic": "#00897B",
            "cytoskeletal": "#F4511E",
            "other": "#546E7A",
        },
        description="Broad mechanism categories for pathway figures.",
    )
)

register_palette(
    Palette(
        name="cytoskeleton_components",
        colors=("#E91E63", "#00BCD4", "#FFC107"),
        semantic={"actin": "#E91E63", "microtubule": "#00BCD4", "intermediate_filament": "#FFC107"},
        description="Actin / MT / IF component palette.",
    )
)

register_palette(
    Palette(
        name="rhogtpase_family",
        colors=("#D81B60", "#1E88E5", "#43A047"),
        semantic={"RhoA": "#D81B60", "Rac1": "#1E88E5", "Cdc42": "#43A047"},
        description="Canonical RhoGTPase family colors.",
    )
)

register_palette(
    Palette(
        name="microglia_states",
        colors=("#37474F", "#26A69A", "#EF5350", "#AB47BC", "#FFA726"),
        semantic={
            "homeostatic": "#37474F",
            "surveillant": "#26A69A",
            "activated": "#EF5350",
            "DAM": "#AB47BC",
            "proliferative": "#FFA726",
        },
        description="Microglial state palette (homeostatic / DAM / etc).",
    )
)

register_palette(
    Palette(
        name="journal_neutral",
        colors=("#1F4E79", "#C0504D", "#9BBB59", "#8064A2", "#4BACC6", "#F79646"),
        description="Neutral journal-safe palette for venues that disallow bright colors.",
    )
)


# Convenience: `get` maps semantic strings to hex across the whole registry.
def semantic_color(palette_name: str, key: str, default: str | None = None) -> str:
    """Semantic lookup with optional fallback — used by recipes."""
    p = get_palette(palette_name)
    if key in p.semantic:
        return p.semantic[key]
    if default is not None:
        return default
    raise KeyError(f"palette {palette_name!r} has no semantic key {key!r}")
