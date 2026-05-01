"""Manifest schema, resolver, and catalog generator."""

from .catalog import (
    INDEX_SCHEMA_VERSION,
    build_catalog,
    build_index,
    catalog_fingerprint,
    emit_index_json,
    write_catalog_json,
)
from .resolver import render_manifest, resolve_panel_data, validate_manifest
from .schema import FigureSpec, Manifest, PanelSpec, load_manifest

__all__ = [
    "FigureSpec",
    "INDEX_SCHEMA_VERSION",
    "Manifest",
    "PanelSpec",
    "build_catalog",
    "build_index",
    "catalog_fingerprint",
    "emit_index_json",
    "load_manifest",
    "render_manifest",
    "resolve_panel_data",
    "validate_manifest",
    "write_catalog_json",
]
