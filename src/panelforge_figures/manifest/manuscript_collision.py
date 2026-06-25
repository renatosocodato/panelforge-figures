"""Manuscript collision and reconciliation (Elevation 10).

Given an :class:`ExistingManuscript` (emitted by ``manuscript_parser``) and a
proposed :class:`FigurePlan` (from :mod:`panelforge_figures.manifest.scout`),
this module:

1. Diffs figure references, defined figure blocks, and proposed panels —
   emitting a :class:`CollisionReport` describing what to keep, insert,
   append, or flag.
2. Reconciles the proposed Methods family list against the existing
   ``Methods`` section.
3. (Optionally) cross-checks parsed claims against per-figure audit
   findings using the same verdict logic as E2 ``claim_check.verify_claim``.
4. Applies *non-destructive* in-place updates under ``policy=update``:
   insertions are made at well-defined anchor points, existing prose is
   never modified.

The four supported policies are:

* ``detect``   — read-only; emit report.
* ``update``   — insert new blocks + Methods paragraphs in place.
* ``propose``  — write ``main.suggested.<ext>`` alongside; user diffs manually.
* ``preserve`` — emit a fresh ``main.fresh.<ext>``, ignoring existing prose.

Style: ``from __future__ import annotations``; ``StrEnum``; frozen dataclasses;
ruff clean; lazy-imports from :mod:`manuscript_scaffold` for Methods
paragraph rendering when available.

The module is intentionally tolerant of partial inputs: missing audit
findings yield ``unverifiable`` verdicts (never an exception); a
manuscript with no Methods section still receives a reasonable
insertion-point heuristic.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "ClaimVerdict",
    "CollisionError",
    "CollisionReport",
    "FigureReconciliation",
    "ManuscriptPolicy",
    "MethodsReconciliation",
    "ReconciliationAction",
    "apply_update_policy",
    "detect_collision",
    "render_collision_report_markdown",
    "save_collision_log",
]


# --------------------------------------------------------------------------- #
# Public enums and errors                                                     #
# --------------------------------------------------------------------------- #


class ManuscriptPolicy(StrEnum):
    """Policy controlling how :func:`apply_update_policy` mutates the file."""

    detect = "detect"            # read-only: emit report, do not write
    update = "update"            # insert new blocks + methods; never modify existing
    propose = "propose"          # emit main.suggested.tex alongside; user diffs manually
    preserve = "preserve"        # ignore existing; emit fresh main.fresh.tex


class ReconciliationAction(StrEnum):
    """Action assigned to each figure during collision detection."""

    keep_existing = "keep_existing"          # block defined, no action
    insert_block = "insert_block"            # referenced but not defined; insert
    append_new = "append_new"                # not in manuscript at all; append
    flag_orphan = "flag_orphan"              # defined but unreferenced; warn user
    flag_referenced_undefined = "flag_referenced_undefined"  # missing block


class ClaimVerdict(StrEnum):
    """Mirror of E2 verify-claims output."""

    supported = "supported"
    unsupported = "unsupported"
    unverifiable = "unverifiable"


class CollisionError(RuntimeError):
    """Raised on insertion failures or unrecognised manuscript structure."""


# --------------------------------------------------------------------------- #
# Public dataclasses                                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FigureReconciliation:
    """Reconciliation verdict for a single figure id."""

    figure_id: str                   # "Figure 1" / "fig:1"
    plan_figure_id: str | None       # figure_id in proposed FigurePlan (may differ)
    action: ReconciliationAction
    existing_block_lines: tuple[int, int] | None  # start/end line if existing
    insertion_point_line: int | None              # where to insert if action=insert_block
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "figure_id": self.figure_id,
            "plan_figure_id": self.plan_figure_id,
            "action": self.action.value,
            "existing_block_lines": list(self.existing_block_lines)
            if self.existing_block_lines
            else None,
            "insertion_point_line": self.insertion_point_line,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class MethodsReconciliation:
    """Reconciliation verdict for one recipe family in the Methods section."""

    recipe_full_name: str
    family: str
    already_documented: bool
    insertion_point_line: int | None  # in existing Methods section
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_full_name": self.recipe_full_name,
            "family": self.family,
            "already_documented": self.already_documented,
            "insertion_point_line": self.insertion_point_line,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class CollisionReport:
    """End-to-end collision diff between manuscript and plan."""

    manuscript_path: Path
    figure_reconciliations: tuple[FigureReconciliation, ...]
    methods_reconciliations: tuple[MethodsReconciliation, ...]
    # (sentence, verdict, rationale) — single tuple keeps the dataclass frozen.
    claim_verdicts: tuple[tuple[str, ClaimVerdict, str], ...]
    n_existing_figures: int
    n_new_figures: int
    n_orphan_refs: int                # referenced but undefined
    n_dangling_blocks: int            # defined but unreferenced
    summary: str                       # one-line human-readable verdict

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "manuscript_path": str(self.manuscript_path),
            "figure_reconciliations": [
                r.to_dict() for r in self.figure_reconciliations
            ],
            "methods_reconciliations": [
                m.to_dict() for m in self.methods_reconciliations
            ],
            "claim_verdicts": [
                {"sentence": s, "verdict": v.value, "rationale": r}
                for (s, v, r) in self.claim_verdicts
            ],
            "n_existing_figures": self.n_existing_figures,
            "n_new_figures": self.n_new_figures,
            "n_orphan_refs": self.n_orphan_refs,
            "n_dangling_blocks": self.n_dangling_blocks,
            "summary": self.summary,
        }


# --------------------------------------------------------------------------- #
# ExistingManuscript duck-typing helpers                                      #
# --------------------------------------------------------------------------- #
#
# Build-A's parser emits an ExistingManuscript object. To keep this module
# decoupled (and unit-testable with mocks), we access everything via attribute
# lookups with safe defaults — no direct import of the parser's class.


def _get(obj: Any, name: str, default: Any = None) -> Any:
    """Attribute-or-key lookup with a default. Tolerates dict-like mocks."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _manuscript_path(existing: Any) -> Path:
    p = _get(existing, "path")
    if p is None:
        return Path("manuscript.tex")
    return Path(p)


def _manuscript_format(existing: Any) -> str:
    """Returns "latex" or "markdown" (defaults to "latex")."""
    fmt = _get(existing, "format")
    if fmt is None:
        # Fall back to extension sniffing.
        p = _manuscript_path(existing)
        ext = p.suffix.lower()
        if ext in {".md", ".markdown"}:
            return "markdown"
        return "latex"
    return str(fmt).lower()


def _manuscript_text(existing: Any) -> str:
    text = _get(existing, "text")
    if text is not None:
        return str(text)
    lines = _get(existing, "lines")
    if lines is not None:
        return "\n".join(str(line) for line in lines)
    return ""


def _manuscript_lines(existing: Any) -> list[str]:
    lines = _get(existing, "lines")
    if lines is not None:
        return [str(line) for line in lines]
    text = _manuscript_text(existing)
    return text.splitlines()


def _figure_blocks(existing: Any) -> list[Any]:
    blocks = _get(existing, "figure_blocks") or _get(existing, "blocks") or ()
    return list(blocks)


def _figure_refs(existing: Any) -> list[Any]:
    refs = _get(existing, "figure_refs") or _get(existing, "refs") or ()
    return list(refs)


def _claims(existing: Any) -> list[Any]:
    claims = _get(existing, "claims") or ()
    return list(claims)


def _block_figure_id(block: Any) -> str:
    """Canonical figure id for a defined block — accepts a few attribute names."""
    for attr in ("figure_id", "label", "name", "id"):
        val = _get(block, attr)
        if val:
            return str(val).strip()
    return ""


def _block_line_range(block: Any) -> tuple[int, int] | None:
    """Return ``(start, end)`` line numbers if available."""
    start = _get(block, "start_line") or _get(block, "begin_line") or _get(block, "line_start")
    end = _get(block, "end_line") or _get(block, "line_end")
    if start is None and end is None:
        line = _get(block, "line")
        if line is None:
            return None
            # Single-line block — collapse to (line, line).
        return (int(line), int(line))
    if start is None:
        start = end
    if end is None:
        end = start
    return (int(start), int(end))


def _ref_figure_id(ref: Any) -> str:
    for attr in ("figure_id", "label", "name", "id"):
        val = _get(ref, attr)
        if val:
            return str(val).strip()
    return ""


def _ref_line(ref: Any) -> int | None:
    line = _get(ref, "line") or _get(ref, "line_number") or _get(ref, "lineno")
    return int(line) if line is not None else None


# --------------------------------------------------------------------------- #
# Figure id normalisation                                                     #
# --------------------------------------------------------------------------- #


def _norm_figure_id(figure_id: str) -> str:
    """Canonicalise a figure id for matching.

    ``"Figure 1"`` ↔ ``"figure 1"`` ↔ ``"fig:1"`` ↔ ``"FIG 1"`` all collapse
    to ``"figure 1"``. Trailing subletters (``"figure 3a"``) are preserved.
    """
    if not figure_id:
        return ""
    raw = figure_id.strip().lower()
    # ``fig:1`` → ``figure 1``
    if raw.startswith("fig:"):
        raw = "figure " + raw[len("fig:"):]
    # ``fig 1`` / ``fig.1`` → ``figure 1``
    if raw.startswith("fig") and not raw.startswith("figure"):
        # ``fig.1`` / ``fig 1``
        tail = raw[3:].lstrip(" .:")
        raw = "figure " + tail
    # Collapse internal whitespace.
    return " ".join(raw.split())


# --------------------------------------------------------------------------- #
# Figure matching                                                             #
# --------------------------------------------------------------------------- #


def _index_existing_figures(
    existing: Any,
) -> tuple[dict[str, Any], dict[str, list[int]]]:
    """Index existing blocks and ref lines by normalised figure id.

    Returns
    -------
    (block_by_id, ref_lines_by_id)
        block_by_id maps norm_id → the figure block object.
        ref_lines_by_id maps norm_id → sorted list of line numbers.
    """
    blocks_by_id: dict[str, Any] = {}
    for block in _figure_blocks(existing):
        fid = _block_figure_id(block)
        norm = _norm_figure_id(fid)
        if norm and norm not in blocks_by_id:
            blocks_by_id[norm] = block

    refs_by_id: dict[str, list[int]] = {}
    for ref in _figure_refs(existing):
        fid = _ref_figure_id(ref)
        norm = _norm_figure_id(fid)
        if not norm:
            continue
        line = _ref_line(ref)
        if line is not None:
            refs_by_id.setdefault(norm, []).append(line)

    # Stable per-id ordering.
    for norm in refs_by_id:
        refs_by_id[norm].sort()
    return blocks_by_id, refs_by_id


def _plan_figure_ids(plan: Any) -> list[str]:
    """Ordered list of figure ids in the plan."""
    figs = _get(plan, "figures") or ()
    return [str(_get(f, "figure_id", "")) for f in figs]


def _match_plan_to_existing(
    plan_ids: list[str],
    existing_ids: set[str],
) -> dict[str, str | None]:
    """Map each plan figure id → matched existing-normalised id, or None.

    Match strategy (in order):
    1. Exact norm-id match.
    2. Index-based fallback: plan's i-th figure ↔ existing's i-th figure
       (only when no exact match was found for that slot AND counts align
       loosely).

    Returns ``{plan_id: existing_norm_id_or_None}`` in plan order.
    """
    matches: dict[str, str | None] = {}
    consumed_existing: set[str] = set()
    sorted_existing = sorted(existing_ids)

    # Pass 1: exact norm match.
    for pid in plan_ids:
        norm = _norm_figure_id(pid)
        if norm and norm in existing_ids:
            matches[pid] = norm
            consumed_existing.add(norm)
        else:
            matches[pid] = None

    # Pass 2: index-based fallback for un-matched plan ids.
    # Walk plan ids in order; for each None, take the next unused existing id.
    remaining_existing = [eid for eid in sorted_existing if eid not in consumed_existing]
    cursor = 0
    for pid in plan_ids:
        if matches[pid] is not None:
            continue
        if cursor >= len(remaining_existing):
            break
        # Only fall back when the plan id parses as a generic "figure N" so we
        # do not silently re-bind a named figure to an unrelated one.
        norm = _norm_figure_id(pid)
        if norm.startswith("figure ") and norm == _norm_figure_id(pid):
            matches[pid] = remaining_existing[cursor]
            consumed_existing.add(remaining_existing[cursor])
            cursor += 1
    return matches


# --------------------------------------------------------------------------- #
# Insertion-point heuristics                                                  #
# --------------------------------------------------------------------------- #


def _find_results_end_line(existing: Any) -> int:
    """Line just before ``\\section{Methods}`` / ``# Methods`` (1-indexed).

    Falls back to the end of file if no Methods header is found. Used as
    the append-anchor for brand-new figures.
    """
    # Prefer parser-provided section info if available.
    results = _get(existing, "results_section")
    if results is not None:
        end = _get(results, "end_line") or _get(results, "line_end")
        if end is not None:
            return int(end)

    methods = _get(existing, "methods_section")
    if methods is not None:
        start = _get(methods, "start_line") or _get(methods, "begin_line") or _get(methods, "line_start")
        if start is not None:
            return max(int(start) - 1, 1)

    # Heuristic scan.
    lines = _manuscript_lines(existing)
    fmt = _manuscript_format(existing)
    for i, line in enumerate(lines, start=1):
        if _is_methods_header(line, fmt):
            return max(i - 1, 1)
    return len(lines)


def _find_methods_insertion_line(existing: Any) -> int | None:
    """Line where new Methods paragraphs should be inserted.

    Preference order:
    1. Just before ``\\subsection{Code and data availability}`` (or markdown
       equivalent) inside the Methods section.
    2. End of the Methods section.
    3. Just before ``\\section{Discussion}``.
    4. End of file.

    Returns ``None`` only when the file is empty.
    """
    fmt = _manuscript_format(existing)
    lines = _manuscript_lines(existing)
    if not lines:
        return None

    methods = _get(existing, "methods_section")
    methods_start = _get(methods, "start_line") if methods is not None else None
    methods_end = _get(methods, "end_line") if methods is not None else None

    if methods_start is None or methods_end is None:
        # Heuristic scan.
        m_s, m_e = _scan_methods_bounds(lines, fmt)
        methods_start = methods_start or m_s
        methods_end = methods_end or m_e

    # 1: search for "Code and data availability" inside Methods.
    if methods_start is not None and methods_end is not None:
        for i in range(int(methods_start), min(int(methods_end), len(lines)) + 1):
            line = lines[i - 1] if i - 1 < len(lines) else ""
            if _is_code_and_data_subheader(line, fmt):
                return max(i - 1, 1)
        # 2: end of methods.
        return int(methods_end)

    # 3: just before Discussion.
    for i, line in enumerate(lines, start=1):
        if _is_discussion_header(line, fmt):
            return max(i - 1, 1)

    # 4: end of file.
    return len(lines)


def _scan_methods_bounds(
    lines: list[str], fmt: str
) -> tuple[int | None, int | None]:
    """Locate the Methods section's (start, end) line numbers by header scan."""
    start: int | None = None
    end: int | None = None
    for i, line in enumerate(lines, start=1):
        if start is None and _is_methods_header(line, fmt):
            start = i
            continue
        if start is not None and end is None and _is_next_section_header(line, fmt):
            end = i - 1
            break
    if start is not None and end is None:
        end = len(lines)
    return start, end


def _is_methods_header(line: str, fmt: str) -> bool:
    s = line.strip()
    if fmt == "latex":
        low = s.lower()
        return (
            low.startswith("\\section{methods}")
            or low.startswith("\\section*{methods}")
            or low.startswith("\\section{materials and methods}")
            or low.startswith("\\section*{materials and methods}")
        )
    # markdown
    low = s.lower()
    return (
        low.startswith("# methods")
        or low.startswith("## methods")
        or low.startswith("# materials and methods")
        or low.startswith("## materials and methods")
    )


def _is_discussion_header(line: str, fmt: str) -> bool:
    s = line.strip().lower()
    if fmt == "latex":
        return s.startswith("\\section{discussion}") or s.startswith("\\section*{discussion}")
    return s.startswith("# discussion") or s.startswith("## discussion")


def _is_next_section_header(line: str, fmt: str) -> bool:
    """True when ``line`` begins a section that isn't ``Methods``."""
    s = line.strip()
    if not s:
        return False
    if fmt == "latex":
        low = s.lower()
        if low.startswith("\\section{") or low.startswith("\\section*{"):
            return not (low.startswith("\\section{methods}")
                        or low.startswith("\\section*{methods}")
                        or low.startswith("\\section{materials and methods}")
                        or low.startswith("\\section*{materials and methods}"))
        return False
    # markdown — H1 or H2 not labelled Methods.
    if s.startswith("# ") or s.startswith("## "):
        low = s.lower()
        return not (low.startswith("# methods")
                    or low.startswith("## methods")
                    or low.startswith("# materials and methods")
                    or low.startswith("## materials and methods"))
    return False


def _is_code_and_data_subheader(line: str, fmt: str) -> bool:
    s = line.strip().lower()
    if fmt == "latex":
        return (
            "\\subsection{code and data availability}" in s
            or "\\subsection*{code and data availability}" in s
            or "\\subsection{data and code availability}" in s
            or "\\subsection*{data and code availability}" in s
        )
    return s.startswith("### code and data availability") or s.startswith(
        "### data and code availability"
    )


# --------------------------------------------------------------------------- #
# Methods reconciliation                                                      #
# --------------------------------------------------------------------------- #


def _methods_text(existing: Any) -> str:
    """Return the body text of the Methods section (lowercased) for substring search."""
    methods = _get(existing, "methods_section")
    if methods is not None:
        body = _get(methods, "text") or _get(methods, "body")
        if body:
            return str(body).lower()

    fmt = _manuscript_format(existing)
    lines = _manuscript_lines(existing)
    start, end = _scan_methods_bounds(lines, fmt)
    if start is None:
        return ""
    end = end or len(lines)
    return "\n".join(lines[start - 1: end]).lower()


def _families_in_plan(plan: Any, recipes_metadata: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Walk plan panels; return ordered (recipe_full_name, family) pairs.

    De-duplicated by family — the first recipe encountered per family wins.
    ``recipes_metadata`` is consulted for the family enum value if available;
    otherwise we infer a coarse family from the recipe's modality prefix.
    """
    figs = _get(plan, "figures") or ()
    seen_family: dict[str, str] = {}  # family → recipe_full_name (first wins)
    order: list[str] = []
    for fig in figs:
        for panel in _get(fig, "panels") or ():
            recipe_full_name = str(_get(panel, "recipe_full_name", "")).strip()
            if not recipe_full_name:
                continue
            family = _resolve_family(recipe_full_name, recipes_metadata)
            if family and family not in seen_family:
                seen_family[family] = recipe_full_name
                order.append(family)
    return [(seen_family[fam], fam) for fam in order]


def _resolve_family(recipe_full_name: str, recipes_metadata: dict[str, Any] | None) -> str:
    """Resolve a recipe family from metadata; coarse fallback otherwise."""
    if recipes_metadata is not None:
        meta = recipes_metadata.get(recipe_full_name)
        if meta is not None:
            family = _get(meta, "family")
            if family is not None:
                val = getattr(family, "value", None)
                if val is not None:
                    return str(val)
                return str(family)

    # Fallback: take token after dot, drop trailing ``_*`` (e.g.
    # ``proteomics.coef_forest_volcano`` → ``coef_forest_volcano``).
    if "." in recipe_full_name:
        return recipe_full_name.split(".", 1)[1]
    return recipe_full_name or "unknown"


# --------------------------------------------------------------------------- #
# Claim verification                                                          #
# --------------------------------------------------------------------------- #


def _verify_one_claim(
    claim: Any,
    findings: dict[str, Any] | None,
    *,
    alpha: float = 0.05,
    correlation_threshold: float = 0.3,
) -> tuple[ClaimVerdict, str]:
    """Mirror of ``claim_check.verify_claim``, restricted to dict-shape findings.

    ``correlation_threshold`` defaults to 0.3 to match
    ``claim_check.verify_claim`` (Cohen's "moderate" floor, ~9% of
    variance); the two must stay in sync.

    Returns ``(verdict, rationale)``. Unknown / missing inputs → unverifiable.
    """
    if findings is None or not isinstance(findings, dict):
        return ClaimVerdict.unverifiable, "no audit findings available for figure"

    assertion = str(_get(claim, "assertion", "") or "").lower()

    p = _extract_p_value(findings)
    r = _extract_correlation(findings)

    if assertion in {"significant_difference", "significant", "diff_significant"}:
        if p is None:
            return ClaimVerdict.unverifiable, "audit findings have no p_value field"
        if p < alpha:
            return ClaimVerdict.supported, f"audit p_value={p:.4g} < alpha={alpha}"
        return ClaimVerdict.unsupported, f"audit p_value={p:.4g} >= alpha={alpha}"

    if assertion in {"no_difference", "null_result"}:
        if p is None:
            return ClaimVerdict.unverifiable, "audit findings have no p_value field"
        if p >= alpha:
            return ClaimVerdict.supported, f"audit p_value={p:.4g} >= alpha={alpha}"
        return ClaimVerdict.unsupported, f"audit p_value={p:.4g} < alpha={alpha} contradicts null"

    if assertion in {"correlation_present", "correlation", "correlated"}:
        if r is None:
            return ClaimVerdict.unverifiable, "audit findings have no correlation field"
        if abs(r) >= correlation_threshold:
            return ClaimVerdict.supported, f"|r|={abs(r):.3g} >= {correlation_threshold}"
        return ClaimVerdict.unsupported, f"|r|={abs(r):.3g} < {correlation_threshold}"

    if assertion in {"no_correlation", "uncorrelated"}:
        if r is None:
            return ClaimVerdict.unverifiable, "audit findings have no correlation field"
        if abs(r) < correlation_threshold:
            return ClaimVerdict.supported, f"|r|={abs(r):.3g} < {correlation_threshold}"
        return ClaimVerdict.unsupported, f"|r|={abs(r):.3g} >= {correlation_threshold}"

    return ClaimVerdict.unverifiable, f"assertion '{assertion}' not auto-checkable"


def _extract_p_value(findings: dict[str, Any]) -> float | None:
    for key in ("p_value", "p", "pvalue", "p_val"):
        v = findings.get(key)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _extract_correlation(findings: dict[str, Any]) -> float | None:
    for key in ("correlation_coefficient", "pearson_r", "spearman_r", "r"):
        v = findings.get(key)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


# --------------------------------------------------------------------------- #
# detect_collision                                                            #
# --------------------------------------------------------------------------- #


def detect_collision(
    existing: Any,
    plan: Any,
    *,
    audit_findings_per_figure: dict[str, dict[str, Any]] | None = None,
    recipes_metadata: dict[str, Any] | None = None,
) -> CollisionReport:
    """Compare an ``ExistingManuscript`` against a proposed :class:`FigurePlan`.

    Parameters
    ----------
    existing
        Parsed manuscript from ``manuscript_parser`` (duck-typed; any object
        exposing ``path``, ``format``, ``text`` / ``lines``, ``figure_blocks``,
        ``figure_refs``, ``methods_section``, ``claims`` works).
    plan
        :class:`panelforge_figures.manifest.scout.FigurePlan` (or equivalent).
    audit_findings_per_figure
        Optional mapping ``figure_id -> audit_findings_dict``. When ``None``
        every claim verdict is :attr:`ClaimVerdict.unverifiable`.
    recipes_metadata
        Optional ``recipe_full_name -> RecipeMetadata`` mapping used to
        resolve families when reconciling Methods paragraphs.
    """
    plan_ids = _plan_figure_ids(plan)
    blocks_by_id, refs_by_id = _index_existing_figures(existing)
    existing_ids = set(blocks_by_id) | set(refs_by_id)

    matches = _match_plan_to_existing(plan_ids, existing_ids)

    # ---- Per-figure reconciliation ---- #
    used_existing: set[str] = set()
    figure_recs: list[FigureReconciliation] = []
    append_anchor = _find_results_end_line(existing)

    for pid in plan_ids:
        norm_existing = matches.get(pid)
        if norm_existing is not None:
            used_existing.add(norm_existing)
            block = blocks_by_id.get(norm_existing)
            if block is not None:
                lines = _block_line_range(block)
                figure_recs.append(
                    FigureReconciliation(
                        figure_id=norm_existing,
                        plan_figure_id=pid,
                        action=ReconciliationAction.keep_existing,
                        existing_block_lines=lines,
                        insertion_point_line=None,
                        rationale="figure already defined in manuscript",
                    )
                )
            else:
                # Referenced but no block — insert at first ref line.
                ref_lines = refs_by_id.get(norm_existing) or []
                anchor = ref_lines[0] if ref_lines else append_anchor
                figure_recs.append(
                    FigureReconciliation(
                        figure_id=norm_existing,
                        plan_figure_id=pid,
                        action=ReconciliationAction.insert_block,
                        existing_block_lines=None,
                        insertion_point_line=anchor,
                        rationale=(
                            f"figure referenced (line {anchor}) but no block defined; "
                            "will insert at first reference"
                        ),
                    )
                )
        else:
            # New figure: append at end of Results.
            figure_recs.append(
                FigureReconciliation(
                    figure_id=pid,
                    plan_figure_id=pid,
                    action=ReconciliationAction.append_new,
                    existing_block_lines=None,
                    insertion_point_line=append_anchor,
                    rationale=(
                        f"figure absent from manuscript; will append at end of Results "
                        f"(line {append_anchor})"
                    ),
                )
            )

    # ---- Dangling + orphan flags ---- #
    n_orphan_refs = 0
    n_dangling_blocks = 0
    for norm_id in sorted(existing_ids - used_existing):
        block = blocks_by_id.get(norm_id)
        ref_lines = refs_by_id.get(norm_id) or []
        if block is not None and not ref_lines:
            n_dangling_blocks += 1
            lines = _block_line_range(block)
            figure_recs.append(
                FigureReconciliation(
                    figure_id=norm_id,
                    plan_figure_id=None,
                    action=ReconciliationAction.flag_orphan,
                    existing_block_lines=lines,
                    insertion_point_line=None,
                    rationale="figure block defined but never referenced",
                )
            )
        elif block is None and ref_lines:
            n_orphan_refs += 1
            figure_recs.append(
                FigureReconciliation(
                    figure_id=norm_id,
                    plan_figure_id=None,
                    action=ReconciliationAction.flag_referenced_undefined,
                    existing_block_lines=None,
                    insertion_point_line=ref_lines[0],
                    rationale=(
                        f"figure referenced (line {ref_lines[0]}) but no block defined "
                        "and no plan match — user must add or remove the reference"
                    ),
                )
            )

    # ---- Methods reconciliation ---- #
    methods_recs: list[MethodsReconciliation] = []
    methods_body_lower = _methods_text(existing)
    methods_anchor = _find_methods_insertion_line(existing)

    for recipe_full_name, family in _families_in_plan(plan, recipes_metadata):
        documented = bool(family) and family.lower() in methods_body_lower
        methods_recs.append(
            MethodsReconciliation(
                recipe_full_name=recipe_full_name,
                family=family,
                already_documented=documented,
                insertion_point_line=None if documented else methods_anchor,
                rationale=(
                    f"family '{family}' already mentioned in Methods"
                    if documented
                    else f"family '{family}' absent from Methods; will append paragraph"
                ),
            )
        )

    # ---- Claim verdicts ---- #
    claim_verdicts: list[tuple[str, ClaimVerdict, str]] = []
    for claim in _claims(existing):
        sentence = str(_get(claim, "sentence", "") or "")
        if not sentence:
            continue
        fig_id = str(_get(claim, "figure_id", "") or "")
        findings = None
        if audit_findings_per_figure is not None:
            # Try direct lookup, then normalised lookup.
            findings = audit_findings_per_figure.get(fig_id)
            if findings is None:
                findings = audit_findings_per_figure.get(_norm_figure_id(fig_id))
        verdict, rationale = _verify_one_claim(claim, findings)
        claim_verdicts.append((sentence, verdict, rationale))

    # ---- Summary ---- #
    n_existing_figures = len(blocks_by_id)
    n_new_figures = sum(1 for r in figure_recs if r.action == ReconciliationAction.append_new)
    n_keep = sum(1 for r in figure_recs if r.action == ReconciliationAction.keep_existing)
    n_insert = sum(1 for r in figure_recs if r.action == ReconciliationAction.insert_block)
    n_methods_new = sum(1 for m in methods_recs if not m.already_documented)
    n_unsupported = sum(1 for (_, v, _) in claim_verdicts if v == ClaimVerdict.unsupported)

    summary = (
        f"{len(plan_ids)} figures: {n_keep} keep / {n_insert} insert / "
        f"{n_new_figures} append; {n_methods_new} methods new"
    )
    if n_unsupported:
        summary += f"; {n_unsupported} unsupported claim"
        if n_unsupported != 1:
            summary += "s"
        summary += " (warn)"
    if n_orphan_refs:
        summary += f"; {n_orphan_refs} dangling ref"
        if n_orphan_refs != 1:
            summary += "s"
    if n_dangling_blocks:
        summary += f"; {n_dangling_blocks} orphan block"
        if n_dangling_blocks != 1:
            summary += "s"

    return CollisionReport(
        manuscript_path=_manuscript_path(existing),
        figure_reconciliations=tuple(figure_recs),
        methods_reconciliations=tuple(methods_recs),
        claim_verdicts=tuple(claim_verdicts),
        n_existing_figures=n_existing_figures,
        n_new_figures=n_new_figures,
        n_orphan_refs=n_orphan_refs,
        n_dangling_blocks=n_dangling_blocks,
        summary=summary,
    )


# --------------------------------------------------------------------------- #
# Figure-block rendering                                                      #
# --------------------------------------------------------------------------- #


def _render_figure_block_latex(figure_id: str, panels: list[Any]) -> str:
    """Render a LaTeX figure environment for the given panels."""
    norm = _norm_figure_id(figure_id)
    label = norm.replace(" ", "")  # "figure1"
    # Use the first panel's id as the file stem so the path matches E5 output.
    stem = label
    if panels:
        first_panel_id = str(_get(panels[0], "panel_id", "") or "")
        if first_panel_id:
            stem = label  # Keep figure-level stem; panels share one composed file.
    return (
        "\\begin{figure}[htbp]\n"
        "\\centering\n"
        f"\\includegraphics[width=\\textwidth]{{panelforge_workspace/figures/{stem}.pdf}}\n"
        "\\caption{TODO — caption (auto-drafted from audit findings; user edits voice).}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}\n"
    )


def _render_figure_block_markdown(figure_id: str, panels: list[Any]) -> str:
    """Render a Markdown figure block for the given panels."""
    norm = _norm_figure_id(figure_id)
    stem = norm.replace(" ", "")
    display = figure_id.strip() or norm.title()
    return (
        f"![{stem}](panelforge_workspace/figures/{stem}.png)\n"
        f"**{display}.** TODO — caption.\n"
    )


def _panels_for_plan_figure(plan: Any, plan_figure_id: str) -> list[Any]:
    figs = _get(plan, "figures") or ()
    for fig in figs:
        if str(_get(fig, "figure_id", "")) == plan_figure_id:
            return list(_get(fig, "panels") or ())
    return []


def _render_methods_paragraph(
    recipe_full_name: str,
    family: str,
    recipes_metadata: dict[str, Any] | None,
    n_panels: int = 1,
) -> str:
    """Lazy-import :mod:`manuscript_scaffold` for the canonical renderer.

    Falls back to an inline 2-sentence template when the helper is
    unavailable or the recipe has no statistical_contract.
    """
    contract: dict[str, Any] = {}
    if recipes_metadata is not None:
        meta = recipes_metadata.get(recipe_full_name)
        if meta is not None:
            try:
                from . import manuscript_scaffold as _ms  # noqa: PLC0415

                contract = _ms._contract_dict_from_recipe_meta(meta)
                if contract:
                    return _ms._render_one_methods_paragraph(family, contract, n_panels)
            except Exception:  # pragma: no cover - defensive fallback
                contract = {}

    plural = "panel" if n_panels == 1 else "panels"
    return (
        f"Statistical analyses for {family} family panels followed the "
        f"recipe-declared contract for {recipe_full_name}. "
        f"(Applied to {n_panels} {family} {plural}.)"
    )


# --------------------------------------------------------------------------- #
# apply_update_policy                                                         #
# --------------------------------------------------------------------------- #


def apply_update_policy(
    existing: Any,
    plan: Any,
    report: CollisionReport,
    *,
    policy: ManuscriptPolicy = ManuscriptPolicy.update,
    dry_run: bool = False,
    recipes_metadata: dict[str, Any] | None = None,
) -> tuple[Path | None, str]:
    """Apply non-destructive insertions per ``report`` and ``policy``.

    Only the actions ``insert_block`` and ``append_new`` produce figure-block
    insertions; ``flag_*`` actions are reported and left to the user.
    Existing prose is **never** modified.

    Returns
    -------
    (output_path, modified_text)
        ``output_path`` is ``None`` when ``dry_run`` is True.
    """
    src_path = _manuscript_path(existing)
    fmt = _manuscript_format(existing)
    text = _manuscript_text(existing)
    lines = text.splitlines()

    if policy is ManuscriptPolicy.detect:
        # Read-only.
        return (None, text)

    if policy is ManuscriptPolicy.preserve:
        fresh = _render_fresh_manuscript(plan, fmt)
        out = src_path.with_suffix(".fresh" + src_path.suffix) if src_path.suffix else src_path.with_name(src_path.name + ".fresh")
        if not dry_run:
            _safe_write(out, fresh)
        return (None if dry_run else out, fresh)

    # ---- Build the insertion list (line, text) ---- #
    insertions: list[tuple[int, str]] = []

    for rec in report.figure_reconciliations:
        if rec.action not in {
            ReconciliationAction.insert_block,
            ReconciliationAction.append_new,
        }:
            continue
        if rec.insertion_point_line is None:
            continue
        plan_fid = rec.plan_figure_id or rec.figure_id
        panels = _panels_for_plan_figure(plan, plan_fid)
        if fmt == "latex":
            block = _render_figure_block_latex(rec.figure_id, panels)
        else:
            block = _render_figure_block_markdown(rec.figure_id, panels)
        insertions.append((rec.insertion_point_line, block))

    for mrec in report.methods_reconciliations:
        if mrec.already_documented:
            continue
        if mrec.insertion_point_line is None:
            continue
        paragraph = _render_methods_paragraph(
            mrec.recipe_full_name, mrec.family, recipes_metadata
        )
        # Wrap as a LaTeX subsection or markdown subheading for clarity.
        if fmt == "latex":
            block = (
                f"\\subsection*{{Methods — {mrec.family}}}\n"
                f"{paragraph}\n"
            )
        else:
            block = f"### Methods — {mrec.family}\n\n{paragraph}\n"
        insertions.append((mrec.insertion_point_line, block))

    # ---- Apply insertions in ascending line order with offset tracking ---- #
    insertions.sort(key=lambda kv: kv[0])
    new_lines: list[str] = list(lines)
    log_entries: list[tuple[int, str]] = []
    offset = 0
    for line_no, block in insertions:
        # ``line_no`` is 1-indexed; we insert *after* that line.
        target = min(line_no + offset, len(new_lines))
        block_lines = block.split("\n")
        # Strip a trailing empty line introduced by trailing "\n" in our templates.
        if block_lines and block_lines[-1] == "":
            block_lines = block_lines[:-1]
        # Bookend with a blank line so neighbouring prose stays paragraph-broken.
        bookended = [""] + block_lines + [""]
        new_lines[target:target] = bookended
        offset += len(bookended)
        # Log first content line of the inserted block.
        excerpt_line = next((bl for bl in block_lines if bl.strip()), block_lines[0] if block_lines else "")
        log_entries.append((line_no, excerpt_line[:120]))

    modified_text = "\n".join(new_lines)
    if text.endswith("\n") and not modified_text.endswith("\n"):
        modified_text += "\n"

    if dry_run:
        return (None, modified_text)

    # ---- Decide output path per policy ---- #
    if policy is ManuscriptPolicy.update:
        out_path = src_path
    elif policy is ManuscriptPolicy.propose:
        out_path = (
            src_path.with_suffix(".suggested" + src_path.suffix)
            if src_path.suffix
            else src_path.with_name(src_path.name + ".suggested")
        )
    else:  # pragma: no cover - exhaustive guard
        raise CollisionError(f"unsupported policy: {policy!r}")

    _safe_write(out_path, modified_text)

    # ---- Emit collision log alongside the workspace ---- #
    try:
        ws_root = _infer_workspace_root(plan, src_path)
        log_path = ws_root / "panelforge_workspace" / "manuscript_collision_log.md"
        save_collision_log(log_entries, log_path)
    except Exception:  # pragma: no cover - log emission is best-effort
        pass

    return (out_path, modified_text)


def _safe_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _infer_workspace_root(plan: Any, fallback: Path) -> Path:
    root = _get(plan, "project_root")
    if root:
        return Path(root)
    return fallback.parent


def _render_fresh_manuscript(plan: Any, fmt: str) -> str:
    """Render a brand-new manuscript skeleton for ``policy=preserve``.

    This is intentionally minimal — the caller (Build-C's CLI) should
    delegate to :mod:`manuscript_scaffold` for full scaffolding when
    available. We render a basic shell so the file exists and can be
    distinguished from the original.
    """
    figs = _get(plan, "figures") or ()
    if fmt == "latex":
        body = [
            "% Auto-generated by panelforge-figures (policy=preserve).",
            "% Edit freely; the original manuscript was left untouched.",
            "\\documentclass{article}",
            "\\usepackage{graphicx}",
            "\\begin{document}",
            "",
            "\\section{Results}",
        ]
        for fig in figs:
            fid = str(_get(fig, "figure_id", ""))
            body.append(_render_figure_block_latex(fid, list(_get(fig, "panels") or ())))
            body.append("")
        body.append("\\section{Methods}")
        body.append("")
        body.append("\\section{Discussion}")
        body.append("")
        body.append("\\end{document}")
        return "\n".join(body) + "\n"
    # markdown
    body = [
        "<!-- Auto-generated by panelforge-figures (policy=preserve). -->",
        "",
        "# Results",
        "",
    ]
    for fig in figs:
        fid = str(_get(fig, "figure_id", ""))
        body.append(_render_figure_block_markdown(fid, list(_get(fig, "panels") or ())))
        body.append("")
    body.extend(["# Methods", "", "# Discussion", ""])
    return "\n".join(body) + "\n"


# --------------------------------------------------------------------------- #
# render_collision_report_markdown                                            #
# --------------------------------------------------------------------------- #


def render_collision_report_markdown(report: CollisionReport) -> str:
    """Render a human-readable markdown report for the CLI verb."""
    lines: list[str] = []
    lines.append("# Manuscript Collision Report")
    lines.append("")
    lines.append(f"**Manuscript**: {report.manuscript_path}")
    lines.append(f"**Summary**: {report.summary}")
    lines.append("")

    # Per-figure table.
    lines.append("## Per-figure reconciliation")
    lines.append("")
    lines.append("| Figure | Existing | Plan | Action |")
    lines.append("| --- | --- | --- | --- |")
    for rec in report.figure_reconciliations:
        if rec.existing_block_lines:
            existing_col = f"defined (lines {rec.existing_block_lines[0]}-{rec.existing_block_lines[1]})"
        elif rec.action == ReconciliationAction.insert_block:
            existing_col = f"referenced only (line {rec.insertion_point_line})"
        elif rec.action == ReconciliationAction.flag_referenced_undefined:
            existing_col = f"referenced only (line {rec.insertion_point_line})"
        else:
            existing_col = "—"
        plan_col = "matched" if rec.plan_figure_id else "—"
        if rec.plan_figure_id and rec.action == ReconciliationAction.append_new:
            plan_col = "new"
        lines.append(
            f"| {rec.figure_id} | {existing_col} | {plan_col} | {rec.action.value} |"
        )
    lines.append("")

    # Methods table.
    lines.append("## Methods reconciliation")
    lines.append("")
    lines.append("| Recipe family | Already documented? | Action |")
    lines.append("| --- | --- | --- |")
    for mrec in report.methods_reconciliations:
        documented = "yes" if mrec.already_documented else "no"
        action = "skip" if mrec.already_documented else "append"
        lines.append(f"| {mrec.family} | {documented} | {action} |")
    lines.append("")

    # Claim verdicts.
    n_supported = sum(1 for (_, v, _) in report.claim_verdicts if v == ClaimVerdict.supported)
    n_unsupported = sum(1 for (_, v, _) in report.claim_verdicts if v == ClaimVerdict.unsupported)
    n_unverifiable = sum(1 for (_, v, _) in report.claim_verdicts if v == ClaimVerdict.unverifiable)
    if report.claim_verdicts:
        lines.append("## Claim verdicts")
        lines.append("")
        lines.append(
            f"({n_supported} supported / {n_unsupported} unsupported / "
            f"{n_unverifiable} unverifiable)"
        )
        lines.append("")
        for sentence, verdict, rationale in report.claim_verdicts:
            marker = " (warn)" if verdict == ClaimVerdict.unsupported else ""
            lines.append(f"- \"{sentence}\" — {verdict.value.upper()}{marker}")
            lines.append(f"  rationale: {rationale}")
        lines.append("")

    # Action plan.
    lines.append("## Action plan under --manuscript-policy=update")
    lines.append("")
    actioned = False
    for rec in report.figure_reconciliations:
        if rec.action == ReconciliationAction.insert_block:
            lines.append(f"- Insert {rec.figure_id} block at line {rec.insertion_point_line}")
            actioned = True
        elif rec.action == ReconciliationAction.append_new:
            lines.append(f"- Append {rec.figure_id} block after line {rec.insertion_point_line}")
            actioned = True
    new_methods = [m for m in report.methods_reconciliations if not m.already_documented]
    if new_methods:
        line_no = new_methods[0].insertion_point_line
        lines.append(
            f"- Append {len(new_methods)} Methods paragraph"
            f"{'s' if len(new_methods) != 1 else ''} at line {line_no}"
        )
        actioned = True
    if n_unsupported:
        lines.append(
            f"- {n_unsupported} unsupported claim"
            f"{'s' if n_unsupported != 1 else ''} flagged — user must reconcile manually"
        )
        actioned = True
    if not actioned:
        lines.append("- No insertions required; manuscript is up to date.")
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# save_collision_log                                                          #
# --------------------------------------------------------------------------- #


def save_collision_log(
    insertions: list[tuple[int, str]],
    path: Path,
) -> Path:
    """Write a structured markdown log of every insertion.

    Each row records:

    * ``line``: the 1-indexed *target* line in the original manuscript
      (insertions happen *after* this line).
    * ``content excerpt``: the first non-blank line of the inserted block,
      truncated to 120 chars.

    A timestamp header is added so ``git diff`` reviewers can correlate
    multiple runs.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds")
    body: list[str] = []
    body.append("# panelforge-figures — Manuscript Collision Log")
    body.append("")
    body.append(f"_Generated {ts}; {len(insertions)} insertion(s)._")
    body.append("")
    body.append("| # | Original line | Content excerpt |")
    body.append("| --- | --- | --- |")
    for i, (line_no, excerpt) in enumerate(insertions, start=1):
        # Escape pipe characters that would break the markdown table.
        safe = excerpt.replace("|", "\\|").replace("\n", " ")
        body.append(f"| {i} | {line_no} | {safe} |")
    body.append("")
    body.append(
        "Verify the inserted lines with `git diff` against the original "
        "manuscript path. Any line not listed above came from upstream prose."
    )
    body.append("")
    path.write_text("\n".join(body), encoding="utf-8")
    return path
