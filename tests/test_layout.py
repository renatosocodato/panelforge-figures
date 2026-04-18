"""Layout helpers — size presets + gridspec."""

import matplotlib.pyplot as plt

from panelforge_figures.core.layout import (
    FIGSIZE_PRESETS,
    make_figure,
    make_panel_grid,
    panel_tag,
    suptitle_with_subtitle,
)


def test_all_required_presets_present():
    required = {
        "single", "single_sq", "1p5", "double",
        "double_sq", "tall", "a4_portrait", "a4_landscape",
    }
    assert required.issubset(FIGSIZE_PRESETS)


def test_make_figure_accepts_preset_and_tuple():
    fig1 = make_figure("single")
    assert tuple(fig1.get_size_inches()) == FIGSIZE_PRESETS["single"]
    fig2 = make_figure((6.0, 4.0))
    assert tuple(fig2.get_size_inches()) == (6.0, 4.0)
    plt.close(fig1)
    plt.close(fig2)


def test_make_panel_grid_and_panel_tag():
    fig = make_figure("double")
    gs = make_panel_grid(fig, 2, 2)
    ax = fig.add_subplot(gs[0, 0])
    panel_tag(ax, "A")
    texts = [t.get_text() for t in ax.texts]
    assert "A" in texts
    plt.close(fig)


def test_suptitle_with_subtitle_adds_two_text_artists():
    fig = make_figure("single")
    suptitle_with_subtitle(fig, "Title", "subtitle here")
    # fig.texts contains the subtitle; fig._suptitle stores the suptitle.
    assert fig._suptitle is not None
    assert any(t.get_text() == "subtitle here" for t in fig.texts)
    plt.close(fig)
