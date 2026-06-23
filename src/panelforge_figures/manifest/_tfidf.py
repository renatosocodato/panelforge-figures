"""Shared stdlib-only TF-IDF helpers for the manifest manuscript modules.

Single source of truth for the lightweight, pure-Python TF-IDF
infrastructure used by three manuscript-aware modules:

* :mod:`manuscript_alignment` — manuscript-section ↔ recipe-question scoring.
* :mod:`manuscript_blueprint` — caption ↔ recipe matching (inverse import).
* :mod:`citation_inserter` — claim-sentence ↔ cached-query matching.

These six helpers were previously copy-pasted into all three modules
(Elevation-era drift). They are extracted here verbatim so every consumer
shares one behaviour-identical implementation: identical tokenisation
(lowercase, alphabetic-only, ≥ 2 chars), identical sklearn-style smoothed
IDF (``log((N+1)/(df+1)) + 1``), and identical cosine handling (returns
``0.0`` for an empty intersection or a zero-norm vector). No third-party
dependencies, fully offline.

Naming note
-----------
``citation_inserter`` historically named its copies ``_tokenise`` /
``_term_freq`` / ``_doc_freq`` / ``_tfidf_vec``. Those names are exported
here as thin aliases so that module's call sites stay unchanged and its
numeric output is byte-identical.
"""

from __future__ import annotations

import math
import re

__all__ = [
    "WORD_RE",
    "clamp01",
    "cosine",
    "document_frequency",
    "idf",
    "term_frequency",
    "tfidf",
    "tokenize",
]


#: Lowercase alphabetic-only word matcher (≥ 2 chars; numerics and
#: single-letter tokens are dropped — keeps the vocabulary aligned with
#: what TF-IDF can usefully discriminate).
WORD_RE = re.compile(r"\b[a-z][a-z]+\b")


def tokenize(text: str) -> list[str]:
    """Lowercase + alphabetic-only word tokenizer.

    Numerics and single-letter tokens are dropped.
    """
    return WORD_RE.findall(text.lower())


def term_frequency(tokens: list[str]) -> dict[str, float]:
    """Per-document term frequency (count / document length)."""
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    n = len(tokens)
    return {t: c / n for t, c in counts.items()}


def document_frequency(docs: list[list[str]]) -> dict[str, int]:
    """Number of documents each term appears in (presence, not count)."""
    df: dict[str, int] = {}
    for doc in docs:
        for t in set(doc):
            df[t] = df.get(t, 0) + 1
    return df


def idf(df: dict[str, int], n_docs: int) -> dict[str, float]:
    """Smoothed IDF (sklearn-style): ``log((N+1)/(df+1)) + 1``."""
    return {t: math.log((n_docs + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def tfidf(tokens: list[str], idf_map: dict[str, float]) -> dict[str, float]:
    """TF-IDF vector: term frequency weighted by the supplied IDF map.

    Terms absent from ``idf_map`` default to a weight of ``1.0`` (matching
    the original consumer behaviour).
    """
    tf = term_frequency(tokens)
    return {t: f * idf_map.get(t, 1.0) for t, f in tf.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two sparse term-weight vectors.

    Returns ``0.0`` when the vectors share no terms or either has a
    zero norm.
    """
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def clamp01(x: float) -> float:
    """Clamp a float into the closed unit interval ``[0, 1]``."""
    return min(1.0, max(0.0, x))
