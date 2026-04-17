"""Core layer — style, palette, primitives, layout, export, contracts."""

from .aesthetic_base import AnnotationStyle, InsetConvention, ModalityAesthetic
from .contract import RecipeContract, RecipeFamily, RecipeMetadata, register_recipe
from .export import export_figure, multi_format_export
from .layout import FIGSIZE_PRESETS, make_figure, make_panel_grid
from .palette import Palette, get_palette, list_palettes, register_palette
from .primitives import (
    add_halo_label,
    bootstrap_ci,
    callout_box,
    colored_bracket,
    density_alpha,
    fixed_point_marker,
    right_of_ci_label,
    saddle_node_star,
    shaded_regime,
    smart_fmt,
    violin_with_ring_markers,
)
from .style import PF_FONT_STACK, apply_base_style, current_theme

__all__ = [
    "FIGSIZE_PRESETS",
    "PF_FONT_STACK",
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
    "colored_bracket",
    "current_theme",
    "density_alpha",
    "export_figure",
    "fixed_point_marker",
    "get_palette",
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
    "violin_with_ring_markers",
]
