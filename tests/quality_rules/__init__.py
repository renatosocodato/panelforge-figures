"""Per-family quality assertions invoked by tests/test_recipes_quality.py."""

from __future__ import annotations

from collections.abc import Callable

from .grant import (
    assert_conceptual_ok,
    assert_flow_ok,
    assert_gantt_ok,
    assert_matrix_ok,
)
from .meta import (
    assert_diagnostic_curve_ok,
    assert_ladder_ok,
    assert_radar_ok,
)
from .sensitivity import (
    assert_contour_ok,
    assert_scatter_collapse_ok,
    assert_sobol_bar_ok,
)

RULES: dict[str, Callable] = {
    "conceptual": assert_conceptual_ok,
    "flow": assert_flow_ok,
    "gantt": assert_gantt_ok,
    "matrix": assert_matrix_ok,
    "diagnostic_curve": assert_diagnostic_curve_ok,
    "ladder": assert_ladder_ok,
    "radar": assert_radar_ok,
    "contour": assert_contour_ok,
    "scatter_collapse": assert_scatter_collapse_ok,
    "sobol_bar": assert_sobol_bar_ok,
}
