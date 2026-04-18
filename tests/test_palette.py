"""Palette registry sanity tests."""

import pytest

from panelforge_figures.core.palette import (
    Palette,
    get_palette,
    list_palettes,
    register_palette,
    semantic_color,
)


def test_all_required_palettes_are_registered():
    required = {
        "okabe_ito",
        "sex_dimorphic",
        "home_gate_trap",
        "wt_ko",
        "redox_bistable",
        "fret_donor_acceptor",
        "sex_x_genotype",
        "timepoint_gradient",
        "mechanism_class",
        "cytoskeleton_components",
        "rhogtpase_family",
        "microglia_states",
        "journal_neutral",
    }
    assert required.issubset(set(list_palettes()))


def test_home_gate_trap_semantic_lookup():
    p = get_palette("home_gate_trap")
    assert p.pick("HOME") == "#2E7D32"
    assert p.pick("GATE") == "#F9A825"
    assert p.pick("TRAP") == "#C62828"


def test_sex_dimorphic_pooled_exists():
    c = semantic_color("sex_dimorphic", "pooled")
    assert c.startswith("#") and len(c) == 7


def test_take_cycles_colors():
    p = get_palette("okabe_ito")
    n = len(p.colors)
    first = p.take(n)
    second = p.take(n * 2)
    assert first == p.colors
    assert second[n:] == p.colors  # wraps around


def test_register_palette_refuses_duplicate():
    with pytest.raises(ValueError):
        register_palette(
            Palette(name="okabe_ito", colors=("#000",)),
            overwrite=False,
        )
