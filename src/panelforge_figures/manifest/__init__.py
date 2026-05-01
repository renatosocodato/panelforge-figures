"""Manifest schema, resolver, and catalog generator."""

from .auto_tag import auto_tag_all, auto_tag_recipe
from .catalog import (
    INDEX_SCHEMA_VERSION,
    build_catalog,
    build_index,
    catalog_fingerprint,
    emit_index_json,
    write_catalog_json,
)
from .intake import (
    INTAKE_QUESTIONS,
    IntakeAnswer,
    IntakeQuestion,
    intake_questions_for_index,
    run_intake_interactive,
)
from .resolver import render_manifest, resolve_panel_data, validate_manifest
from .schema import FigureSpec, Manifest, PanelSpec, load_manifest
from .scoring import (
    DEFAULT_SHORTLIST_SIZE,
    MINIMUM_SCORE_FOR_SHORTLIST,
    SCORING_RUBRIC_VERSION,
    WEIGHTS,
    ProjectProfile,
    ScoredRecipe,
    score_recipes,
    scoring_rubric_dict,
)

__all__ = [
    "DEFAULT_SHORTLIST_SIZE",
    "FigureSpec",
    "INDEX_SCHEMA_VERSION",
    "INTAKE_QUESTIONS",
    "IntakeAnswer",
    "IntakeQuestion",
    "MINIMUM_SCORE_FOR_SHORTLIST",
    "Manifest",
    "PanelSpec",
    "ProjectProfile",
    "SCORING_RUBRIC_VERSION",
    "ScoredRecipe",
    "WEIGHTS",
    "auto_tag_all",
    "auto_tag_recipe",
    "build_catalog",
    "build_index",
    "catalog_fingerprint",
    "emit_index_json",
    "intake_questions_for_index",
    "load_manifest",
    "render_manifest",
    "resolve_panel_data",
    "run_intake_interactive",
    "score_recipes",
    "scoring_rubric_dict",
    "validate_manifest",
    "write_catalog_json",
]
