"""Manuscript-aware scoring boost.

Reads full manuscript text, computes TF-IDF (or optionally
sentence-transformers) similarity between manuscript sections and recipe
``_META.answers_question`` strings, returns per-recipe ``manuscript_alignment``
score ∈ [0, 1].

Elevation 7 (v3.0.0-rc2): introduces the ``manuscript_alignment`` term and
registers it under ``WEIGHTS_HISTORY['1.1.0']``.  v3.0.0 ships in shadow
mode — the rubric is a known but non-default version, so re-ranking is
opt-in via ``--weights-version 1.1.0`` until calibration data lands.

The TF-IDF backend is pure Python (no extra deps) so this elevation stays
lightweight + offline.  The optional ``sentence_transformers`` backend is
gated behind the ``[embeddings]`` extra.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from ._tfidf import clamp01 as _clamp01
from ._tfidf import cosine as _cosine
from ._tfidf import document_frequency as _document_frequency
from ._tfidf import idf as _idf
from ._tfidf import tfidf as _tfidf
from ._tfidf import tokenize as _tokenize

__all__ = [
    "ManuscriptAlignmentError",
    "AlignmentBackend",
    "AlignmentScore",
    "compute_alignment_scores",
    "compute_tfidf_alignment",
    "compute_embedding_alignment",
    "score_to_dict",
]


class ManuscriptAlignmentError(RuntimeError):
    """Raised when manuscript can't be read or backend is missing."""


class AlignmentBackend(StrEnum):
    """Selects the similarity backend for manuscript alignment."""

    tfidf = "tfidf"
    sentence_transformers = "sentence_transformers"


@dataclass(frozen=True)
class AlignmentScore:
    """Per-recipe alignment result.

    Attributes
    ----------
    recipe_full_name
        The dotted ``"{modality}.{name}"`` identifier.
    score
        Similarity ∈ [0, 1].  Always clamped — the TF-IDF cosine and the
        sentence-transformer cosine can both stray slightly outside that
        range due to FP rounding.
    matched_sections
        Top-3 manuscript section headers (best → worst) used for
        diagnostics; empty when no sections were detected.
    backend
        Which backend produced the score.
    """

    recipe_full_name: str
    score: float
    matched_sections: tuple[str, ...]
    backend: AlignmentBackend


# ─────────── TF-IDF backend ───────────
#
# The pure-Python TF-IDF helpers (``_tokenize`` / ``_term_frequency`` /
# ``_document_frequency`` / ``_idf`` / ``_tfidf`` / ``_cosine`` / ``_clamp01``)
# live in :mod:`._tfidf` — the single source of truth shared with
# ``manuscript_blueprint`` and ``citation_inserter``. They are imported at
# the top of this module under their original private names.


_MD_HEADER_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.MULTILINE)
_LATEX_SECTION_RE = re.compile(r"\\(?:section|subsection)\*?\{(.+?)\}", re.MULTILINE)


def _split_manuscript_sections(text: str) -> dict[str, str]:
    """Split manuscript text by markdown headers OR LaTeX section commands.

    Returns a dict ``{header: section_body}`` plus a ``"_full"`` entry
    holding the entire document — used as a fallback when no headers are
    present (so we always have at least one comparable document).
    """
    sections: dict[str, str] = {"_full": text}

    # Markdown headers take precedence — if any present, use them
    splits = list(_MD_HEADER_RE.finditer(text))
    if splits:
        for i, m in enumerate(splits):
            heading = m.group(1).strip()
            start = m.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            sections[heading] = text[start:end].strip()
        return sections

    # LaTeX fallback
    splits = list(_LATEX_SECTION_RE.finditer(text))
    if splits:
        for i, m in enumerate(splits):
            heading = m.group(1).strip()
            start = m.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            sections[heading] = text[start:end].strip()
    return sections


def compute_tfidf_alignment(
    manuscript_text: str,
    recipes: list[Any],   # list of RecipeInfo / _RegistryEntry
) -> list[AlignmentScore]:
    """TF-IDF cosine similarity between manuscript sections + recipe questions.

    Each recipe's score is the **best** cosine similarity across all
    detected manuscript sections.  Sections fall back to the full
    manuscript when no headers are found.
    """
    sections = _split_manuscript_sections(manuscript_text)
    section_tokens = {h: _tokenize(t) for h, t in sections.items()}

    recipe_questions: dict[str, str] = {}
    for info in recipes:
        full = f"{info.metadata.modality}.{info.metadata.name}"
        recipe_questions[full] = info.metadata.answers_question
    recipe_tokens = {full: _tokenize(q) for full, q in recipe_questions.items()}

    # IDF computed across ALL documents (sections + recipe questions) so
    # term-rarity is calibrated against the corpus the user has.
    all_docs = list(section_tokens.values()) + list(recipe_tokens.values())
    df = _document_frequency(all_docs)
    idf = _idf(df, max(len(all_docs), 1))

    section_vecs = {h: _tfidf(toks, idf) for h, toks in section_tokens.items()}
    recipe_vecs = {full: _tfidf(toks, idf) for full, toks in recipe_tokens.items()}

    scores: list[AlignmentScore] = []
    for full, rvec in recipe_vecs.items():
        # Score against every section except the synthetic "_full" entry
        # (which would otherwise dominate when sections are short).
        sims = [
            (h, _cosine(rvec, svec))
            for h, svec in section_vecs.items()
            if h != "_full"
        ]
        if not sims:
            # No headers detected — fall back to the full manuscript.
            sims = [("_full", _cosine(rvec, section_vecs["_full"]))]
        sims.sort(key=lambda kv: kv[1], reverse=True)
        best_score = sims[0][1] if sims else 0.0
        # Top-3 matched sections for diagnostics.
        matched = tuple(h for h, _ in sims[:3])
        scores.append(
            AlignmentScore(
                recipe_full_name=full,
                score=_clamp01(best_score),
                matched_sections=matched,
                backend=AlignmentBackend.tfidf,
            )
        )
    return scores


def compute_embedding_alignment(
    manuscript_text: str,
    recipes: list[Any],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> list[AlignmentScore]:
    """Optional sentence-transformers backend (gated by ``[embeddings]`` extra).

    Raises ``ManuscriptAlignmentError`` if ``sentence_transformers`` is
    not importable so callers can degrade gracefully to TF-IDF.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:                 # pragma: no cover - env-dependent
        raise ManuscriptAlignmentError(
            "sentence-transformers not installed; install with "
            "`pip install panelforge-figures[embeddings]`"
        ) from exc

    try:
        import numpy as np
    except ImportError as exc:                 # pragma: no cover - numpy is a hard dep
        raise ManuscriptAlignmentError(
            "numpy not available; required for the sentence-transformers backend"
        ) from exc

    model = SentenceTransformer(model_name)
    sections = _split_manuscript_sections(manuscript_text)
    section_keys = list(sections.keys())
    section_embs = model.encode([sections[k] for k in section_keys])

    questions = [info.metadata.answers_question for info in recipes]
    full_names = [f"{info.metadata.modality}.{info.metadata.name}" for info in recipes]
    recipe_embs = model.encode(questions) if questions else []

    scores: list[AlignmentScore] = []
    for i, full in enumerate(full_names):
        rvec = recipe_embs[i]
        sims: list[tuple[str, float]] = []
        for j, sk in enumerate(section_keys):
            if sk == "_full":
                continue
            svec = section_embs[j]
            num = float(np.dot(rvec, svec))
            den = float(np.linalg.norm(rvec) * np.linalg.norm(svec))
            sims.append((sk, num / den if den else 0.0))
        sims.sort(key=lambda kv: kv[1], reverse=True)
        best_score = sims[0][1] if sims else 0.0
        scores.append(
            AlignmentScore(
                recipe_full_name=full,
                score=_clamp01(best_score),
                matched_sections=tuple(s for s, _ in sims[:3]),
                backend=AlignmentBackend.sentence_transformers,
            )
        )
    return scores


def compute_alignment_scores(
    manuscript_path: Path,
    recipes: list[Any],
    *,
    backend: AlignmentBackend = AlignmentBackend.tfidf,
) -> list[AlignmentScore]:
    """Top-level pipeline: read manuscript, dispatch to backend.

    Parameters
    ----------
    manuscript_path
        Path to a UTF-8-encoded markdown or LaTeX manuscript file.
    recipes
        List of ``_RegistryEntry`` (or any object with
        ``.metadata.modality``, ``.metadata.name``,
        ``.metadata.answers_question``).
    backend
        Which similarity backend to use.  Default is TF-IDF (offline,
        zero extra deps).

    Raises
    ------
    ManuscriptAlignmentError
        If the manuscript file is missing, or the requested backend is
        unavailable.
    """
    if not manuscript_path.exists():
        raise ManuscriptAlignmentError(f"manuscript not found: {manuscript_path}")
    text = manuscript_path.read_text(encoding="utf-8")
    if backend == AlignmentBackend.tfidf:
        return compute_tfidf_alignment(text, recipes)
    return compute_embedding_alignment(text, recipes)


def score_to_dict(score: AlignmentScore) -> dict[str, Any]:
    """JSON-serializable view of an ``AlignmentScore``.

    Used by the CLI's ``--json`` output and by anything else that needs
    to ship the score over a wire (e.g. the recipes_index integrator).
    """
    return {
        "recipe_full_name": score.recipe_full_name,
        "score": score.score,
        "matched_sections": list(score.matched_sections),
        "backend": score.backend.value,
    }
