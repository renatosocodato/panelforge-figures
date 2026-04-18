"""Base style sanity tests."""

import matplotlib as mpl

from panelforge_figures.core.style import (
    PF_FONT_STACK,
    apply_base_style,
    current_theme,
    temporary_style,
)


def test_apply_base_style_sets_font_and_tick_rcparams():
    apply_base_style()
    assert mpl.rcParams["font.family"] == ["sans-serif"]
    assert mpl.rcParams["font.sans-serif"][0] == PF_FONT_STACK[0]
    assert mpl.rcParams["pdf.fonttype"] == 42
    assert mpl.rcParams["ps.fonttype"] == 42
    assert mpl.rcParams["svg.fonttype"] == "none"
    assert mpl.rcParams["axes.spines.top"] is False
    assert mpl.rcParams["axes.spines.right"] is False
    assert mpl.rcParams["xtick.direction"] == "out"
    assert mpl.rcParams["ytick.direction"] == "out"


def test_apply_base_style_accepts_overrides_and_records_theme():
    apply_base_style(theme="pnas", overrides={"axes.labelsize": 9.5})
    assert mpl.rcParams["axes.labelsize"] == 9.5
    assert current_theme() == "pnas"


def test_temporary_style_restores_rcparams():
    apply_base_style()
    before = float(mpl.rcParams["axes.labelsize"])
    with temporary_style({"axes.labelsize": before + 2}):
        assert mpl.rcParams["axes.labelsize"] == before + 2
    assert mpl.rcParams["axes.labelsize"] == before
