"""Unit tests for :mod:`panelforge_figures.core.qa`.

These tests exercise the QA checker in isolation by constructing tiny
figures that deliberately violate each rule. The cross-modality sweep
test (``test_cross_modality_qa.py``) then asserts no real recipe trips
any of the rules.
"""

from __future__ import annotations

import matplotlib.pyplot as plt

from panelforge_figures.core import apply_base_style
from panelforge_figures.core.qa import check_figure_integrity


def _fresh_fig():
    apply_base_style()
    fig, ax = plt.subplots(figsize=(3.0, 2.0))
    ax.plot([0, 1], [0, 1])
    ax.set_title("ok")
    return fig, ax


def test_clean_figure_reports_ok():
    fig, _ = _fresh_fig()
    try:
        report = check_figure_integrity(fig)
        assert report.ok
        assert report.errors == []
    finally:
        plt.close(fig)


def test_detects_non_approved_font():
    fig, ax = _fresh_fig()
    ax.text(0.5, 0.5, "bad", fontfamily="Times New Roman")
    try:
        report = check_figure_integrity(fig)
        rules = [i.rule for i in report.errors]
        assert "font_family" in rules
    finally:
        plt.close(fig)


def test_detects_too_small_font():
    fig, ax = _fresh_fig()
    ax.text(0.5, 0.5, "tiny", fontsize=3.0)
    try:
        report = check_figure_integrity(fig)
        rules = [i.rule for i in report.errors]
        assert "font_size_too_small" in rules
    finally:
        plt.close(fig)


def test_detects_empty_axes():
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(4.0, 2.0))
    ax_left.plot([0, 1], [0, 1])
    # ax_right intentionally left empty — should be flagged.
    try:
        report = check_figure_integrity(fig)
        rules = [i.rule for i in report.errors]
        assert "empty_axes" in rules
    finally:
        plt.close(fig)


def test_axis_off_is_not_flagged_as_empty():
    """An axis whose xaxis + yaxis are both hidden is intentional decoration."""
    fig, ax = plt.subplots(figsize=(2.0, 2.0))
    ax.axis("off")
    try:
        report = check_figure_integrity(fig)
        assert "empty_axes" not in [i.rule for i in report.errors]
    finally:
        plt.close(fig)
