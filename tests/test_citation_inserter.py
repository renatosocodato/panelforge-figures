"""Tests for E14 — smart citation insertion from Consensus cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.citation_inserter import (
    CACHE_DIR_DEFAULT,
    BibEntry,
    CitationInsertionResult,
    CitationSuggestion,
    InserterError,
    apply_citation_insertions,
    build_bib_entries_from_consensus,
    render_suggestions_markdown,
    scan_consensus_cache,
    suggest_citations_for_manuscript,
)

# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _write_cache_entry(
    cache_dir: Path,
    *,
    name: str,
    query: str,
    papers: list[dict],
) -> Path:
    """Write one Consensus cache JSON file under ``cache_dir``."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{name}.json"
    target.write_text(
        json.dumps({"query": query, "papers": papers}),
        encoding="utf-8",
    )
    return target


def _make_paper(
    *,
    title: str = "Microglia regulate synaptic plasticity",
    authors: list[str] | None = None,
    year: int = 2024,
    journal: str = "Nat Neurosci",
    doi: str = "10.1038/nn.demo",
) -> dict:
    return {
        "title": title,
        "authors": authors or ["Smith J.", "Doe A."],
        "year": year,
        "journal": journal,
        "doi": doi,
        "abstract": "Background: synaptic plasticity is gated by microglia.",
        "relevance_score": 0.91,
    }


# --------------------------------------------------------------------------- #
# 1. scan_consensus_cache                                                     #
# --------------------------------------------------------------------------- #


class TestScanConsensusCache:
    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        assert scan_consensus_cache(tmp_path / "nope") == {}

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "cache").mkdir()
        assert scan_consensus_cache(tmp_path / "cache") == {}

    def test_reads_well_formed_cache(self, tmp_path: Path) -> None:
        cache = tmp_path / "cache"
        _write_cache_entry(
            cache,
            name="q1",
            query="microglia synaptic plasticity",
            papers=[_make_paper(), _make_paper(title="Synaptic pruning")],
        )
        out = scan_consensus_cache(cache)
        assert "microglia synaptic plasticity" in out
        assert len(out["microglia synaptic plasticity"]) == 2

    def test_falls_back_to_top_papers_key(self, tmp_path: Path) -> None:
        # Some E9 snapshots use ``top_papers`` instead of ``papers``.
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "legacy.json").write_text(
            json.dumps(
                {"query": "rho dynamics", "top_papers": [_make_paper()]}
            ),
            encoding="utf-8",
        )
        out = scan_consensus_cache(cache)
        assert "rho dynamics" in out
        assert len(out["rho dynamics"]) == 1

    def test_corrupt_json_is_silently_skipped(self, tmp_path: Path) -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "broken.json").write_text("{not: valid json", encoding="utf-8")
        _write_cache_entry(
            cache, name="ok", query="ok", papers=[_make_paper()]
        )
        out = scan_consensus_cache(cache)
        assert "ok" in out and "broken" not in out

    def test_query_falls_back_to_filename_stem(self, tmp_path: Path) -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "no_query_field.json").write_text(
            json.dumps({"papers": [_make_paper()]}),
            encoding="utf-8",
        )
        out = scan_consensus_cache(cache)
        assert "no_query_field" in out

    def test_skips_files_with_empty_paper_list(self, tmp_path: Path) -> None:
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "empty.json").write_text(
            json.dumps({"query": "x", "papers": []}),
            encoding="utf-8",
        )
        out = scan_consensus_cache(cache)
        assert out == {}


# --------------------------------------------------------------------------- #
# 2. build_bib_entries_from_consensus                                         #
# --------------------------------------------------------------------------- #


class TestBuildBibEntries:
    def test_basic_cite_key_generation(self) -> None:
        papers = [
            _make_paper(
                title="Microglia regulate synaptic plasticity",
                authors=["Smith J."],
                year=2024,
            )
        ]
        entries = build_bib_entries_from_consensus(papers)
        assert len(entries) == 1
        assert entries[0].cite_key == "smith2024microglia"

    def test_handles_comma_first_author_format(self) -> None:
        # "Doe, J." vs. "J. Doe" must both surface "doe" as the surname.
        papers = [
            _make_paper(
                title="Rho GTPase pulsing",
                authors=["Doe, John"],
                year=2023,
            )
        ]
        entries = build_bib_entries_from_consensus(papers)
        assert entries[0].cite_key.startswith("doe2023")

    def test_dedup_against_existing_keys(self) -> None:
        papers = [_make_paper(title="Microglia synaptic plasticity")]
        entries = build_bib_entries_from_consensus(
            papers,
            existing_keys={"smith2024microglia"},
        )
        # Must NOT collide with the existing key.
        assert entries[0].cite_key != "smith2024microglia"
        assert entries[0].cite_key == "smith2024microgliaa"

    def test_dedup_handles_consecutive_collisions(self) -> None:
        papers = [
            _make_paper(title="Synaptic plasticity", authors=["Smith J."]),
            _make_paper(title="Synaptic pruning", authors=["Smith J."]),
            _make_paper(title="Synaptic scaling", authors=["Smith J."]),
        ]
        entries = build_bib_entries_from_consensus(papers)
        keys = [e.cite_key for e in entries]
        assert len(set(keys)) == 3  # all unique

    def test_skips_paper_with_empty_title(self) -> None:
        papers = [
            _make_paper(title=""),
            _make_paper(title="Real paper", authors=["Alpha A."]),
        ]
        entries = build_bib_entries_from_consensus(papers)
        assert len(entries) == 1
        assert "real" in entries[0].cite_key

    def test_bibtex_rendering_includes_required_fields(self) -> None:
        papers = [
            _make_paper(
                title="A & B test paper",
                authors=["Doe J.", "Roe K."],
                year=2024,
                journal="Cell",
                doi="10.1016/j.cell.2024.demo",
            )
        ]
        entries = build_bib_entries_from_consensus(papers)
        bib = entries[0].to_bibtex()
        assert bib.startswith("@article{")
        assert "title = {A \\& B test paper}" in bib
        assert "author = {Doe J. and Roe K.}" in bib
        assert "journal = {Cell}" in bib
        assert "year = {2024}" in bib
        assert "doi = {10.1016/j.cell.2024.demo}" in bib

    def test_year_extracted_from_string(self) -> None:
        papers = [
            _make_paper(title="Demo work", authors=["Alpha A."]),
        ]
        papers[0]["year"] = "Published in 2022"
        entries = build_bib_entries_from_consensus(papers)
        assert entries[0].fields["year"] == "2022"


# --------------------------------------------------------------------------- #
# 3. suggest_citations_for_manuscript                                         #
# --------------------------------------------------------------------------- #


def _write_manuscript(
    tmp_path: Path,
    *,
    body: str,
    name: str = "main.tex",
) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


_DEMO_LATEX = r"""\documentclass{article}
\begin{document}
\section{Results}
Microglia regulate synaptic plasticity in the cortex \ref{fig:1}.
Rho GTPase activation pulses during cell migration \ref{fig:2}.
Figure 1 shows the distribution of cell counts.
\begin{figure}
\includegraphics{fig1.png}
\caption{Microglia panel.}
\label{fig:1}
\end{figure}
\begin{figure}
\includegraphics{fig2.png}
\caption{Rho panel.}
\label{fig:2}
\end{figure}
\end{document}
"""


class TestSuggestPipeline:
    def test_dry_run_with_no_cache_yields_no_suggestions(
        self, tmp_path: Path
    ) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        result = suggest_citations_for_manuscript(
            ms, cache_dir=tmp_path / "no_cache_here"
        )
        assert result.n_suggestions == 0
        assert result.n_applied == 0
        assert result.n_sentences_scanned >= 1

    def test_suggests_when_cache_matches_claim(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[
                _make_paper(title="Microglia regulate synaptic plasticity"),
                _make_paper(
                    title="Synaptic plasticity in cortex",
                    authors=["Alpha B."],
                ),
            ],
        )
        result = suggest_citations_for_manuscript(ms, min_similarity=0.3)
        assert result.n_suggestions >= 1
        assert len(result.new_bib_entries) >= 1
        first = result.suggestions[0]
        assert first.confidence > 0.0
        assert len(first.cite_keys) >= 1

    def test_min_similarity_filters_low_matches(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="unrelated",
            query="quasar redshift cosmology supernova",
            papers=[
                _make_paper(
                    title="Quasar redshift survey",
                    authors=["Zeta Z."],
                )
            ],
        )
        # With min_similarity=0.99 the irrelevant cache shouldn't match.
        result = suggest_citations_for_manuscript(ms, min_similarity=0.99)
        assert result.n_suggestions == 0

    def test_skips_sentences_with_existing_cite(self, tmp_path: Path) -> None:
        body = r"""\documentclass{article}
\begin{document}
Microglia regulate synaptic plasticity \cite{existing2020} \ref{fig:1}.
\begin{figure}
\caption{Demo.}
\label{fig:1}
\end{figure}
\end{document}
"""
        ms = _write_manuscript(tmp_path, body=body)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[_make_paper()],
        )
        result = suggest_citations_for_manuscript(ms, min_similarity=0.3)
        assert result.n_suggestions == 0

    def test_dedup_against_existing_bib(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[_make_paper(authors=["Smith J."], year=2024)],
        )
        bib = tmp_path / "references.bib"
        bib.write_text(
            "@article{smith2024microglia,\n"
            "  title = {Old},\n"
            "  author = {Smith J.},\n"
            "  year = {2024}\n}\n",
            encoding="utf-8",
        )
        result = suggest_citations_for_manuscript(
            ms,
            min_similarity=0.3,
            existing_bib_path=bib,
        )
        keys = [e.cite_key for e in result.new_bib_entries]
        # The generator must avoid the pre-existing key.
        assert "smith2024microglia" not in keys

    def test_top_n_limits_cite_count(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[
                _make_paper(
                    title=f"Microglia paper {i}",
                    authors=[f"Auth{i} A."],
                )
                for i in range(10)
            ],
        )
        result = suggest_citations_for_manuscript(
            ms, min_similarity=0.3, top_n_papers=2,
        )
        if result.suggestions:
            assert len(result.suggestions[0].cite_keys) == 2

    def test_unparseable_manuscript_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "garbage.xyz"
        bad.write_text("totally not a recognisable manuscript", encoding="utf-8")
        with pytest.raises(InserterError):
            suggest_citations_for_manuscript(bad)


# --------------------------------------------------------------------------- #
# 4. apply_citation_insertions                                                #
# --------------------------------------------------------------------------- #


class TestApplyInsertions:
    def test_inserts_cite_before_period(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        line_idx = 3  # 0-indexed → 1-indexed line 4
        line = ms.read_text(encoding="utf-8").splitlines()[line_idx]
        # Sentence ends in '.'; offset must point to the period.
        offset = len(line.rstrip()) - 1
        sug = CitationSuggestion(
            sentence="Microglia regulate synaptic plasticity in the cortex.",
            line_number=line_idx + 1,
            char_offset=offset,
            cite_keys=("smith2024microglia",),
            confidence=0.9,
            rationale="demo",
        )
        bib_entry = BibEntry(
            entry_type="article",
            cite_key="smith2024microglia",
            fields={"title": "Demo", "author": "Smith J.", "year": "2024"},
        )
        ms_out, bib_out = apply_citation_insertions(
            ms, [sug], [bib_entry], backup=True,
        )
        assert ms_out == ms
        modified = ms.read_text(encoding="utf-8")
        assert r"\cite{smith2024microglia}" in modified
        # Order: text + cite + period
        assert modified.find(r"\cite{smith2024microglia}") < modified.find(
            "ref{fig:1}.\n"
        ) + 1000  # sanity
        # Citation must appear BEFORE the period of the target sentence.
        target_idx = modified.find("synaptic plasticity in the cortex")
        period_idx = modified.find(".", target_idx)
        cite_idx = modified.find(r"\cite{smith2024microglia}", target_idx)
        assert target_idx < cite_idx < period_idx

    def test_backup_manuscript_created(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        sug = CitationSuggestion(
            sentence="X.",
            line_number=1,
            char_offset=0,
            cite_keys=("k",),
            confidence=1.0,
            rationale="demo",
        )
        bib_entry = BibEntry(
            entry_type="article",
            cite_key="k",
            fields={"title": "T"},
        )
        apply_citation_insertions(ms, [sug], [bib_entry], backup=True)
        backups = list(tmp_path.glob("main.tex.bak*"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == _DEMO_LATEX

    def test_no_backup_when_flag_false(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        sug = CitationSuggestion(
            sentence="X.",
            line_number=1,
            char_offset=0,
            cite_keys=("k",),
            confidence=1.0,
            rationale="demo",
        )
        bib_entry = BibEntry(
            entry_type="article", cite_key="k", fields={"title": "T"},
        )
        apply_citation_insertions(ms, [sug], [bib_entry], backup=False)
        backups = list(tmp_path.glob("main.tex.bak*"))
        assert backups == []

    def test_multiple_suggestions_preserve_offsets(self, tmp_path: Path) -> None:
        # Two suggestions on the same line — applying the rightmost first
        # must keep the leftmost's offset valid.
        body = "A very long sentence one. A very long sentence two.\n"
        ms = tmp_path / "main.tex"
        ms.write_text(body, encoding="utf-8")
        # Sentence 1 ends at offset 24 (period); sentence 2 at offset 49.
        idx1 = body.index("one.") + 3  # position of '.'
        idx2 = body.index("two.") + 3  # position of '.'
        sugs = [
            CitationSuggestion(
                sentence="A very long sentence one.",
                line_number=1,
                char_offset=idx1,
                cite_keys=("a2024",),
                confidence=0.8,
                rationale="d",
            ),
            CitationSuggestion(
                sentence="A very long sentence two.",
                line_number=1,
                char_offset=idx2,
                cite_keys=("b2024",),
                confidence=0.8,
                rationale="d",
            ),
        ]
        bibs = [
            BibEntry(entry_type="article", cite_key="a2024", fields={"title": "A"}),
            BibEntry(entry_type="article", cite_key="b2024", fields={"title": "B"}),
        ]
        apply_citation_insertions(ms, sugs, bibs, backup=False)
        out = ms.read_text(encoding="utf-8")
        # Both citations must be present
        assert r"\cite{a2024}" in out
        assert r"\cite{b2024}" in out
        # Each cite must appear AFTER 'one'/'two' and BEFORE the
        # next period. Search positions inside the rendered output.
        one_word = out.find("one")
        a_pos = out.find(r"\cite{a2024}")
        # The period of sentence 1 sits immediately after \cite{a2024}.
        a_close = a_pos + len(r"\cite{a2024}")
        assert one_word < a_pos
        assert out[a_close] == "."

        two_word = out.find("two")
        b_pos = out.find(r"\cite{b2024}")
        b_close = b_pos + len(r"\cite{b2024}")
        assert two_word < b_pos
        assert out[b_close] == "."

    def test_appends_bib_when_file_exists(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        bib = tmp_path / "references.bib"
        bib.write_text(
            "@article{prior2020work,\n  title = {Prior},\n  year = {2020}\n}\n",
            encoding="utf-8",
        )
        sug = CitationSuggestion(
            sentence="X.",
            line_number=1,
            char_offset=0,
            cite_keys=("new2024",),
            confidence=0.9,
            rationale="d",
        )
        new = BibEntry(
            entry_type="article",
            cite_key="new2024",
            fields={"title": "New work", "year": "2024"},
        )
        apply_citation_insertions(
            ms, [sug], [new], existing_bib_path=bib, backup=True,
        )
        out = bib.read_text(encoding="utf-8")
        assert "prior2020work" in out
        assert "new2024" in out
        backups = list(tmp_path.glob("references.bib.bak*"))
        assert len(backups) == 1

    def test_skips_duplicate_bib_entries(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        bib = tmp_path / "references.bib"
        bib.write_text(
            "@article{dup2024,\n  title = {Existing},\n  year = {2024}\n}\n",
            encoding="utf-8",
        )
        sug = CitationSuggestion(
            sentence="X.",
            line_number=1,
            char_offset=0,
            cite_keys=("dup2024",),
            confidence=0.9,
            rationale="d",
        )
        new = BibEntry(
            entry_type="article",
            cite_key="dup2024",
            fields={"title": "Duplicate", "year": "2024"},
        )
        apply_citation_insertions(
            ms, [sug], [new], existing_bib_path=bib, backup=False,
        )
        out = bib.read_text(encoding="utf-8")
        # Should NOT have appended a second entry; only the original
        # "Existing" body is present (we'd see "Duplicate" if it had).
        assert "Duplicate" not in out
        assert "Existing" in out

    def test_creates_bib_when_missing(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        bib = tmp_path / "references.bib"
        assert not bib.exists()
        sug = CitationSuggestion(
            sentence="X.",
            line_number=1,
            char_offset=0,
            cite_keys=("fresh2024",),
            confidence=0.9,
            rationale="d",
        )
        new = BibEntry(
            entry_type="article",
            cite_key="fresh2024",
            fields={"title": "Fresh", "year": "2024"},
        )
        apply_citation_insertions(
            ms, [sug], [new], existing_bib_path=bib, backup=True,
        )
        assert bib.exists()
        assert "fresh2024" in bib.read_text(encoding="utf-8")

    def test_out_of_bounds_line_raises(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body="only one line.\n")
        sug = CitationSuggestion(
            sentence="x",
            line_number=99,
            char_offset=0,
            cite_keys=("k",),
            confidence=1.0,
            rationale="d",
        )
        with pytest.raises(InserterError):
            apply_citation_insertions(
                ms, [sug], [], backup=False,
            )


# --------------------------------------------------------------------------- #
# 5. render_suggestions_markdown                                              #
# --------------------------------------------------------------------------- #


class TestRenderMarkdown:
    def test_renders_empty_result(self, tmp_path: Path) -> None:
        result = CitationInsertionResult(
            manuscript_path=tmp_path / "m.tex",
            n_sentences_scanned=0,
            n_suggestions=0,
            n_applied=0,
            new_bib_entries=(),
            suggestions=(),
            backup_manuscript_path=None,
            backup_bib_path=None,
        )
        out = render_suggestions_markdown(result)
        assert "Citation Suggestions" in out
        assert "No suggestions" in out

    def test_renders_with_suggestions(self, tmp_path: Path) -> None:
        sug = CitationSuggestion(
            sentence="Microglia regulate synaptic plasticity.",
            line_number=12,
            char_offset=38,
            cite_keys=("smith2024microglia", "doe2023synapse"),
            confidence=0.84,
            rationale="cached query match",
        )
        entry = BibEntry(
            entry_type="article",
            cite_key="smith2024microglia",
            fields={
                "title": "Microglia",
                "author": "Smith J.",
                "year": "2024",
            },
        )
        result = CitationInsertionResult(
            manuscript_path=tmp_path / "m.tex",
            n_sentences_scanned=10,
            n_suggestions=1,
            n_applied=0,
            new_bib_entries=(entry,),
            suggestions=(sug,),
            backup_manuscript_path=None,
            backup_bib_path=None,
        )
        out = render_suggestions_markdown(result)
        assert "smith2024microglia" in out
        assert "doe2023synapse" in out
        assert "0.84" in out
        assert "@article" in out  # BibTeX preview block


# --------------------------------------------------------------------------- #
# 6. CLI smoke                                                                #
# --------------------------------------------------------------------------- #


class TestCLI:
    def test_help_works(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["cite", "--help"])
        assert result.exit_code == 0
        assert "citation" in result.output.lower()

    def test_suggest_help_works(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["cite", "suggest", "--help"])
        assert result.exit_code == 0
        assert "consensus" in result.output.lower()

    def test_dry_run_emits_markdown(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[_make_paper()],
        )
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "cite", "suggest",
                str(ms),
                "--min-similarity", "0.2",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Citation Suggestions" in result.output

    def test_dry_run_emits_json(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[_make_paper()],
        )
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "cite", "suggest",
                str(ms),
                "--min-similarity", "0.2",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        # Find the JSON in the output.
        start = result.output.find("{")
        end = result.output.rfind("}")
        assert start != -1 and end != -1
        payload = json.loads(result.output[start:end + 1])
        assert "suggestions" in payload
        assert "new_bib_entries" in payload
        assert payload["n_applied"] == 0

    def test_apply_modifies_files(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        cache = tmp_path / "panelforge_workspace" / ".consensus_cache"
        _write_cache_entry(
            cache,
            name="microglia",
            query="microglia regulate synaptic plasticity",
            papers=[_make_paper()],
        )
        bib = tmp_path / "references.bib"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "cite", "suggest",
                str(ms),
                "--min-similarity", "0.2",
                "--apply",
                "--bib-path", str(bib),
            ],
        )
        assert result.exit_code == 0, result.output
        # The manuscript must now contain at least one \cite{} marker.
        assert r"\cite{" in ms.read_text(encoding="utf-8")
        # The bib file must exist + have at least one entry.
        assert bib.exists()
        assert "@article" in bib.read_text(encoding="utf-8")

    def test_output_path_writes_file(self, tmp_path: Path) -> None:
        ms = _write_manuscript(tmp_path, body=_DEMO_LATEX)
        out = tmp_path / "report.md"
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["cite", "suggest", str(ms), "--output", str(out)],
        )
        assert result.exit_code == 0
        assert out.exists()


# --------------------------------------------------------------------------- #
# 7. CACHE_DIR_DEFAULT export                                                 #
# --------------------------------------------------------------------------- #


def test_cache_dir_default_exported() -> None:
    assert CACHE_DIR_DEFAULT == "panelforge_workspace/.consensus_cache"
