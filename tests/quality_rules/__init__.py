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
from .omics import (
    assert_volcano_ok,
)
from .rhogtpase import (
    assert_bifurcation_ok,
    assert_phase_portrait_ok,
)
from .sensitivity import (
    assert_contour_ok,
    assert_scatter_collapse_ok,
    assert_sobol_bar_ok,
)
from .shared import (
    assert_coef_forest_ok,
    assert_heatmap_ok,
    assert_hysteresis_loop_ok,
    assert_ridge_by_group_ok,
    assert_split_violin_ok,
    assert_timecourse_hierarchical_ci_ok,
)

RULES: dict[str, Callable] = {
    # Grant families.
    "conceptual": assert_conceptual_ok,
    "flow": assert_flow_ok,
    "gantt": assert_gantt_ok,
    "matrix": assert_matrix_ok,
    # Meta / diagnostic.
    "diagnostic_curve": assert_diagnostic_curve_ok,
    "ladder": assert_ladder_ok,
    "radar": assert_radar_ok,
    # Sensitivity-like.
    "contour": assert_contour_ok,
    "scatter_collapse": assert_scatter_collapse_ok,
    "sobol_bar": assert_sobol_bar_ok,
    # RhoGTPase dynamics.
    "phase_portrait": assert_phase_portrait_ok,
    "bifurcation": assert_bifurcation_ok,
    # Omics.
    "volcano": assert_volcano_ok,
    # Shared across modalities.
    "heatmap": assert_heatmap_ok,
    "ridge_by_group": assert_ridge_by_group_ok,
    "timecourse_hierarchical_ci": assert_timecourse_hierarchical_ci_ok,
    "coef_forest": assert_coef_forest_ok,
    "split_violin": assert_split_violin_ok,
    "hysteresis_loop": assert_hysteresis_loop_ok,
}
