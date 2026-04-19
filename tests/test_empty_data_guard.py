"""Unit tests for the empty-data guard primitive."""

from __future__ import annotations

import matplotlib.pyplot as plt

from panelforge_figures.core import empty_data_guard


def test_empty_input_draws_placeholder():
    fig, ax = plt.subplots()
    try:
        handled = empty_data_guard(ax, n_points=0, message="no cells")
        assert handled is True
        # A single muted placeholder text should be present.
        placeholder_texts = [
            t.get_text() for t in ax.texts if t.get_text()
        ]
        assert placeholder_texts == ["no cells"]
        # Spines and ticks are hidden so the panel reads as intentional.
        assert not any(ax.spines[s].get_visible()
                       for s in ("top", "right", "left", "bottom"))
        assert ax.get_xticks().size == 0
        assert ax.get_yticks().size == 0
    finally:
        plt.close(fig)


def test_non_empty_input_is_a_no_op():
    fig, ax = plt.subplots()
    try:
        handled = empty_data_guard(ax, n_points=3)
        assert handled is False
        # No placeholder text, default spines intact.
        assert len(ax.texts) == 0
        assert ax.spines["bottom"].get_visible()
        assert ax.spines["left"].get_visible()
    finally:
        plt.close(fig)


def test_min_points_threshold():
    """min_points lets recipes require more than one sample (e.g. violins)."""
    fig, ax = plt.subplots()
    try:
        handled = empty_data_guard(ax, n_points=2, min_points=5,
                                   message="need ≥5 points")
        assert handled is True
    finally:
        plt.close(fig)
