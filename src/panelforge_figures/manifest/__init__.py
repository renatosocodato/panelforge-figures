"""Manifest schema, resolver, and catalog generator."""

from .catalog import build_catalog, catalog_fingerprint, write_catalog_json
from .resolver import render_manifest, resolve_panel_data, validate_manifest
from .schema import FigureSpec, Manifest, PanelSpec, load_manifest

__all__ = [
    "FigureSpec",
    "Manifest",
    "PanelSpec",
    "build_catalog",
    "catalog_fingerprint",
    "load_manifest",
    "render_manifest",
    "resolve_panel_data",
    "validate_manifest",
    "write_catalog_json",
]
