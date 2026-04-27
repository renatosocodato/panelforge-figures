"""Core layer — style, palette, primitives, layout, export, contracts, QA."""

from .aesthetic_base import AnnotationStyle, InsetConvention, ModalityAesthetic
from .contract import RecipeContract, RecipeFamily, RecipeMetadata, register_recipe
from .export import export_figure, multi_format_export
from .gam_logistic_utility import fit_phase_boundary
from .hmm_decoding_utility import (
    decode_states,
    decode_states_semi,
    fit_summary,
)
from .km_survival_utility import kaplan_meier
from .layout import FIGSIZE_PRESETS, make_figure, make_panel_grid
from .palette import Palette, get_palette, list_palettes, register_palette
from .primitives import (
    add_halo_label,
    bootstrap_ci,
    callout_box,
    colored_bracket,
    density_alpha,
    empty_data_guard,
    fixed_point_marker,
    right_of_ci_label,
    saddle_node_star,
    shaded_regime,
    smart_fmt,
    smart_place_callout,
    violin_with_ring_markers,
)
from .qa import (
    FigureIntegrityIssue,
    FigureIntegrityReport,
    check_figure_integrity,
)
from .style import (
    PF_FONT_SIZES,
    PF_FONT_STACK,
    PF_LINE_WIDTHS,
    apply_base_style,
    current_theme,
    is_approved_font_family,
)
from .tost_bounds_utility import (
    classify_outcome,
    tost_band_patch,
)

__all__ = [
    "FIGSIZE_PRESETS",
    "FigureIntegrityIssue",
    "FigureIntegrityReport",
    "PF_FONT_SIZES",
    "PF_FONT_STACK",
    "PF_LINE_WIDTHS",
    "AnnotationStyle",
    "InsetConvention",
    "ModalityAesthetic",
    "Palette",
    "RecipeContract",
    "RecipeFamily",
    "RecipeMetadata",
    "add_halo_label",
    "apply_base_style",
    "bootstrap_ci",
    "callout_box",
    "check_figure_integrity",
    "classify_outcome",
    "colored_bracket",
    "current_theme",
    "decode_states",
    "decode_states_semi",
    "density_alpha",
    "empty_data_guard",
    "export_figure",
    "fit_phase_boundary",
    "fit_summary",
    "fixed_point_marker",
    "get_palette",
    "is_approved_font_family",
    "kaplan_meier",
    "list_palettes",
    "make_figure",
    "make_panel_grid",
    "multi_format_export",
    "register_palette",
    "register_recipe",
    "right_of_ci_label",
    "saddle_node_star",
    "shaded_regime",
    "smart_fmt",
    "smart_place_callout",
    "tost_band_patch",
    "violin_with_ring_markers",
]
