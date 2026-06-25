"""Audit-driven caption drafts.

Emits markdown caption stubs per figure from:

* the recipe's contract metadata (title, response_label, family)
* the figure's audit_findings (p-values, effect sizes, n)
* the provenance figure_sha256 (so the rendered seed travels with its hash)
* optional style hints (nature / cell / nejm / lab-default / plain)

Pluggable LLM backend via :mod:`panelforge_figures.safety`'s
:func:`is_llm_allowed`; falls back to template-only when no API key
is present, when the LLM is blocked by the data-class policy, or when
the caller did not explicitly opt into LLM polish.

The output is a *stub the user edits*, NOT final text — an auditable
seed for the writing process that anchors prose to the same
provenance and audit data as the rendered figure.

Public API
----------

* :func:`draft_caption_template_only` — pure-Python template render,
  always offline, never raises (besides programming errors).
* :func:`draft_caption_from_provenance` — read a sidecar
  ``provenance.json`` and produce a draft from its embedded
  ``audit`` and ``recipe.contract`` blocks.
* :func:`render_caption_markdown` — turn a :class:`CaptionDraft` into
  a markdown string the user can paste into a manuscript.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "CaptionDraft",
    "CaptionError",
    "CaptionStyle",
    "draft_caption_from_provenance",
    "draft_caption_template_only",
    "render_caption_markdown",
]


class CaptionStyle(StrEnum):
    """Lab/journal style hints that drive the title-line formatter."""

    plain = "plain"
    nature = "nature"
    cell = "cell"
    nejm = "nejm"
    lab_default = "lab_default"


class CaptionError(RuntimeError):
    """Raised when no provenance, no audit, or LLM call fails."""


@dataclass(frozen=True)
class CaptionDraft:
    """Structured caption seed.

    Fields
    ------
    figure_id
        Stable identifier — typically the figure's filename stem
        (e.g. ``"panel_a"``, ``"figure_1"``). Captions are *rendered*
        from this id verbatim (it never participates in a cross-reference
        comparison here), so it is intentionally not run through
        :func:`._figure_id.normalise_figure_id`; the auditors that *match*
        ids (``xref_linter`` / ``claim_check``) use that canonical form.
    style
        Resolved :class:`CaptionStyle` used to render the title line.
    title_line
        Bold first line of the caption — different per style
        (Nature uses ``|`` separators, Cell uses ``.`` separators,
        NEJM uses an em-dash).
    body
        One to three short paragraphs of template-rendered prose.
    statistics_line
        Compact one-liner with F-stats / p-values / n synthesised from
        the audit ``terms`` block.
    figure_sha256
        Optional sha256 hex digest of the figure file the caption was
        drafted against; copied straight from the provenance sidecar.
    audit_summary
        Subset of the audit dict that the template actually consumed —
        useful for downstream tooling to verify what statistics were
        embedded into the prose.
    notes
        Caveats appended as HTML comments in the markdown render —
        e.g. ``"template-only — no LLM polish"`` or
        ``"LLM polish deferred to v2.6.0"``.
    """

    figure_id: str
    style: CaptionStyle
    title_line: str
    body: str
    statistics_line: str
    figure_sha256: str | None
    audit_summary: dict[str, Any]
    notes: tuple[str, ...] = ()


# ───────────────────────────── helpers ──────────────────────────────────


def _format_statistic_line(audit: dict[str, Any], family: str) -> str:
    """Compose a one-line statistic summary from audit findings.

    The audit pipeline (Sprint 1A — :mod:`statistical_audit`) emits a
    ``terms`` list per recipe that lists every coefficient or factor
    with its F-statistic, p-value, and degrees of freedom. We render
    a semicolon-joined string of those terms first; if the audit lacks
    a ``terms`` block but has a top-level p / F / n, we fall back to
    a single-line summary; otherwise we emit a documented "no summary"
    sentinel so reviewers know the caption is missing a stat line.
    """
    parts: list[str] = []
    for term in audit.get("terms", []) or []:
        f = term.get("f_stat")
        p = term.get("p_value")
        df_n = term.get("df_num")
        df_d = term.get("df_den")
        name = term.get("term", "")
        if f is not None and p is not None:
            df_part = f"({df_n},{df_d})" if (df_n and df_d) else ""
            label = f" ({name})" if name else ""
            parts.append(f"F{df_part} = {f:.3g}, p = {p:.3g}{label}")
    if parts:
        return "; ".join(parts)

    # Fallbacks for audit dicts that summarise rather than enumerate.
    p = audit.get("p_value")
    f = audit.get("f_stat")
    n = audit.get("n_per_group") or audit.get("n_per_cell")
    if f is not None and p is not None:
        n_part = f", n = {n}" if n is not None else ""
        return f"F = {f:.3g}, p = {p:.3g}{n_part}"
    if p is not None:
        n_part = f", n = {n}" if n is not None else ""
        return f"p = {p:.3g}{n_part}"
    return "no statistical summary in audit"


# Family-keyed prose templates. The placeholders are populated from
# the recipe's ``contract`` block; missing fields fall back to safe
# generic strings so the template never raises a KeyError.
_TEMPLATES_BY_FAMILY: dict[str, str] = {
    "coef_forest": (
        "{response_label} as a function of {factors}. "
        "Each marker reports the {effect_size_units} effect size with 95% CI; "
        "the dashed reference indicates the null. {statistics_line}. "
        "{n_summary}."
    ),
    "comparison": (
        "Comparison of {response_label} between groups. "
        "Center line: median. Whiskers: 95% CI. {statistics_line}. "
        "{n_summary}."
    ),
    "factorial": (
        "Two-way factorial of {factors} on {response_label}. "
        "{statistics_line}. {n_summary}."
    ),
    "correlation": (
        "Relationship between {x_label} and {response_label}. "
        "Solid line: linear regression. Shading: 95% CI. {statistics_line}. "
        "{n_summary}."
    ),
    "equivalence": (
        "Equivalence test for {response_label}. "
        "Bounds: ±{equivalence_margin} ({effect_size_units}). "
        "{statistics_line}. {n_summary}."
    ),
}

_DEFAULT_TEMPLATE = (
    "{response_label} ({family} family). "
    "{statistics_line}. {n_summary}."
)


def _style_title_line(style: CaptionStyle, figure_id: str, title: str) -> str:
    """Style the bold first line per house rules.

    * Nature uses ``Figure N | Title.`` with a vertical bar.
    * Cell uses ``Figure N. Title.`` with a period.
    * NEJM uses ``Figure N — Title`` with an em-dash, period outside.
    * lab_default and plain reuse the figure_id verbatim — the test
      suite distinguishes them in case a future revision diverges.
    """
    if style == CaptionStyle.nature:
        return f"**Figure {figure_id} | {title}.**"
    if style == CaptionStyle.cell:
        return f"**Figure {figure_id}. {title}.**"
    if style == CaptionStyle.nejm:
        return f"**Figure {figure_id} — {title}**."
    if style == CaptionStyle.lab_default:
        return f"**{figure_id}.** {title}."
    return f"**{figure_id}.** {title}."


def _factors_label(contract_dict: dict[str, Any]) -> str:
    """Compose the ``{factors}`` substitution string.

    Looks at four common contract keys (group_label_a/b, factor_a/b)
    and joins whichever are populated; falls back to ``"groups"``.
    """
    return (
        ", ".join(
            f
            for f in (
                contract_dict.get("group_label_a"),
                contract_dict.get("group_label_b"),
                contract_dict.get("factor_a"),
                contract_dict.get("factor_b"),
            )
            if f
        )
        or "groups"
    )


def _summarise_n(audit: dict[str, Any], n_per_group: int | None) -> str:
    """Pick the most specific n-summary the audit can support."""
    if audit.get("n_per_cell"):
        return f"n = {audit['n_per_cell']}/cell"
    if audit.get("n_per_group"):
        return f"n = {audit['n_per_group']}/group"
    if n_per_group is not None:
        return f"n = {n_per_group}/group"
    return "n: see methods"


# ───────────────────────────── public API ───────────────────────────────


def draft_caption_template_only(
    *,
    figure_id: str,
    contract_dict: dict[str, Any],
    audit: dict[str, Any],
    family: str,
    figure_sha256: str | None = None,
    style: CaptionStyle = CaptionStyle.plain,
    n_per_group: int | None = None,
) -> CaptionDraft:
    """Template-only caption draft — no LLM. Always fast, always offline.

    Parameters
    ----------
    figure_id
        Stable identifier for the figure (e.g. ``"panel_a"`` or the
        provenance ``figure_path`` stem).
    contract_dict
        The recipe's ``contract`` mapping. ``title``,
        ``response_label``, factors, and effect-size units are read
        from here.
    audit
        Audit findings dict, typically the ``audit`` block of a
        provenance sidecar.
    family
        Recipe family — keys :data:`_TEMPLATES_BY_FAMILY`.
    figure_sha256
        Optional sha256 of the rendered figure; surfaced as an HTML
        comment in the rendered markdown.
    style
        Style hint that drives :func:`_style_title_line`.
    n_per_group
        Caller-supplied fallback when the audit lacks an n summary.
    """
    title = contract_dict.get(
        "title",
        contract_dict.get("response_label", "Figure"),
    )
    response_label = contract_dict.get("response_label", "outcome")
    title_line = _style_title_line(style, figure_id, title)
    statistics_line = _format_statistic_line(audit, family)

    factors = _factors_label(contract_dict)
    n_summary = _summarise_n(audit, n_per_group)

    template = _TEMPLATES_BY_FAMILY.get(family, _DEFAULT_TEMPLATE)
    body = template.format(
        response_label=response_label,
        factors=factors,
        statistics_line=statistics_line,
        n_summary=n_summary,
        family=family,
        x_label=contract_dict.get("x_label", "x"),
        effect_size_units=contract_dict.get("effect_size_units", "standardized"),
        equivalence_margin=contract_dict.get("equivalence_margin", "δ"),
    ).strip()

    audit_summary = {
        k: audit[k]
        for k in ("p_value", "f_stat", "n_per_cell", "n_per_group", "terms")
        if k in audit
    }

    return CaptionDraft(
        figure_id=figure_id,
        style=style,
        title_line=title_line,
        body=body,
        statistics_line=statistics_line,
        figure_sha256=figure_sha256,
        audit_summary=audit_summary,
        notes=("template-only — no LLM polish",),
    )


def draft_caption_from_provenance(
    provenance_path: Path,
    *,
    style: CaptionStyle = CaptionStyle.plain,
    use_llm: bool = False,
) -> CaptionDraft:
    """Read provenance.json + audit_findings, draft a caption.

    Parameters
    ----------
    provenance_path
        Path to a sidecar ``*.provenance.json`` file produced by the
        v1.8.0 provenance chain.
    style
        Style hint per :class:`CaptionStyle`.
    use_llm
        Opt-in flag for LLM polish. Gated at runtime by
        :func:`panelforge_figures.safety.is_llm_allowed`. For v2.5.0
        we ship template-only output even when ``use_llm=True`` —
        the actual LLM call is deferred to v2.6.0 — but the call
        site is wired so the gate is exercised today.

    Raises
    ------
    CaptionError
        If the sidecar does not contain an ``audit`` block. Captions
        are explicitly an *audit-driven* artefact; without findings
        we refuse to silently emit prose without a stats line.
    """
    data = json.loads(Path(provenance_path).read_text(encoding="utf-8"))

    figure_path = Path(data.get("figure_path", "figure"))
    figure_id = figure_path.stem
    figure_sha256 = data.get("figure_sha256")
    audit = data.get("audit") or {}
    contract_dict = data.get("recipe", {}).get("contract", {}) or {}
    family = data.get("recipe", {}).get("family", "unknown")

    if not audit:
        raise CaptionError(
            f"provenance at {provenance_path} has no `audit` block; "
            "the figure was rendered without statistical_audit. "
            "Re-render with the audit pipeline enabled, or use "
            "`draft_caption_template_only` directly with an audit dict."
        )

    base_draft = draft_caption_template_only(
        figure_id=figure_id,
        contract_dict=contract_dict,
        audit=audit,
        family=family,
        figure_sha256=figure_sha256,
        style=style,
    )

    if not use_llm:
        return base_draft

    # use_llm=True: gate by the data-class policy first.
    from panelforge_figures.safety import is_llm_allowed

    if not is_llm_allowed():
        return CaptionDraft(
            figure_id=base_draft.figure_id,
            style=base_draft.style,
            title_line=base_draft.title_line,
            body=base_draft.body,
            statistics_line=base_draft.statistics_line,
            figure_sha256=base_draft.figure_sha256,
            audit_summary=base_draft.audit_summary,
            notes=base_draft.notes
            + (
                "LLM requested but blocked by data-class policy; template only",
            ),
        )

    # LLM allowed: in v2.5.0 we still emit template output but log
    # the deferred-capability marker so consumers know the request
    # was honoured policy-wise but not yet wired to a model call.
    return CaptionDraft(
        figure_id=base_draft.figure_id,
        style=base_draft.style,
        title_line=base_draft.title_line,
        body=base_draft.body,
        statistics_line=base_draft.statistics_line,
        figure_sha256=base_draft.figure_sha256,
        audit_summary=base_draft.audit_summary,
        notes=base_draft.notes + ("LLM polish deferred to v2.6.0",),
    )


def render_caption_markdown(draft: CaptionDraft) -> str:
    """Render a :class:`CaptionDraft` as Markdown for the user to edit.

    Layout:

    1. The bold ``title_line`` (style-specific).
    2. A blank line.
    3. The ``body`` paragraph(s).
    4. An HTML comment with the figure's sha256, if any.
    5. One HTML comment per note (e.g. template-only marker).
    """
    lines = [
        draft.title_line,
        "",
        draft.body,
    ]
    if draft.figure_sha256:
        lines.extend(
            [
                "",
                f"<!-- figure sha256: {draft.figure_sha256} -->",
            ]
        )
    for note in draft.notes:
        lines.append(f"<!-- caption note: {note} -->")
    return "\n".join(lines)
