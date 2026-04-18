"""Primitive helpers: smart_fmt, halo labels, bootstrap CI, density alpha."""

import matplotlib.pyplot as plt
import numpy as np

from panelforge_figures.core.primitives import (
    add_halo_label,
    bootstrap_ci,
    density_alpha,
    right_of_ci_label,
    smart_fmt,
)


def test_smart_fmt_three_decimals_below_threshold():
    assert smart_fmt(0.0034) == "0.003"
    assert smart_fmt(0.009) == "0.009"


def test_smart_fmt_two_decimals_above_threshold():
    assert smart_fmt(0.123) == "0.12"
    assert smart_fmt(-1.5)  == "-1.50"
    assert smart_fmt(42.0)  == "42.00"


def test_smart_fmt_nan_and_none():
    assert smart_fmt(None) == ""
    assert smart_fmt(float("nan")) == "nan"


def test_halo_label_returns_plain_text_no_stroke():
    """add_halo_label was historically a stroked label; post-crispness
    pass it renders plain text (no path effects, no bbox, no stroke)
    regardless of the historical `halo_width` kwarg.
    """
    fig, ax = plt.subplots()
    t = add_halo_label(ax, 0.5, 0.5, "hello", halo_width=3.0)
    assert t.get_text() == "hello"
    # No path effects (no stroke), and no bbox applied.
    assert not t.get_path_effects()
    assert t.get_bbox_patch() is None
    plt.close(fig)


def test_right_of_ci_label_places_right_of_upper_ci():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10)
    right_of_ci_label(ax, y=0, upper_ci=3.0, estimate=2.5)
    labels = [t for t in ax.texts]
    assert len(labels) == 1
    x_pos, _ = labels[0].get_position()
    assert x_pos > 3.0, "text must sit to the right of the upper CI extent"
    plt.close(fig)


def test_density_alpha_bounds():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(500)
    y = rng.standard_normal(500)
    alpha = density_alpha(x, y)
    assert alpha.shape == x.shape
    assert float(alpha.min()) >= 0.08 - 1e-9
    assert float(alpha.max()) <= 0.9 + 1e-9


def test_bootstrap_ci_shape_and_ordering():
    rng = np.random.default_rng(1)
    x = np.linspace(0, 10, 50)
    y = 1.5 * x + rng.normal(0, 0.4, x.size)
    xg, mean, lo, hi = bootstrap_ci(x, y, fit="linear", n_resamples=200)
    assert xg.size == mean.size == lo.size == hi.size
    assert np.all(lo <= mean + 1e-9)
    assert np.all(mean <= hi + 1e-9)
