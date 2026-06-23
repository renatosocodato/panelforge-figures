"""Tests for the shared `manifest._tfidf` module (structural-debt item #10).

Context
-------
The six pure-Python TF-IDF helpers (tokenize, term-frequency,
document-frequency, idf, tf-idf vector, cosine) were previously
copy-pasted into three modules — ``manuscript_alignment``,
``manuscript_blueprint``, and ``citation_inserter`` — and the blueprint
docstring falsely claimed to "reuse the TF-IDF infrastructure from
manuscript_alignment" while never importing it.

This test pins two things:

1. The *core behaviour* of the extracted helpers (tokenisation, the
   tf-idf vector, and cosine similarity on a small fixture).
2. That all three consumer modules now route through ``manifest._tfidf``
   rather than re-defining the helpers locally — asserted by object
   *identity* against the shared functions. These identity assertions
   reproduce-before-fix: on the unfixed (triplicated) code each module
   bound its own distinct function object, so the ``is`` checks fail.
"""
from __future__ import annotations

import math

from panelforge_figures.manifest import _tfidf
from panelforge_figures.manifest import citation_inserter as ci
from panelforge_figures.manifest import manuscript_alignment as ma
from panelforge_figures.manifest import manuscript_blueprint as mb

# ──────────────────────── 1. core behaviour ────────────────────────


def test_tokenize_lowercases_and_filters() -> None:
    """`tokenize` lowercases, keeps alphabetic words ≥ 2 chars, drops the rest."""
    tokens = _tfidf.tokenize("RNA-seq of 12 Cells: a B cd EF!")
    # "a"/"B" are single-letter → dropped; "12" numeric → dropped.
    # "rna", "seq", "of", "cells", "cd", "ef" survive (lowercased).
    assert tokens == ["rna", "seq", "of", "cells", "cd", "ef"]


def test_tokenize_empty() -> None:
    assert _tfidf.tokenize("") == []


def test_term_frequency_normalises_by_length() -> None:
    tf = _tfidf.term_frequency(["a", "a", "b", "c"])
    assert tf["a"] == 0.5
    assert tf["b"] == 0.25
    assert tf["c"] == 0.25
    assert _tfidf.term_frequency([]) == {}


def test_idf_is_sklearn_smoothed() -> None:
    """IDF uses the smoothed sklearn form: log((N+1)/(df+1)) + 1."""
    df = {"common": 3, "rare": 1}
    idf = _tfidf.idf(df, n_docs=3)
    assert idf["common"] == math.log((3 + 1) / (3 + 1)) + 1.0  # == 1.0
    assert idf["rare"] == math.log((3 + 1) / (1 + 1)) + 1.0
    # The rarer term must have the strictly larger IDF weight.
    assert idf["rare"] > idf["common"]


def test_tfidf_vector_weights_by_idf() -> None:
    idf = {"x": 2.0}  # "y" absent → defaults to weight 1.0
    vec = _tfidf.tfidf(["x", "x", "y", "y"], idf)
    assert vec["x"] == 0.5 * 2.0
    assert vec["y"] == 0.5 * 1.0


def test_cosine_identical_and_orthogonal() -> None:
    a = {"x": 1.0, "y": 2.0}
    # Identical direction → cosine 1.0 (modulo FP rounding — exactly why
    # the codebase clamps cosine outputs with `clamp01`).
    assert math.isclose(_tfidf.cosine(a, a), 1.0, rel_tol=1e-9)
    # Disjoint support → cosine 0.0.
    assert _tfidf.cosine(a, {"z": 3.0}) == 0.0
    # Zero-norm vector → 0.0 (no division-by-zero).
    assert _tfidf.cosine(a, {}) == 0.0


def test_cosine_on_small_fixture() -> None:
    """End-to-end tf-idf cosine over a tiny 3-doc corpus.

    The query doc shares more vocabulary with doc-A than doc-B, so its
    similarity to A must strictly exceed its similarity to B.
    """
    query = _tfidf.tokenize("volcano plot of differential gene expression")
    doc_a = _tfidf.tokenize("differential gene expression volcano plot panel")
    doc_b = _tfidf.tokenize("survival kaplan meier curve over time")

    corpus = [query, doc_a, doc_b]
    df = _tfidf.document_frequency(corpus)
    idf = _tfidf.idf(df, len(corpus))

    qv = _tfidf.tfidf(query, idf)
    av = _tfidf.tfidf(doc_a, idf)
    bv = _tfidf.tfidf(doc_b, idf)

    sim_a = _tfidf.cosine(qv, av)
    sim_b = _tfidf.cosine(qv, bv)

    assert 0.0 < sim_a <= 1.0
    assert sim_b == 0.0 or sim_b < sim_a
    assert sim_a > sim_b


def test_clamp01() -> None:
    assert _tfidf.clamp01(-0.5) == 0.0
    assert _tfidf.clamp01(0.3) == 0.3
    assert _tfidf.clamp01(1.7) == 1.0


# ─────────── 2. consumers route through the shared module ───────────
#
# These identity checks are the reproduce-before-fix guard: on the
# pre-extraction (triplicated) code each module defined its own copy, so
# every `is _tfidf.<fn>` assertion fails.


def test_manuscript_alignment_uses_shared_tfidf() -> None:
    assert ma._tokenize is _tfidf.tokenize
    assert ma._idf is _tfidf.idf
    assert ma._tfidf is _tfidf.tfidf
    assert ma._cosine is _tfidf.cosine
    assert ma._document_frequency is _tfidf.document_frequency
    assert ma._clamp01 is _tfidf.clamp01


def test_manuscript_blueprint_uses_shared_tfidf() -> None:
    assert mb._tokenize is _tfidf.tokenize
    assert mb._idf is _tfidf.idf
    assert mb._tfidf is _tfidf.tfidf
    assert mb._cosine is _tfidf.cosine
    assert mb._document_frequency is _tfidf.document_frequency


def test_citation_inserter_uses_shared_tfidf() -> None:
    # citation_inserter historically used different private names; they
    # must now alias the shared implementations.
    assert ci._tokenise is _tfidf.tokenize
    assert ci._idf is _tfidf.idf
    assert ci._tfidf_vec is _tfidf.tfidf
    assert ci._cosine is _tfidf.cosine
    assert ci._doc_freq is _tfidf.document_frequency
    assert ci._clamp01 is _tfidf.clamp01


def test_no_local_redefinition_of_helpers() -> None:
    """No consumer module re-defines a TF-IDF helper as its own function.

    A local ``def`` would create a function whose ``__module__`` points
    at the consumer module instead of ``manifest._tfidf``; assert every
    bound helper still belongs to the shared module.
    """
    shared = _tfidf.__name__  # "panelforge_figures.manifest._tfidf"
    for fn in (ma._tokenize, ma._idf, ma._tfidf, ma._cosine, ma._clamp01):
        assert fn.__module__ == shared
    for fn in (mb._tokenize, mb._idf, mb._tfidf, mb._cosine):
        assert fn.__module__ == shared
    for fn in (ci._tokenise, ci._idf, ci._tfidf_vec, ci._cosine, ci._clamp01):
        assert fn.__module__ == shared
