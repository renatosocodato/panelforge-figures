"""Notebook-native Python API for panelforge-figures.

Wraps CLI surfaces — profile / recommend / render / scout / audit-* /
lint-xrefs / verify-claims — into idiomatic Python callables that
return rich-display objects suitable for Jupyter.

Design goals
------------
* No mandatory IPython import — the rich-display methods (``_repr_html_`` /
  ``_repr_markdown_`` / ``_repr_png_``) are duck-typed so Jupyter picks them
  up automatically when available; pure-text fallbacks keep the API usable
  from the plain Python REPL.
* All heavy imports (pandas, matplotlib, manuscript_parse, etc.) are
  lazy — importing :mod:`panelforge_figures.notebook` does not load
  pandas.
* Each public function returns a frozen dataclass so callers can
  introspect / serialise the result without re-running the audit.

Public surface
--------------
:exc:`NotebookError` — raised on notebook-specific failures.
:class:`ProfileReport` — wraps E8 data-profile output.
:class:`RecommendationReport` — wraps E8 family-recommend output.
:class:`AuditWrapper` — wraps E11/E15/E16/E17 audit reports.
:class:`RenderResult` — wraps a rendered matplotlib figure.
:func:`profile` — profile a data file.
:func:`recommend` — profile + recommend families + detect gaps.
:func:`render` — render a recipe to a matplotlib Figure (optionally save).
:func:`scout` — run E11 project scout.
:func:`audit_venue` — run E16 venue auditor.
:func:`audit_bias` — run E17 bias auditor.
:func:`lint_xrefs` — run E15 xref linter.
:func:`verify_claims` — run E11 claim-check.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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


# --------------------------------------------------------------------------- #
# Errors                                                                      #
# --------------------------------------------------------------------------- #


class NotebookError(RuntimeError):
    """Raised on Jupyter-specific failures (missing IPython, render failure,
    unknown recipe, etc.).
    """


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _esc(value: Any) -> str:
    """HTML-escape a value, coercing to str first."""
    return html.escape(str(value), quote=True)


def _verdict_color(verdict: str) -> str:
    """Map a verdict / overall-status string to a CSS background colour.

    Returns a soft pastel hex string so the rendered box stays readable in
    both light and dark Jupyter themes.
    """
    v = verdict.lower()
    if v in {"ready_to_submit", "honest", "clean", "passed", "ok"}:
        return "#e8f5e9"
    if v in {"needs_revision", "needs_review", "warnings", "warn"}:
        return "#fff8e1"
    if v in {"blocked", "concerning", "errors", "failed", "fail"}:
        return "#ffebee"
    return "#f5f5f5"


def _verdict_text_color(verdict: str) -> str:
    """Companion to :func:`_verdict_color` — high-contrast text colour."""
    v = verdict.lower()
    if v in {"ready_to_submit", "honest", "clean", "passed", "ok"}:
        return "#1b5e20"
    if v in {"needs_revision", "needs_review", "warnings", "warn"}:
        return "#ef6c00"
    if v in {"blocked", "concerning", "errors", "failed", "fail"}:
        return "#b71c1c"
    return "#424242"


def _confidence_bar_html(value: float, *, width_px: int = 120) -> str:
    """Render a CSS-only horizontal confidence bar with a numeric label.

    Values are clamped to ``[0, 1]``. The bar's hue ramps from amber
    (<0.5) to green (>=0.5) to give the eye a quick read of recipe fit.
    """
    pct = max(0.0, min(1.0, float(value)))
    fill_px = int(pct * width_px)
    if pct >= 0.7:
        hue = "#2e7d32"
    elif pct >= 0.5:
        hue = "#558b2f"
    elif pct >= 0.3:
        hue = "#ef6c00"
    else:
        hue = "#c62828"
    return (
        f'<div style="display:inline-block;vertical-align:middle;'
        f'width:{width_px}px;height:10px;background:#eee;'
        f'border:1px solid #ccc;border-radius:3px;overflow:hidden;'
        f'margin-right:6px;">'
        f'<div style="width:{fill_px}px;height:100%;background:{hue};"></div>'
        f"</div>"
        f'<span style="font-family:monospace;">{pct:.2f}</span>'
    )


# --------------------------------------------------------------------------- #
# ProfileReport                                                               #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProfileReport:
    """Wraps an E8 :class:`DataProfile` for inline notebook display."""

    data_path: Path
    profile_dict: dict[str, Any]

    def _repr_html_(self) -> str:
        d = self.profile_dict
        rows: list[str] = []
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">rows</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("n_rows"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">columns</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("n_cols"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">numeric</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("n_numeric"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">categorical</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("n_categorical"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">binary</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("n_binary"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">missing (fraction)</th>'
            f'<td style="padding:4px 8px;">{float(d.get("fraction_missing", 0.0)):.3f}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">grouping</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("grouping_structure"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">has paired id</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("has_paired_id"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">has time column</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("has_time_column"))}</td></tr>'
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;">detected 2x2</th>'
            f'<td style="padding:4px 8px;">{_esc(d.get("detected_2x2"))}</td></tr>'
        )

        # Column kinds as a sub-table.
        col_kinds = d.get("column_kinds", {}) or {}
        cols_html = "<br>".join(
            f"<code>{_esc(k)}</code> → {_esc(v)}" for k, v in col_kinds.items()
        )
        rows.append(
            f'<tr><th style="text-align:left;padding:4px 8px;vertical-align:top;">'
            f"columns</th>"
            f'<td style="padding:4px 8px;">{cols_html}</td></tr>'
        )

        return (
            '<div style="font-family:sans-serif;border:1px solid #ddd;'
            'border-radius:4px;padding:8px;margin:4px 0;">'
            f'<div style="font-weight:bold;margin-bottom:6px;">'
            f"ProfileReport: <code>{_esc(self.data_path)}</code></div>"
            '<table style="border-collapse:collapse;">' + "".join(rows) + "</table>"
            "</div>"
        )

    def _repr_markdown_(self) -> str:
        d = self.profile_dict
        col_kinds = d.get("column_kinds", {}) or {}
        col_lines = "\n".join(f"  - `{k}` → {v}" for k, v in col_kinds.items())
        return (
            f"### ProfileReport: `{self.data_path}`\n\n"
            f"- rows: **{d.get('n_rows')}**\n"
            f"- columns: **{d.get('n_cols')}**\n"
            f"- numeric / categorical / binary: "
            f"{d.get('n_numeric')} / {d.get('n_categorical')} / {d.get('n_binary')}\n"
            f"- missing fraction: {float(d.get('fraction_missing', 0.0)):.3f}\n"
            f"- grouping: `{d.get('grouping_structure')}`\n"
            f"- paired id: {d.get('has_paired_id')}  •  time column: "
            f"{d.get('has_time_column')}  •  2x2: {d.get('detected_2x2')}\n\n"
            "**Columns**:\n" + col_lines
        )

    def __repr__(self) -> str:
        d = self.profile_dict
        return (
            f"ProfileReport(path={self.data_path!s}, "
            f"rows={d.get('n_rows')}, cols={d.get('n_cols')}, "
            f"numeric={d.get('n_numeric')}, categorical={d.get('n_categorical')}, "
            f"grouping={d.get('grouping_structure')!r})"
        )


# --------------------------------------------------------------------------- #
# RecommendationReport                                                        #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RecommendationReport:
    """Wraps :func:`recommend_families` output for inline notebook display."""

    data_path: Path
    profile: dict[str, Any]
    recommendations: list[dict[str, Any]]
    gaps: list[dict[str, Any]]

    def _repr_html_(self) -> str:
        # Header: data path + summary numbers.
        header = (
            '<div style="font-family:sans-serif;border:1px solid #ddd;'
            'border-radius:4px;padding:8px;margin:4px 0;">'
            f'<div style="font-weight:bold;margin-bottom:6px;">'
            f"RecommendationReport: <code>{_esc(self.data_path)}</code></div>"
            f'<div style="color:#555;margin-bottom:8px;">'
            f"{len(self.recommendations)} recommendation"
            f"{'s' if len(self.recommendations) != 1 else ''}"
            f" • {len(self.gaps)} gap{'s' if len(self.gaps) != 1 else ''}"
            "</div>"
        )

        # Recommendations table.
        recs_rows: list[str] = []
        if self.recommendations:
            recs_rows.append(
                '<tr style="background:#fafafa;">'
                '<th style="text-align:left;padding:4px 8px;">family</th>'
                '<th style="text-align:left;padding:4px 8px;">confidence</th>'
                '<th style="text-align:left;padding:4px 8px;">recipes</th>'
                '<th style="text-align:left;padding:4px 8px;">rationale</th>'
                "</tr>"
            )
            for rec in self.recommendations:
                conf = float(rec.get("confidence", 0.0))
                recs_rows.append(
                    "<tr>"
                    f'<td style="padding:4px 8px;"><code>{_esc(rec.get("family"))}</code></td>'
                    f'<td style="padding:4px 8px;">{_confidence_bar_html(conf)}</td>'
                    f'<td style="padding:4px 8px;">{_esc(rec.get("n_matching_recipes"))}</td>'
                    f'<td style="padding:4px 8px;color:#444;">{_esc(rec.get("rationale"))}</td>'
                    "</tr>"
                )
            recs_html = (
                '<table style="border-collapse:collapse;width:100%;">'
                + "".join(recs_rows)
                + "</table>"
            )
        else:
            recs_html = '<div style="color:#888;">No recommendations.</div>'

        recs_section = (
            '<div style="font-weight:bold;margin-top:6px;margin-bottom:4px;">'
            "Recommendations</div>" + recs_html
        )

        # Gaps section.
        if self.gaps:
            gap_rows: list[str] = [
                '<tr style="background:#fafafa;">'
                '<th style="text-align:left;padding:4px 8px;">family</th>'
                '<th style="text-align:left;padding:4px 8px;">suggested recipe</th>'
                '<th style="text-align:left;padding:4px 8px;">rationale</th>'
                "</tr>"
            ]
            for gap in self.gaps:
                gap_rows.append(
                    "<tr>"
                    f'<td style="padding:4px 8px;"><code>{_esc(gap.get("family"))}</code></td>'
                    f'<td style="padding:4px 8px;"><code>{_esc(gap.get("suggested_recipe_name"))}</code></td>'
                    f'<td style="padding:4px 8px;color:#444;">{_esc(gap.get("rationale"))}</td>'
                    "</tr>"
                )
            gaps_section = (
                '<div style="font-weight:bold;margin-top:8px;margin-bottom:4px;">'
                "Recipe gaps</div>"
                + '<table style="border-collapse:collapse;width:100%;">'
                + "".join(gap_rows)
                + "</table>"
            )
        else:
            gaps_section = ""

        return header + recs_section + gaps_section + "</div>"

    def _repr_markdown_(self) -> str:
        lines: list[str] = [
            f"### RecommendationReport: `{self.data_path}`",
            "",
            f"_{len(self.recommendations)} recommendation(s) • "
            f"{len(self.gaps)} gap(s)_",
            "",
            "**Recommendations**",
            "",
            "| family | confidence | recipes | rationale |",
            "| --- | --- | --- | --- |",
        ]
        for rec in self.recommendations:
            lines.append(
                f"| `{rec.get('family')}` "
                f"| {float(rec.get('confidence', 0.0)):.2f} "
                f"| {rec.get('n_matching_recipes')} "
                f"| {rec.get('rationale')} |"
            )
        if self.gaps:
            lines.extend(
                [
                    "",
                    "**Recipe gaps**",
                    "",
                    "| family | suggested recipe | rationale |",
                    "| --- | --- | --- |",
                ]
            )
            for gap in self.gaps:
                lines.append(
                    f"| `{gap.get('family')}` "
                    f"| `{gap.get('suggested_recipe_name')}` "
                    f"| {gap.get('rationale')} |"
                )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"RecommendationReport(path={self.data_path!s}, "
            f"n_recommendations={len(self.recommendations)}, "
            f"n_gaps={len(self.gaps)})"
        )


# --------------------------------------------------------------------------- #
# AuditWrapper                                                                #
# --------------------------------------------------------------------------- #


def _audit_status(kind: str, report_dict: dict[str, Any]) -> tuple[str, str]:
    """Return ``(status_label, verdict)`` for an audit report.

    The verdict drives the HTML banner colour. Each audit kind exposes
    slightly different fields, so we normalise here rather than at the
    call sites.
    """
    if kind == "venue":
        v = str(report_dict.get("overall_verdict", "unknown"))
        return v.replace("_", " ").title(), v
    if kind == "bias":
        v = str(report_dict.get("overall_verdict", "unknown"))
        return v.replace("_", " ").title(), v
    if kind == "lint-xrefs":
        v = str(report_dict.get("verdict", "unknown"))
        return v.title(), v
    if kind == "verify-claims":
        n_unsupported = int(report_dict.get("n_unsupported", 0))
        n_unv = int(report_dict.get("n_unverifiable", 0))
        if n_unsupported > 0:
            return "Unsupported claims found", "errors"
        if n_unv > 0:
            return "Partial: unverifiable claims", "warnings"
        return "Clean", "clean"
    if kind == "scout":
        plan = report_dict.get("figure_plan") or {}
        figs = plan.get("figures") or []
        return f"{len(figs)} figure(s) planned", "ok"
    return "unknown", "unknown"


@dataclass(frozen=True)
class AuditWrapper:
    """Generic notebook-display wrapper for audit reports."""

    kind: str                       # "venue" / "bias" / "lint-xrefs" / "verify-claims" / "scout"
    report_dict: dict[str, Any]
    markdown_repr: str

    def _repr_html_(self) -> str:
        label, verdict = _audit_status(self.kind, self.report_dict)
        bg = _verdict_color(verdict)
        fg = _verdict_text_color(verdict)
        title = self.kind.replace("-", " ").title()
        body = self._kind_body_html()
        return (
            f'<div style="font-family:sans-serif;border:1px solid #ccc;'
            f"border-radius:6px;padding:10px;margin:4px 0;background:{bg};"
            f'color:{fg};">'
            f'<div style="font-weight:bold;font-size:1.05em;margin-bottom:4px;">'
            f"{_esc(title)} — {_esc(label)}</div>"
            f"{body}</div>"
        )

    def _kind_body_html(self) -> str:
        """Render kind-specific summary HTML; falls through to a markdown box."""
        d = self.report_dict
        if self.kind == "venue":
            return (
                '<div style="font-family:monospace;">'
                f"errors: {_esc(d.get('n_errors'))} • "
                f"warnings: {_esc(d.get('n_warnings'))} • "
                f"info: {_esc(d.get('n_info'))} • "
                f"venue: <b>{_esc(d.get('venue'))}</b>"
                "</div>"
            )
        if self.kind == "bias":
            return (
                '<div style="font-family:monospace;">'
                f"errors: {_esc(d.get('n_errors'))} • "
                f"warnings: {_esc(d.get('n_warnings'))} • "
                f"info: {_esc(d.get('n_info'))} • "
                f"inspected: {_esc(d.get('n_figures_inspected'))} • "
                f"skipped: {_esc(d.get('n_figures_skipped'))}"
                "</div>"
            )
        if self.kind == "lint-xrefs":
            return (
                '<div style="font-family:monospace;">'
                f"errors: {_esc(d.get('n_errors'))} • "
                f"warnings: {_esc(d.get('n_warnings'))} • "
                f"refs: {_esc(d.get('n_referenced'))} • "
                f"blocks: {_esc(d.get('n_blocks'))} • "
                f"rendered: {_esc(d.get('n_rendered'))}"
                "</div>"
            )
        if self.kind == "verify-claims":
            return (
                '<div style="font-family:monospace;">'
                f"claims: {_esc(d.get('n_claims'))} • "
                f"supported: {_esc(d.get('n_supported'))} • "
                f"unsupported: {_esc(d.get('n_unsupported'))} • "
                f"unverifiable: {_esc(d.get('n_unverifiable'))}"
                "</div>"
            )
        if self.kind == "scout":
            plan = d.get("figure_plan") or {}
            figs = plan.get("figures") or []
            inv = d.get("inventory") or {}
            data_files = inv.get("data_files") or []
            return (
                '<div style="font-family:monospace;">'
                f"data files: {len(data_files)} • "
                f"figures planned: {len(figs)} • "
                f"manuscript: {_esc(inv.get('manuscript_path'))}"
                "</div>"
            )
        return f'<pre style="white-space:pre-wrap;">{_esc(self.markdown_repr)}</pre>'

    def _repr_markdown_(self) -> str:
        return self.markdown_repr

    def __repr__(self) -> str:
        label, _ = _audit_status(self.kind, self.report_dict)
        return f"AuditWrapper(kind={self.kind!r}, status={label!r})"


# --------------------------------------------------------------------------- #
# RenderResult                                                                #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RenderResult:
    """Wraps a rendered figure for inline notebook display.

    Attributes
    ----------
    figure
        The live ``matplotlib.figure.Figure`` — callers can keep mutating
        it (titles, axis labels, annotations) before saving.
    output_path
        Filesystem path where the figure was saved, or ``None`` when
        ``save=False`` was passed to :func:`render`.
    provenance
        Optional ProvenanceRecord-style dict; reserved for future
        integration with the E5 provenance machinery.
    """

    figure: Any                     # matplotlib.figure.Figure
    output_path: Path | None
    provenance: dict[str, Any] | None = field(default=None)

    def _repr_png_(self) -> bytes:
        """Delegate to matplotlib's built-in PNG rendering."""
        fig = self.figure
        # matplotlib.figure.Figure exposes _repr_png_; if missing we fall
        # back to manually rasterising via BytesIO.
        if hasattr(fig, "_repr_png_"):
            data = fig._repr_png_()
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
        from io import BytesIO

        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
        return buf.getvalue()

    def __repr__(self) -> str:
        return (
            f"RenderResult(figure={type(self.figure).__name__}, "
            f"output_path={self.output_path!s})"
        )


# --------------------------------------------------------------------------- #
# Public API: profile / recommend                                             #
# --------------------------------------------------------------------------- #


def profile(data_path: Path | str) -> ProfileReport:
    """Profile a data file. Returns a :class:`ProfileReport` that renders
    inline in Jupyter.

    Parameters
    ----------
    data_path
        Path to a ``.csv`` / ``.tsv`` / ``.parquet`` / ``.xlsx`` / ``.json``
        file (any source accepted by :func:`profile_data`).

    Returns
    -------
    ProfileReport

    Examples
    --------
    >>> from panelforge_figures.notebook import profile
    >>> p = profile("data/cells.csv")
    >>> p  # auto-renders as HTML table in Jupyter
    """
    from panelforge_figures.manifest.family_recommender import profile_data

    path = Path(data_path)
    prof = profile_data(path)
    return ProfileReport(data_path=path, profile_dict=prof.to_dict())


def recommend(
    data_path: Path | str,
    *,
    top_k: int = 5,
) -> RecommendationReport:
    """Profile a data file and recommend figure families.

    Wraps :func:`profile_data` + :func:`recommend_families` +
    :func:`detect_recipe_gaps` and returns a single
    :class:`RecommendationReport` that auto-renders inline.

    Parameters
    ----------
    data_path
        Path to a tabular data source.
    top_k
        Maximum number of family recommendations to keep (default 5).

    Returns
    -------
    RecommendationReport
    """
    from panelforge_figures.manifest.family_recommender import (
        detect_recipe_gaps,
        profile_data,
        recommend_families,
    )

    path = Path(data_path)
    prof = profile_data(path)
    recs = recommend_families(prof, top_k=top_k)
    gaps = detect_recipe_gaps(prof, recs)

    return RecommendationReport(
        data_path=path,
        profile=prof.to_dict(),
        recommendations=[
            {
                "family": r.family,
                "confidence": r.confidence,
                "rationale": r.rationale,
                "n_matching_recipes": r.n_matching_recipes,
                "matching_recipe_names": list(r.matching_recipe_names),
            }
            for r in recs
        ],
        gaps=[
            {
                "family": g.family,
                "suggested_recipe_name": g.suggested_recipe_name,
                "rationale": g.rationale,
            }
            for g in gaps
        ],
    )


# --------------------------------------------------------------------------- #
# Public API: render                                                          #
# --------------------------------------------------------------------------- #


def render(
    recipe_full_name: str,
    *,
    contract: Any = None,
    data: Any = None,
    save: bool = False,
    output_dir: Path | str | None = None,
    **kwargs: Any,
) -> RenderResult:
    """Render a registered recipe inline in Jupyter.

    Parameters
    ----------
    recipe_full_name
        ``"modality.recipe_name"`` — e.g.
        ``"biophysics_scaling.compartment_paired_delta_scatter"``.
    contract
        Either ``None`` (use the recipe's ``demo_contract``), a dict of
        keyword arguments forwarded to the recipe's
        :class:`RecipeContract`, or a pre-built ``RecipeContract``
        instance.
    data
        Reserved for future use (passing a DataFrame / file path);
        currently ignored — pass ``contract=`` directly.
    save
        When ``True``, save the figure to ``output_dir`` after rendering.
    output_dir
        Directory to save the PNG into (default
        ``panelforge_workspace/figures``).
    **kwargs
        Forwarded as extra keyword arguments to the recipe's
        ``render(...)`` function.

    Returns
    -------
    RenderResult
        Wraps the live ``matplotlib.figure.Figure`` and the optional
        output path.

    Raises
    ------
    NotebookError
        If the recipe is not registered, or if no contract / demo
        contract is available.
    """
    from panelforge_figures.core.contract import ensure_all_imported, get_recipe

    # Make sure every modality is imported so user-supplied recipe names
    # resolve (recipes only register on import).
    ensure_all_imported()

    try:
        rec_info = get_recipe(recipe_full_name)
    except KeyError as exc:
        raise NotebookError(f"recipe not found: {recipe_full_name!r}") from exc

    # Build the contract object.
    if contract is None:
        if rec_info.demo_contract is None:
            raise NotebookError(
                f"recipe {recipe_full_name!r} requires an explicit contract "
                "argument (no demo_contract registered)"
            )
        contract_obj = rec_info.demo_contract()
    elif isinstance(contract, dict):
        contract_obj = rec_info.contract(**contract)
    else:
        # Assume the caller already built a RecipeContract instance.
        contract_obj = contract

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    rec_info.render(contract_obj, ax=ax, **kwargs)

    output_path: Path | None = None
    if save:
        out_dir = Path(output_dir) if output_dir is not None else Path(
            "panelforge_workspace/figures"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = recipe_full_name.replace(".", "_")
        output_path = out_dir / f"{safe_name}.png"
        fig.savefig(output_path, dpi=300, bbox_inches="tight")

    return RenderResult(figure=fig, output_path=output_path, provenance=None)


# --------------------------------------------------------------------------- #
# Public API: scout / audit-* / lint / verify-claims                          #
# --------------------------------------------------------------------------- #


def scout(
    project_root: Path | str = ".",
    **kwargs: Any,
) -> AuditWrapper:
    """Run :func:`scout_project` (E11) inline in Jupyter.

    Parameters
    ----------
    project_root
        Directory containing the project tree to walk.
    **kwargs
        Forwarded to :func:`scout_project` — accepts ``max_figures``,
        ``venue``, ``target_novelty``, ``consensus_client``,
        ``use_mock_novelty``, ``manuscript_policy``.

    Returns
    -------
    AuditWrapper
        With ``kind="scout"``.
    """
    from panelforge_figures.manifest.scout import (
        render_scout_report_markdown,
        scout_project,
    )

    kwargs.setdefault("use_mock_novelty", True)
    report = scout_project(Path(project_root), **kwargs)
    return AuditWrapper(
        kind="scout",
        report_dict=report.to_dict(),
        markdown_repr=render_scout_report_markdown(report),
    )


def audit_venue(
    manuscript_path: Path | str,
    *,
    venue: str,
    **kwargs: Any,
) -> AuditWrapper:
    """Run the E16 venue auditor inline in Jupyter.

    Parameters
    ----------
    manuscript_path
        Path to the manuscript (``.tex`` / ``.md``).
    venue
        Target venue name (``"nature"`` / ``"cell"`` / ``"nejm"`` / ...
        — any value of :class:`Venue`).
    **kwargs
        Forwarded to :func:`venue_auditor.audit_venue` — accepts
        ``figures_dir``, ``bib_path``, ``n_main_figures``,
        ``n_main_tables``.

    Returns
    -------
    AuditWrapper
        With ``kind="venue"``.
    """
    from panelforge_figures.manifest.venue_auditor import (
        Venue,
        render_venue_audit_markdown,
    )
    from panelforge_figures.manifest.venue_auditor import (
        audit_venue as _audit_venue,
    )

    # Coerce figures_dir from str→Path if provided as a string.
    if "figures_dir" in kwargs and kwargs["figures_dir"] is not None:
        kwargs["figures_dir"] = Path(kwargs["figures_dir"])
    if "bib_path" in kwargs and kwargs["bib_path"] is not None:
        kwargs["bib_path"] = Path(kwargs["bib_path"])

    report = _audit_venue(Path(manuscript_path), venue=Venue(venue), **kwargs)
    return AuditWrapper(
        kind="venue",
        report_dict=report.to_dict(),
        markdown_repr=render_venue_audit_markdown(report),
    )


def audit_bias(
    figures_dir: Path | str = "panelforge_workspace/figures",
) -> AuditWrapper:
    """Run the E17 bias auditor inline in Jupyter.

    Parameters
    ----------
    figures_dir
        Directory of rendered figures + provenance sidecars.

    Returns
    -------
    AuditWrapper
        With ``kind="bias"``.
    """
    from panelforge_figures.manifest.bias_auditor import (
        audit_bias_across_directory,
        render_bias_audit_markdown,
    )

    report = audit_bias_across_directory(Path(figures_dir))
    return AuditWrapper(
        kind="bias",
        report_dict=report.to_dict(),
        markdown_repr=render_bias_audit_markdown(report),
    )


def lint_xrefs(
    manuscript_path: Path | str,
    *,
    figures_dir: Path | str = "panelforge_workspace/figures",
) -> AuditWrapper:
    """Run the E15 xref linter inline in Jupyter.

    Parameters
    ----------
    manuscript_path
        Path to the manuscript.
    figures_dir
        Directory of rendered figures (used to detect orphans / missing
        files).  When the directory does not exist, the linter operates
        on the manuscript alone.

    Returns
    -------
    AuditWrapper
        With ``kind="lint-xrefs"``.
    """
    from panelforge_figures.manifest.xref_linter import (
        lint_xrefs as _lint_xrefs,
    )
    from panelforge_figures.manifest.xref_linter import (
        render_lint_report_markdown,
    )

    fdir = Path(figures_dir)
    report = _lint_xrefs(
        Path(manuscript_path),
        figures_dir=fdir if fdir.exists() else None,
    )
    return AuditWrapper(
        kind="lint-xrefs",
        report_dict=report.to_dict(),
        markdown_repr=render_lint_report_markdown(report),
    )


def verify_claims(
    manuscript_path: Path | str,
    *,
    figures_dir: Path | str = "panelforge_workspace/figures",
    alpha: float = 0.05,
) -> AuditWrapper:
    """Run the claim-check pipeline inline in Jupyter.

    Parameters
    ----------
    manuscript_path
        Path to the manuscript.
    figures_dir
        Directory containing rendered figures + provenance sidecars.
    alpha
        Significance threshold for the statistical-evidence checks.

    Returns
    -------
    AuditWrapper
        With ``kind="verify-claims"``.
    """
    from panelforge_figures.manifest.claim_check import (
        render_markdown_report,
        verify_manuscript,
    )

    report = verify_manuscript(
        Path(manuscript_path),
        Path(figures_dir),
        alpha=alpha,
    )
    return AuditWrapper(
        kind="verify-claims",
        report_dict={
            "n_claims": report.n_claims,
            "n_supported": report.n_supported,
            "n_unsupported": report.n_unsupported,
            "n_unverifiable": report.n_unverifiable,
            "claims": [
                {
                    "figure_id": v.claim.figure_id,
                    "verdict": v.verdict.value,
                    "rationale": v.rationale,
                }
                for v in report.claims
            ],
        },
        markdown_repr=render_markdown_report(report),
    )
