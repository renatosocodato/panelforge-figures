"""Jupyter notebook integration for panelforge-figures.

Lazy-loads heavy deps (IPython, matplotlib) so the base install stays slim.
"""
from .api import (
    AuditWrapper,
    NotebookError,
    ProfileReport,
    RecommendationReport,
    RenderResult,
    audit_bias,
    audit_venue,
    lint_xrefs,
    profile,
    recommend,
    render,
    scout,
    verify_claims,
)

__all__ = [
    "AuditWrapper",
    "NotebookError",
    "ProfileReport",
    "RecommendationReport",
    "RenderResult",
    "audit_bias",
    "audit_venue",
    "lint_xrefs",
    "profile",
    "recommend",
    "render",
    "scout",
    "verify_claims",
]


def load_ipython_extension(ipython):  # pragma: no cover — IPython hook
    """Entry point for `%load_ext panelforge_figures.notebook`.

    Delegates to :func:`panelforge_figures.notebook.magic.load_ipython_extension`.
    """
    from .magic import load_ipython_extension as _impl
    _impl(ipython)
