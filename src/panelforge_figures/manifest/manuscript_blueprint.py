"""Manuscript-to-FigurePlan inverse direction (Elevation 10 — phase 3).

Given an existing manuscript file (LaTeX or Markdown), parse it, identify
every figure caption, match each caption to the best-fitting recipe via
TF-IDF cosine similarity, and emit a ``figures_plan.yaml`` that the rest
of the panelforge-figures pipeline can pick up via ``figures execute-plan``.

This is the **inverse** of the scout-then-scaffold pipeline:

* normal:    ``data/`` + intake answers  →  scout  →  ``figures_plan.yaml``  →  ``manuscript/main.tex``
* blueprint: ``manuscript.tex``  →  blueprint-import  →  ``figures_plan.yaml``  →  (resume normal pipeline)

The blueprint path lets a user who already has a written manuscript
(e.g. a re-submission, an editorial revision, or a draft from a
collaborator) recover the panelforge plan without re-doing the intake.

Public API
----------
- :class:`BlueprintImportResult` — frozen dataclass returned by
  :func:`import_blueprint_from_manuscript`.
- :class:`BlueprintImportError` — raised on parse failures or write
  errors.
- :class:`CaptionMatch` — one caption → best-fitting recipe + top-3
  alternative recipes.
- :func:`match_caption_to_recipe` — match one caption string against
  the registered recipes.
- :func:`import_blueprint_from_manuscript` — end-to-end driver.

Design notes
------------
* The matcher scores captions against the recipe corpus
  (``metadata.answers_question`` for every registered recipe) with a
  stdlib-only TF-IDF cosine similarity drawn from the shared
  :mod:`._tfidf` module (``tokenize`` / ``term_frequency`` /
  ``document_frequency`` / ``idf`` / ``tfidf`` / ``cosine``) — the same
  single-source-of-truth helpers used by :mod:`manuscript_alignment` and
  :mod:`citation_inserter`, with no extra deps; if that computation
  raises it falls back to a local Jaccard keyword-overlap score
  (``_keyword_overlap_score``) so partial functionality remains.
* Captions below ``min_similarity`` are flagged as ``is_gap=True`` with
  the original caption pasted into ``suggested_research_question`` so
  the user can scaffold a recipe via ``figures fill-gap`` afterwards.
* The emitted ``figures_plan.yaml`` is byte-compatible with what the
  scout writes — :func:`save_figure_plan_yaml` is reused.

See ``docs/spec_manuscript_collision.md`` §4 for the spec.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._tfidf import cosine as _cosine
from ._tfidf import document_frequency as _document_frequency
from ._tfidf import idf as _idf
from ._tfidf import tfidf as _tfidf
from ._tfidf import tokenize as _tokenize

__all__ = [
    "BlueprintImportError",
    "BlueprintImportResult",
    "CaptionMatch",
    "import_blueprint_from_manuscript",
    "match_caption_to_recipe",
]


# ─────────────────────────── exceptions ──────────────────────────────────


class BlueprintImportError(RuntimeError):
    """Raised on parse failures, missing manuscripts, or write errors."""


# ─────────────────────────── dataclasses ─────────────────────────────────


@dataclass(frozen=True)
class CaptionMatch:
    """One caption → best-fitting recipe + top-3 alternatives.

    Attributes
    ----------
    figure_id
        The figure identifier extracted from the manuscript (e.g.
        ``"fig:1"`` from ``\\label{fig:1}``, or the numeric position
        for unlabeled figures).
    caption_excerpt
        The first ~200 characters of the cleaned caption text — used
        for the markdown report and for ``suggested_research_question``
        when the match is a gap.
    suggested_recipe_full_name
        The best-fitting recipe's ``full_name`` (e.g.
        ``"omics_differential.volcano_labeled_repelled"``).  ``None`` if
        no recipe scored above zero.
    similarity_score
        Cosine similarity in ``[0, 1]``.  Strictly ``0.0`` means no
        textual overlap at all; values below ``min_similarity`` are
        treated as gaps by :func:`import_blueprint_from_manuscript`.
    candidate_alternatives
        Top-3 next-best recipe ``full_name``s — useful for the user
        when reviewing a borderline match.
    """

    figure_id: str
    caption_excerpt: str
    suggested_recipe_full_name: str | None
    similarity_score: float
    candidate_alternatives: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BlueprintImportResult:
    """End-to-end result of one :func:`import_blueprint_from_manuscript` run."""

    manuscript_path: Path
    n_figures_parsed: int
    n_figures_matched: int            # similarity >= min_similarity
    n_figures_unmatched: int          # similarity < min_similarity
    matches: tuple[CaptionMatch, ...]
    figure_plan_path: Path | None     # location of the emitted figures_plan.yaml
    notes: tuple[str, ...] = ()


# ─────────────────────────── caption text cleanup ────────────────────────


# LaTeX caption-command stripper: matches ``\command``, ``\command{arg}``,
# and ``\command[opt]{arg}``.  Keeps the inner ``arg`` text by capturing it.
_LATEX_TEXT_CMD_RE = re.compile(r"\\(?:emph|textbf|textit|texttt|mathit|mathrm)\{([^{}]*)\}")
_LATEX_BARE_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?")
_LATEX_BRACES_RE = re.compile(r"[{}]")

# Markdown markup stripper: ``**bold**``, ``*italic*``, ``[text](url)``,
# inline math ``$...$``, link-references ``[@cite]``.
_MD_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_CITE_RE = re.compile(r"\[@[^\]]+\]")
_MD_MATH_RE = re.compile(r"\$[^$]*\$")


def _strip_caption_formatting(text: str) -> str:
    """Strip LaTeX / Markdown markup from a caption string.

    The cleaner is deliberately tolerant: unknown commands are dropped,
    inline math is removed (TF-IDF can't match ``$\alpha$`` to anything
    useful), and whitespace is normalised.
    """
    if not text:
        return ""
    # Strip text-affecting LaTeX commands but keep their inner text.
    cleaned = _LATEX_TEXT_CMD_RE.sub(r"\1", text)
    # Strip the rest of the LaTeX commands.
    cleaned = _LATEX_BARE_CMD_RE.sub(" ", cleaned)
    cleaned = _LATEX_BRACES_RE.sub(" ", cleaned)
    # Strip Markdown markup.
    cleaned = _MD_BOLD_RE.sub(r"\1", cleaned)
    cleaned = _MD_ITALIC_RE.sub(r"\1", cleaned)
    cleaned = _MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = _MD_CITE_RE.sub(" ", cleaned)
    cleaned = _MD_MATH_RE.sub(" ", cleaned)
    # Normalise whitespace.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ─────────────────────────── recipe corpus helpers ───────────────────────


def _list_recipes_safe() -> list[Any]:
    """Return every registered recipe, tolerant on import failures."""
    try:
        from ..core.contract import ensure_all_imported, list_recipes
    except Exception:  # pragma: no cover — defensive
        return []
    try:
        ensure_all_imported()
    except Exception:  # pragma: no cover — modality import failed
        pass
    try:
        return list(list_recipes())
    except Exception:  # pragma: no cover — defensive
        return []


def _recipe_full_name(recipe: Any) -> str:
    """Best-effort ``modality.name`` extraction from a recipe entry."""
    full = getattr(recipe, "full_name", None)
    if full:
        return str(full)
    meta = getattr(recipe, "metadata", None)
    if meta is not None:
        modality = getattr(meta, "modality", None)
        name = getattr(meta, "name", None)
        if modality and name:
            return f"{modality}.{name}"
    return ""


def _recipe_answers_question(recipe: Any) -> str:
    """Best-effort answers_question extraction from a recipe entry."""
    meta = getattr(recipe, "metadata", None)
    if meta is not None:
        q = getattr(meta, "answers_question", None)
        if q:
            return str(q)
    return ""


# ─────────────────────────── TF-IDF + Jaccard fallback ───────────────────
#
# The TF-IDF helpers (``_tokenize`` / ``_term_frequency`` /
# ``_document_frequency`` / ``_idf`` / ``_tfidf`` / ``_cosine``) come from the
# shared :mod:`._tfidf` module — the single source of truth also used by
# ``manuscript_alignment`` and ``citation_inserter``. They are imported under
# their original private names at the top of this module. Only the
# blueprint-specific Jaccard fallback below is defined locally.


def _keyword_overlap_score(caption_tokens: list[str], recipe_tokens: list[str]) -> float:
    """Fallback similarity: |intersection| / |union| (Jaccard)."""
    if not caption_tokens or not recipe_tokens:
        return 0.0
    a = set(caption_tokens)
    b = set(recipe_tokens)
    inter = a & b
    union = a | b
    if not union:
        return 0.0
    return len(inter) / len(union)


# ─────────────────────────── match_caption_to_recipe ─────────────────────


def match_caption_to_recipe(
    caption_text: str,
    *,
    candidate_recipes: list[Any] | None = None,
    min_similarity: float = 0.4,
    figure_id: str = "?",
) -> CaptionMatch:
    """Match one caption string to the best-fitting registered recipe.

    Uses a stdlib-only TF-IDF cosine similarity over the recipe corpus
    (``metadata.answers_question`` for every registered recipe).  If the
    TF-IDF computation raises, falls back to a Jaccard keyword-overlap
    score; if the recipe registry can't be loaded at all, returns an
    empty (``similarity_score = 0.0``) match so the caller always gets a
    structured answer.

    Parameters
    ----------
    caption_text
        The caption text (already stripped of LaTeX/Markdown markup, or
        the cleaner is applied here as a final defensive pass).
    candidate_recipes
        Optional explicit recipe list to match against.  ``None`` →
        every registered recipe.
    min_similarity
        Below this threshold the caller treats the match as a gap; this
        function still returns the best-scoring candidate (a downstream
        consumer may choose to display it as "would have been …").
    figure_id
        Figure identifier passed through to :class:`CaptionMatch`.

    Returns
    -------
    CaptionMatch
        Always non-None; ``similarity_score = 0.0`` when no recipe matched.
    """
    cleaned = _strip_caption_formatting(caption_text)
    excerpt = cleaned[:200]
    caption_tokens = _tokenize(cleaned)

    if candidate_recipes is None:
        candidate_recipes = _list_recipes_safe()

    if not candidate_recipes:
        return CaptionMatch(
            figure_id=figure_id,
            caption_excerpt=excerpt,
            suggested_recipe_full_name=None,
            similarity_score=0.0,
            candidate_alternatives=(),
        )

    # Build the recipe corpus from answers_question.
    recipe_corpus: list[tuple[str, str, list[str]]] = []
    for r in candidate_recipes:
        full = _recipe_full_name(r)
        question = _recipe_answers_question(r)
        if not full or not question:
            continue
        recipe_corpus.append((full, question, _tokenize(question)))

    if not recipe_corpus:
        return CaptionMatch(
            figure_id=figure_id,
            caption_excerpt=excerpt,
            suggested_recipe_full_name=None,
            similarity_score=0.0,
            candidate_alternatives=(),
        )

    # Try TF-IDF cosine; fall back to Jaccard keyword overlap on failure.
    try:
        all_docs = [caption_tokens] + [toks for _, _, toks in recipe_corpus]
        df = _document_frequency(all_docs)
        idf = _idf(df, max(len(all_docs), 1))
        caption_vec = _tfidf(caption_tokens, idf)
        scored: list[tuple[str, float]] = []
        for full, _q, toks in recipe_corpus:
            rec_vec = _tfidf(toks, idf)
            scored.append((full, _cosine(caption_vec, rec_vec)))
    except Exception:  # pragma: no cover — fallback
        scored = [
            (full, _keyword_overlap_score(caption_tokens, toks))
            for full, _q, toks in recipe_corpus
        ]

    scored.sort(key=lambda kv: kv[1], reverse=True)
    if not scored:
        best_full: str | None = None
        best_score = 0.0
        alts: tuple[str, ...] = ()
    else:
        best_full, best_score = scored[0]
        if best_score == 0.0:
            best_full = None
        alts = tuple(full for full, _ in scored[1:4])

    # Clamp similarity to [0, 1].
    score = max(0.0, min(1.0, float(best_score)))
    return CaptionMatch(
        figure_id=figure_id,
        caption_excerpt=excerpt,
        suggested_recipe_full_name=best_full if score > 0.0 else None,
        similarity_score=score,
        candidate_alternatives=alts,
    )


# ─────────────────────────── manuscript parsing bridge ──────────────────


def _parse_manuscript_safely(manuscript_path: Path) -> Any:
    """Try Build-A's parse_manuscript; raise a clean BlueprintImportError on failure."""
    try:
        from .manuscript_parse import parse_manuscript
    except ImportError as exc:
        raise BlueprintImportError(
            f"manuscript_parse not available (Build-A may not have landed): {exc}"
        ) from exc

    try:
        return parse_manuscript(manuscript_path)
    except Exception as exc:
        raise BlueprintImportError(
            f"failed to parse {manuscript_path}: {exc}"
        ) from exc


def _figure_blocks_from_parsed(existing: Any) -> list[Any]:
    """Best-effort extraction of figure blocks from a parsed ExistingManuscript."""
    blocks = getattr(existing, "figure_blocks", None)
    if blocks is None:
        return []
    return list(blocks)


def _block_attr(block: Any, name: str, default: Any = None) -> Any:
    """Read ``block.name`` or ``block[name]``."""
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


# ─────────────────────────── FigurePlan synthesis ────────────────────────


def _build_panel_for_match(
    match: CaptionMatch,
    *,
    figure_index: int,
    min_similarity: float,
) -> Any:
    """Construct a PanelSlot for one caption match, lazy-importing scout."""
    from .scout import PanelSlot

    figure_id_label = f"Figure {figure_index}"
    # Convert "1A" / "fig:1" / etc. to a panel_id label.
    panel_id = f"{figure_index}A"

    is_gap = match.similarity_score < min_similarity
    if not is_gap and match.suggested_recipe_full_name:
        return PanelSlot(
            panel_id=panel_id,
            figure_id=figure_id_label,
            recipe_full_name=match.suggested_recipe_full_name,
            research_question=match.caption_excerpt,
            data_file_hint=None,
            role="primary",
            is_gap=False,
            rationale=(
                f"caption→recipe TF-IDF match "
                f"(similarity={match.similarity_score:.2f})"
            ),
        )
    # Gap branch — caption couldn't be matched.
    return PanelSlot(
        panel_id=panel_id,
        figure_id=figure_id_label,
        recipe_full_name="",
        research_question=match.caption_excerpt,
        data_file_hint=None,
        role="primary",
        is_gap=True,
        suggested_recipe_name=f"imported_blueprint_panel_{figure_index}_v1",
        suggested_research_question=match.caption_excerpt,
        rationale=(
            f"caption similarity {match.similarity_score:.2f} < threshold "
            f"{min_similarity:.2f}; scaffold a recipe via figures fill-gap"
        ),
    )


def _build_figure_slot(panel: Any, *, figure_index: int) -> Any:
    """Wrap one PanelSlot into a single-panel FigureSlot."""
    from .scout import FigureSlot, FigureSlotKind

    figure_id_label = f"Figure {figure_index}"
    title = f"Figure {figure_index} — imported from manuscript"
    return FigureSlot(
        figure_id=figure_id_label,
        title=title,
        slot_kind=FigureSlotKind.biology,
        panels=(panel,),
    )


def _build_figure_plan_from_matches(
    matches: list[CaptionMatch],
    *,
    project_root: Path,
    venue: str,
    min_similarity: float,
) -> Any:
    """Build a :class:`FigurePlan` from a list of caption matches.

    Each match becomes a single-panel figure (the import path keeps the
    1-caption→1-figure mapping intact; the user can re-group panels via
    a downstream edit).
    """
    from .scout import FigurePlan

    figures: list[Any] = []
    for idx, match in enumerate(matches, start=1):
        panel = _build_panel_for_match(
            match,
            figure_index=idx,
            min_similarity=min_similarity,
        )
        figures.append(_build_figure_slot(panel, figure_index=idx))

    n_panels = sum(len(f.panels) for f in figures)
    n_gaps = sum(1 for f in figures for p in f.panels if p.is_gap)
    return FigurePlan(
        project_root=project_root,
        project_id=None,
        figures=tuple(figures),
        venue=venue,
        n_figures=len(figures),
        n_panels=n_panels,
        n_gaps=n_gaps,
    )


# ─────────────────────────── end-to-end driver ───────────────────────────


def _resolve_venue(
    requested: str | None,
    existing: Any,
) -> str:
    """Pick the venue: explicit request → manuscript hint → 'cell' default."""
    if requested:
        return requested
    hint = getattr(existing, "venue_hint", None)
    if hint:
        try:
            return str(hint.value) if hasattr(hint, "value") else str(hint)
        except Exception:  # pragma: no cover — defensive
            pass
    return "cell"


def import_blueprint_from_manuscript(
    manuscript_path: Path,
    *,
    output_plan_path: Path | None = None,
    min_similarity: float = 0.4,
    venue: str | None = None,
) -> BlueprintImportResult:
    """Parse a manuscript → emit a ``figures_plan.yaml``.

    Pipeline
    --------
    1. :func:`manuscript_parse.parse_manuscript` →
       :class:`ExistingManuscript` (Build-A's module).
    2. Extract every figure block.  For each block:
       a. Strip LaTeX/Markdown markup from the caption text.
       b. Match the caption to the best recipe via
          :func:`match_caption_to_recipe`.
       c. If ``similarity >= min_similarity``: include as ``role=primary``
          recipe panel.
       d. If below threshold: flag as ``is_gap=True`` with the caption
          excerpt in ``suggested_research_question``.
    3. Build a :class:`FigurePlan` with one figure per caption (single
       panel each — the user can re-group via downstream edits).
    4. If ``output_plan_path`` is set: write the plan via
       :func:`scout.save_figure_plan_yaml`.
    5. Return :class:`BlueprintImportResult`.

    Parameters
    ----------
    manuscript_path
        Path to an existing manuscript file (``.tex`` / ``.md`` / ``.txt``).
    output_plan_path
        Where to write the emitted ``figures_plan.yaml``.  ``None`` →
        don't write; just return the matches.
    min_similarity
        Threshold below which a caption is treated as a gap.
    venue
        Venue string for the plan.  ``None`` → use the manuscript hint
        if any, else ``"cell"``.

    Raises
    ------
    BlueprintImportError
        On parse failures or write errors.  Per-caption matching errors
        are absorbed into a gap entry rather than raised.
    """
    manuscript_path = Path(manuscript_path)
    if not manuscript_path.exists():
        raise BlueprintImportError(f"manuscript not found: {manuscript_path}")

    notes: list[str] = []

    existing = _parse_manuscript_safely(manuscript_path)
    blocks = _figure_blocks_from_parsed(existing)
    if not blocks:
        notes.append(
            "no figure blocks detected in manuscript; emitted plan will be empty"
        )

    candidate_recipes = _list_recipes_safe()
    if not candidate_recipes:
        notes.append(
            "registered recipe list is empty; every caption will become a gap"
        )

    matches: list[CaptionMatch] = []
    for i, block in enumerate(blocks, start=1):
        figure_id = (
            _block_attr(block, "figure_id")
            or _block_attr(block, "label")
            or f"fig:{i}"
        )
        caption_text = (
            _block_attr(block, "caption_text")
            or _block_attr(block, "caption")
            or ""
        )
        try:
            match = match_caption_to_recipe(
                caption_text,
                candidate_recipes=candidate_recipes,
                min_similarity=min_similarity,
                figure_id=str(figure_id),
            )
        except Exception as exc:  # pragma: no cover — defensive
            warnings.warn(
                f"caption match failed for {figure_id}: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            match = CaptionMatch(
                figure_id=str(figure_id),
                caption_excerpt=_strip_caption_formatting(caption_text)[:200],
                suggested_recipe_full_name=None,
                similarity_score=0.0,
                candidate_alternatives=(),
            )
        matches.append(match)

    n_parsed = len(matches)
    n_matched = sum(1 for m in matches if m.similarity_score >= min_similarity)
    n_unmatched = n_parsed - n_matched

    resolved_venue = _resolve_venue(venue, existing)

    figure_plan_path: Path | None = None
    if output_plan_path is not None:
        try:
            from .scout import save_figure_plan_yaml
        except ImportError as exc:  # pragma: no cover — defensive
            raise BlueprintImportError(
                f"scout.save_figure_plan_yaml not importable: {exc}"
            ) from exc
        plan = _build_figure_plan_from_matches(
            matches,
            project_root=manuscript_path.parent,
            venue=resolved_venue,
            min_similarity=min_similarity,
        )
        try:
            figure_plan_path = save_figure_plan_yaml(plan, Path(output_plan_path))
        except Exception as exc:
            raise BlueprintImportError(
                f"failed to write figures_plan to {output_plan_path}: {exc}"
            ) from exc
        notes.append(f"wrote figures_plan to {figure_plan_path}")

    if n_unmatched:
        notes.append(
            f"{n_unmatched} caption(s) below similarity threshold "
            f"{min_similarity:.2f}; flagged as gaps"
        )

    return BlueprintImportResult(
        manuscript_path=manuscript_path,
        n_figures_parsed=n_parsed,
        n_figures_matched=n_matched,
        n_figures_unmatched=n_unmatched,
        matches=tuple(matches),
        figure_plan_path=figure_plan_path,
        notes=tuple(notes),
    )
