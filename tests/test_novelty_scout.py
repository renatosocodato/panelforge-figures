"""Tests for E9 — literature-novelty scout."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
import yaml
from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.novelty_scout import (
    ConsensusAPIError,
    ConsensusPaper,
    ConsensusProClient,
    ConsensusSearchResult,
    ConsensusUnavailableError,
    FigurePlanNoveltyReport,
    MockConsensusClient,
    NoveltyClass,
    NoveltyThresholds,
    PanelCandidate,
    PanelRole,
    TargetNovelty,
    assess_panel_novelty,
    build_consensus_query,
    classify_novelty,
    is_supporting_panel,
    render_markdown_report,
    score_figure_plan,
)

# ─────────────────── helpers ───────────────────

def _result(
    *,
    n: int = 0,
    consensus: float = 0.0,
    avg_year: float | None = None,
    papers: tuple[ConsensusPaper, ...] = (),
    meter: str | None = None,
    query: str = "q",
) -> ConsensusSearchResult:
    return ConsensusSearchResult(
        query=query,
        n_matching_papers=n,
        consensus_meter=meter,
        consensus_strength=consensus,
        avg_year=avg_year,
        top_papers=papers,
    )


def _paper(title: str = "Demo paper", year: int = 2024) -> ConsensusPaper:
    return ConsensusPaper(
        title=title,
        authors=("Doe J.",),
        year=year,
        journal="J. Demo",
        doi=f"10.1000/{title.lower().replace(' ', '_')}",
        abstract_excerpt="Background: ...",
        relevance_score=0.85,
    )


# ─────────────────── 1. classify_novelty decision matrix ───────────────────


class TestClassifyNovelty:
    def test_repetition_when_many_papers_strong_consensus(self) -> None:
        r = _result(n=20, consensus=0.8, avg_year=2022.0)
        assert classify_novelty(r) == NoveltyClass.repetition

    def test_repetition_at_exact_threshold(self) -> None:
        r = _result(n=15, consensus=0.75, avg_year=2022.0)
        assert classify_novelty(r) == NoveltyClass.repetition

    def test_incremental_when_partial_overlap(self) -> None:
        r = _result(n=8, consensus=0.6, avg_year=2022.0)
        assert classify_novelty(r) == NoveltyClass.incremental

    def test_incremental_at_exact_threshold(self) -> None:
        r = _result(n=5, consensus=0.5, avg_year=2022.0)
        assert classify_novelty(r) == NoveltyClass.incremental

    def test_zero_papers_is_ultra_novelty(self) -> None:
        r = _result(n=0)
        assert classify_novelty(r) == NoveltyClass.ultra_novelty

    def test_old_lone_paper_is_ultra_novelty(self) -> None:
        # 1 paper from 2018 with current_year=2026 → 8 yrs old → ultra
        r = _result(n=1, consensus=0.0, avg_year=2018.0)
        assert classify_novelty(r) == NoveltyClass.ultra_novelty

    def test_recent_lone_paper_is_hidden_novelty(self) -> None:
        # 1 paper from 2024 (recent niche) → hidden, not ultra
        r = _result(n=1, consensus=0.0, avg_year=2024.0)
        assert classify_novelty(r) == NoveltyClass.hidden_novelty

    def test_few_papers_weak_consensus_is_hidden_novelty(self) -> None:
        # 3 papers, consensus 0.3 → fails repetition + incremental, not 0,
        # avg_year too recent → hidden_novelty
        r = _result(n=3, consensus=0.3, avg_year=2024.0)
        assert classify_novelty(r) == NoveltyClass.hidden_novelty

    def test_many_papers_weak_consensus_falls_through(self) -> None:
        # 20 papers but consensus 0.4 < 0.75 → not repetition.
        # 20 papers + consensus 0.4 < 0.5 → not incremental.
        # → hidden_novelty
        r = _result(n=20, consensus=0.4, avg_year=2022.0)
        assert classify_novelty(r) == NoveltyClass.hidden_novelty

    def test_two_papers_old_avg_year_is_ultra(self) -> None:
        # n=2 (<= ultra_max_papers=2), avg_year=2018 → 8yr old → ultra
        r = _result(n=2, consensus=0.0, avg_year=2018.0)
        assert classify_novelty(r) == NoveltyClass.ultra_novelty

    def test_custom_thresholds_override(self) -> None:
        # tighter thresholds for a stricter scout
        strict = NoveltyThresholds(
            repetition_min_papers=10,
            repetition_min_consensus=0.6,
            current_year=2026,
        )
        r = _result(n=10, consensus=0.6, avg_year=2022.0)
        assert classify_novelty(r, thresholds=strict) == NoveltyClass.repetition
        # under default thresholds the same data is incremental
        assert classify_novelty(r) == NoveltyClass.incremental


# ─────────────────── 2. is_supporting_panel ───────────────────


class TestIsSupportingPanel:
    def test_explicit_supporting_role(self) -> None:
        assert is_supporting_panel(
            "actin_microtubule_morphometry.actin_filament_density",
            explicit_role=PanelRole.supporting,
        )

    def test_explicit_methodology_role(self) -> None:
        assert is_supporting_panel(
            "anything.whatever",
            explicit_role=PanelRole.methodology,
        )

    def test_meta_and_diagnostic_modality_is_supporting(self) -> None:
        assert is_supporting_panel(
            "meta_and_diagnostic.bayes_factor_arrow_plot",
            modality="meta_and_diagnostic",
        )

    def test_modality_check_is_case_insensitive(self) -> None:
        assert is_supporting_panel(
            "anything.foo",
            modality="META_AND_DIAGNOSTIC",
        )

    def test_recipe_name_with_provenance_is_supporting(self) -> None:
        assert is_supporting_panel(
            "some_modality.panel_provenance_ledger_table",
        )

    def test_recipe_name_with_control_is_supporting(self) -> None:
        assert is_supporting_panel(
            "some_modality.negative_control_baseline_panel",
        )

    def test_recipe_name_with_baseline_is_supporting(self) -> None:
        assert is_supporting_panel(
            "some_modality.measurement_baseline_distribution",
        )

    def test_recipe_name_with_qc_is_supporting(self) -> None:
        assert is_supporting_panel(
            "some_modality.batch_qc_summary",
        )

    def test_recipe_name_with_calibration_is_supporting(self) -> None:
        assert is_supporting_panel(
            "some_modality.intensity_calibration_curve",
        )

    def test_random_recipe_with_auto_role_is_not_supporting(self) -> None:
        assert not is_supporting_panel(
            "actin_microtubule_morphometry.actin_filament_density",
            explicit_role=PanelRole.auto,
        )

    def test_primary_role_does_not_force_protection(self) -> None:
        # primary role + non-protected name → False
        assert not is_supporting_panel(
            "rhogtpase_dynamics.activation_pulse_train",
            explicit_role=PanelRole.primary,
        )


# ─────────────────── 3. MockConsensusClient ───────────────────


class TestMockConsensusClient:
    def test_records_calls(self) -> None:
        client = MockConsensusClient()
        client.search("q1")
        client.search("q2")
        assert client.calls == ["q1", "q2"]

    def test_returns_preloaded_results(self) -> None:
        preset = _result(query="known", n=42, consensus=0.9)
        client = MockConsensusClient(results_by_query={"known": preset})
        out = client.search("known")
        assert out.n_matching_papers == 42
        assert out.consensus_strength == pytest.approx(0.9)

    def test_falls_back_to_default(self) -> None:
        client = MockConsensusClient()
        out = client.search("unknown_query")
        assert out.n_matching_papers == 0
        assert out.top_papers == ()

    def test_custom_default(self) -> None:
        custom_default = _result(query="default", n=5, consensus=0.7)
        client = MockConsensusClient(default=custom_default)
        out = client.search("anything")
        assert out.n_matching_papers == 5


# ─────────────────── 4. assess_panel_novelty ───────────────────


class TestAssessPanelNovelty:
    @staticmethod
    def _panel(
        recipe: str = "rhogtpase_dynamics.activation_pulse_train",
        question: str = "Does RhoGTPase activation pulse rhythmically?",
        role: PanelRole = PanelRole.auto,
        modality: str | None = None,
    ) -> PanelCandidate:
        return PanelCandidate(
            panel_id="p1",
            recipe_full_name=recipe,
            research_question=question,
            role=role,
            modality=modality,
        )

    def test_supporting_panel_with_repetition_keeps_protected(self) -> None:
        panel = self._panel(
            recipe="meta_and_diagnostic.panel_provenance_ledger_table",
            modality="meta_and_diagnostic",
        )
        client = MockConsensusClient(
            default=_result(n=50, consensus=0.95, avg_year=2018.0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.maximal)
        assert a.is_supporting is True
        assert a.suggestion == "keep_protected"
        assert "supporting" in a.rationale.lower()

    def test_non_supporting_repetition_maximal_drops(self) -> None:
        panel = self._panel()
        client = MockConsensusClient(
            default=_result(n=50, consensus=0.95, avg_year=2020.0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.maximal)
        assert a.is_supporting is False
        assert a.novelty_class == NoveltyClass.repetition
        assert a.suggestion == "drop"

    def test_non_supporting_repetition_balanced_demotes(self) -> None:
        panel = self._panel()
        client = MockConsensusClient(
            default=_result(n=50, consensus=0.95, avg_year=2020.0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.balanced)
        assert a.suggestion == "demote_to_supplementary"

    def test_non_supporting_repetition_permissive_informational(self) -> None:
        panel = self._panel()
        client = MockConsensusClient(
            default=_result(n=50, consensus=0.95, avg_year=2020.0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.permissive)
        assert a.suggestion == "informational"

    def test_non_supporting_ultra_novelty_promotes(self) -> None:
        panel = self._panel()
        client = MockConsensusClient(
            default=_result(n=0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.maximal)
        assert a.novelty_class == NoveltyClass.ultra_novelty
        assert a.suggestion == "promote"

    def test_non_supporting_incremental_maximal_demotes(self) -> None:
        panel = self._panel()
        client = MockConsensusClient(
            default=_result(n=8, consensus=0.6, avg_year=2022.0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.maximal)
        assert a.suggestion == "demote_to_supplementary"

    def test_non_supporting_hidden_novelty_keeps_with_flag(self) -> None:
        panel = self._panel()
        client = MockConsensusClient(
            default=_result(n=2, consensus=0.3, avg_year=2024.0),
        )
        a = assess_panel_novelty(panel, client, target=TargetNovelty.maximal)
        assert a.novelty_class == NoveltyClass.hidden_novelty
        assert a.suggestion == "keep_flag_opportunity"

    def test_assessment_includes_top_paper_titles(self) -> None:
        panel = self._panel()
        papers = (
            _paper("Paper A"),
            _paper("Paper B"),
            _paper("Paper C"),
            _paper("Paper D"),
        )
        client = MockConsensusClient(
            default=_result(n=4, consensus=0.4, avg_year=2024.0, papers=papers),
        )
        a = assess_panel_novelty(panel, client)
        assert a.top_paper_titles == ("Paper A", "Paper B", "Paper C")

    def test_assessment_propagates_target(self) -> None:
        panel = self._panel()
        client = MockConsensusClient()
        a = assess_panel_novelty(panel, client, target=TargetNovelty.balanced)
        assert a.target_novelty == TargetNovelty.balanced


# ─────────────────── 5. score_figure_plan ───────────────────


class TestScoreFigurePlan:
    @staticmethod
    def _ultra_panel(idx: int) -> PanelCandidate:
        return PanelCandidate(
            panel_id=f"ultra-{idx}",
            recipe_full_name=f"some_modality.novel_panel_{idx}",
            research_question=f"Genuinely novel claim {idx}",
        )

    @staticmethod
    def _rep_panel(idx: int) -> PanelCandidate:
        return PanelCandidate(
            panel_id=f"rep-{idx}",
            recipe_full_name=f"some_modality.well_known_panel_{idx}",
            research_question=f"Well-established claim {idx}",
        )

    @staticmethod
    def _supporting_panel(idx: int) -> PanelCandidate:
        return PanelCandidate(
            panel_id=f"sup-{idx}",
            recipe_full_name=f"meta_and_diagnostic.panel_provenance_ledger_{idx}",
            research_question=f"Supporting QC {idx}",
            modality="meta_and_diagnostic",
        )

    def test_all_ultra_yields_ultra_rich(self) -> None:
        panels = [self._ultra_panel(i) for i in range(5)]
        client = MockConsensusClient(default=_result(n=0))
        report = score_figure_plan(panels, client)
        assert report.overall_verdict == "ultra-rich"
        assert report.n_ultra_novelty == 5
        assert report.novelty_density == pytest.approx(1.0)

    def test_all_repetition_yields_repetitive(self) -> None:
        panels = [self._rep_panel(i) for i in range(5)]
        client = MockConsensusClient(
            default=_result(n=50, consensus=0.95, avg_year=2020.0),
        )
        report = score_figure_plan(panels, client)
        assert report.overall_verdict == "repetitive"
        assert report.n_repetition == 5
        assert report.novelty_density == pytest.approx(0.0)

    def test_supporting_panels_excluded_from_density(self) -> None:
        # 3 supporting + 2 ultra = density should be 2/2 = 1.0 (over unprotected)
        panels = [self._supporting_panel(i) for i in range(3)] + \
                 [self._ultra_panel(i) for i in range(2)]
        # supporting panels return repetition (lots of papers), ultra return n=0
        results_by_query = {}
        for i in range(3):
            results_by_query[f"Supporting QC {i}"] = _result(
                n=50, consensus=0.95, avg_year=2020.0,
            )
        for i in range(2):
            results_by_query[f"Genuinely novel claim {i}"] = _result(n=0)
        client = MockConsensusClient(results_by_query=results_by_query)
        report = score_figure_plan(panels, client)
        assert report.n_protected == 3
        assert report.n_ultra_novelty == 2
        # density = (0 hidden + 2 ultra) / max(5-3, 1) = 2/2 = 1.0
        assert report.novelty_density == pytest.approx(1.0)
        # ultra-rich: density >= 0.6 AND ultra >= 30%
        assert report.overall_verdict == "ultra-rich"

    def test_promote_drop_demote_lists(self) -> None:
        # Mix: 1 ultra (promote), 1 rep (drop on maximal), 1 incremental (demote)
        panels = [
            self._ultra_panel(1),
            self._rep_panel(1),
            PanelCandidate(
                panel_id="inc-1",
                recipe_full_name="some_modality.incremental_panel",
                research_question="Incremental claim",
            ),
        ]
        results_by_query = {
            "Genuinely novel claim 1": _result(n=0),
            "Well-established claim 1": _result(
                n=50, consensus=0.95, avg_year=2020.0,
            ),
            "Incremental claim": _result(n=8, consensus=0.6, avg_year=2022.0),
        }
        client = MockConsensusClient(results_by_query=results_by_query)
        report = score_figure_plan(panels, client, target=TargetNovelty.maximal)
        assert "ultra-1" in report.promote_panels
        assert "rep-1" in report.drop_panels
        assert "inc-1" in report.demote_panels

    def test_balanced_keeps_incremental(self) -> None:
        panels = [self._rep_panel(1), self._rep_panel(2), self._ultra_panel(1)]
        results_by_query = {
            "Well-established claim 1": _result(
                n=50, consensus=0.95, avg_year=2020.0,
            ),
            "Well-established claim 2": _result(
                n=50, consensus=0.95, avg_year=2020.0,
            ),
            "Genuinely novel claim 1": _result(n=0),
        }
        client = MockConsensusClient(results_by_query=results_by_query)
        report = score_figure_plan(panels, client, target=TargetNovelty.balanced)
        # On balanced, repetition is demoted, not dropped
        assert "rep-1" in report.demote_panels
        assert "rep-2" in report.demote_panels
        assert report.drop_panels == ()

    def test_to_dict_roundtrip(self) -> None:
        panels = [self._ultra_panel(1)]
        client = MockConsensusClient(default=_result(n=0))
        report = score_figure_plan(panels, client)
        d = report.to_dict()
        # JSON-roundtrippable
        roundtrip = json.loads(json.dumps(d))
        assert roundtrip["overall_verdict"] == report.overall_verdict
        assert roundtrip["n_panels"] == 1


# ─────────────────── 6. build_consensus_query ───────────────────


class TestBuildConsensusQuery:
    def test_strips_question_mark(self) -> None:
        p = PanelCandidate(
            panel_id="p",
            recipe_full_name="m.r",
            research_question="Does X cause Y?",
        )
        assert build_consensus_query(p) == "Does X cause Y"

    def test_strips_trailing_period(self) -> None:
        p = PanelCandidate(
            panel_id="p",
            recipe_full_name="m.r",
            research_question="X causes Y.",
        )
        assert build_consensus_query(p) == "X causes Y"

    def test_strips_trailing_exclamation(self) -> None:
        p = PanelCandidate(
            panel_id="p",
            recipe_full_name="m.r",
            research_question="Eureka!",
        )
        assert build_consensus_query(p) == "Eureka"

    def test_joins_extra_terms_with_AND(self) -> None:
        p = PanelCandidate(
            panel_id="p",
            recipe_full_name="m.r",
            research_question="Does X cause Y?",
            extra_query_terms=("microglia", "in vivo"),
        )
        assert build_consensus_query(p) == "Does X cause Y AND microglia AND in vivo"

    def test_empty_extras_returns_bare_question(self) -> None:
        p = PanelCandidate(
            panel_id="p",
            recipe_full_name="m.r",
            research_question="Does X cause Y",
            extra_query_terms=(),
        )
        assert build_consensus_query(p) == "Does X cause Y"


# ─────────────────── 7. ConsensusProClient ───────────────────


class TestConsensusProClient:
    def test_raises_when_no_api_key_no_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        with pytest.raises(ConsensusUnavailableError):
            ConsensusProClient()

    def test_uses_explicit_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    def test_uses_env_var_when_no_explicit_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CONSENSUS_API_KEY", "env-key")
        client = ConsensusProClient()
        assert client.api_key == "env-key"

    def test_explicit_key_overrides_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CONSENSUS_API_KEY", "env-key")
        client = ConsensusProClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"

    def test_custom_endpoint(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(
            api_key="k", endpoint_url="https://custom.example/api/v2",
        )
        assert client.endpoint_url == "https://custom.example/api/v2"

    def test_parse_response_handles_missing_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(api_key="k")
        # Sparse / minimal response
        result = client._parse_response("q", {})
        assert result.n_matching_papers == 0
        assert result.consensus_strength == 0.0
        assert result.top_papers == ()
        assert result.avg_year is None

    def test_parse_response_handles_full_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(api_key="k")
        data = {
            "query": "q",
            "n_matching_papers": 42,
            "consensus": {"meter": "yes", "strength": 0.78},
            "papers": [
                {
                    "title": "Rho activation pulses",
                    "authors": ["Doe J.", "Smith K."],
                    "year": 2024,
                    "journal": "Nat. Cell Biol.",
                    "doi": "10.1038/s41556-024-12345",
                    "abstract": "We show that Rho activation is pulsatile...",
                    "relevance": 0.91,
                },
                {
                    "title": "RhoA dynamics",
                    "authors": ["Lee R."],
                    "year": 2022,
                    "journal": "Cell",
                    "doi": "10.1016/j.cell.2022.99",
                    "abstract": "RhoA dynamics review...",
                    "relevance": 0.85,
                },
            ],
        }
        result = client._parse_response("q", data)
        assert result.n_matching_papers == 42
        assert result.consensus_meter == "yes"
        assert result.consensus_strength == pytest.approx(0.78)
        assert len(result.top_papers) == 2
        assert result.top_papers[0].title == "Rho activation pulses"
        assert result.top_papers[0].authors == ("Doe J.", "Smith K.")
        assert result.avg_year == pytest.approx(2023.0)

    def test_parse_response_truncates_abstracts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(api_key="k")
        long_abstract = "A" * 1000
        data = {
            "papers": [
                {"title": "T", "abstract": long_abstract, "year": 2024},
            ],
        }
        result = client._parse_response("q", data)
        assert len(result.top_papers[0].abstract_excerpt) == 400

    def test_search_raises_consensus_unavailable_if_requests_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(api_key="k")
        # Pretend `requests` import fails
        with mock.patch.dict("sys.modules", {"requests": None}):
            with pytest.raises(ConsensusUnavailableError):
                client.search("q")


# ─────────────────── 8. render_markdown_report ───────────────────


class TestRenderMarkdownReport:
    def _make_report(self) -> FigurePlanNoveltyReport:
        panels = [
            PanelCandidate(
                panel_id="panel-1A",
                recipe_full_name="biophysics_scaling.compartment_paired_delta_scatter",
                research_question="Does compartment effect size differ from whole-cell?",
            ),
            PanelCandidate(
                panel_id="panel-2B",
                recipe_full_name="meta_and_diagnostic.panel_provenance_ledger_table",
                research_question="Provenance summary",
                modality="meta_and_diagnostic",
            ),
        ]
        client = MockConsensusClient(default=_result(n=0))
        return score_figure_plan(panels, client)

    def test_contains_title(self) -> None:
        text = render_markdown_report(self._make_report())
        assert "# Novelty Scout Report" in text

    def test_contains_verdict(self) -> None:
        text = render_markdown_report(self._make_report())
        # The exact verdict depends on the data, but it must appear
        report = self._make_report()
        assert report.overall_verdict in text

    def test_lists_all_panels(self) -> None:
        text = render_markdown_report(self._make_report())
        assert "panel-1A" in text
        assert "panel-2B" in text

    def test_distribution_table_well_formed(self) -> None:
        text = render_markdown_report(self._make_report())
        assert "## Distribution" in text
        assert "ultra-novelty" in text
        assert "hidden-novelty" in text
        assert "incremental" in text
        assert "repetition" in text
        assert "(supporting)" in text

    def test_ultra_novelty_panel_has_promote_suggestion(self) -> None:
        text = render_markdown_report(self._make_report())
        # panel-1A is ultra (n=0); should be tagged for promote
        assert "promote" in text

    def test_supporting_panel_marked_protected(self) -> None:
        text = render_markdown_report(self._make_report())
        assert "supporting-protected" in text or "keep_protected" in text

    def test_includes_distribution_count(self) -> None:
        text = render_markdown_report(self._make_report())
        # Counts table has at least one row matching `| ... | <int> |` format
        import re
        rows = re.findall(r"\|\s+\S[^|]+\|\s+\d+\s+\|", text)
        assert len(rows) >= 5  # ultra, hidden, incremental, repetition, supporting

    def test_no_action_section_when_no_changes(self) -> None:
        # All-supporting plan: only keep_protected, no promote/drop/demote
        panels = [
            PanelCandidate(
                panel_id="p1",
                recipe_full_name="meta_and_diagnostic.panel_provenance_ledger",
                research_question="Provenance",
                modality="meta_and_diagnostic",
            ),
        ]
        client = MockConsensusClient(default=_result(n=50, consensus=0.95))
        report = score_figure_plan(panels, client)
        text = render_markdown_report(report)
        assert "No structural changes" in text


# ─────────────────── 9. CLI smoke ───────────────────


class TestCLI:
    def test_help_works(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["novelty-scout", "--help"])
        assert result.exit_code == 0
        assert "novelty" in result.output.lower()
        assert "consensus" in result.output.lower()

    def test_no_input_exits_1(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["novelty-scout", "--mock"])
        assert result.exit_code == 1
        assert "no panels to assess" in result.output or \
               "no panels to assess" in (result.stderr_bytes or b"").decode()

    def test_candidate_recipe_with_mock_runs(self) -> None:
        # Use a real recipe so the registry lookup succeeds
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "novelty-scout",
                "--candidate-recipe",
                "biophysics_scaling.compartment_paired_delta_scatter",
                "--mock",
            ],
        )
        assert result.exit_code == 0, f"output: {result.output}\nexc: {result.exception}"
        assert "Novelty Scout Report" in result.output

    def test_candidate_recipe_unknown_warns_and_skips(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "novelty-scout",
                "--candidate-recipe",
                "definitely_does_not_exist.fake_recipe",
                "--mock",
            ],
        )
        # No real panels → exit 1
        assert result.exit_code == 1

    def test_from_yaml_with_mock_json(self, tmp_path: Path) -> None:
        yaml_path = tmp_path / "panels.yaml"
        yaml_path.write_text(
            yaml.safe_dump(
                {
                    "panels": [
                        {
                            "panel_id": "p1",
                            "recipe_full_name": "rhogtpase_dynamics.activation_pulse_train",
                            "research_question": "Does Rho pulse?",
                        },
                        {
                            "panel_id": "p2",
                            "recipe_full_name": "meta_and_diagnostic.panel_provenance_ledger_table",
                            "research_question": "Provenance summary",
                            "modality": "meta_and_diagnostic",
                        },
                    ],
                }
            )
        )
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "novelty-scout",
                "--from-yaml", str(yaml_path),
                "--mock",
                "--json",
            ],
        )
        assert result.exit_code == 0, f"output: {result.output}\nexc: {result.exception}"
        # Output should be a valid JSON; the cli emits the JSON to stdout +
        # a stderr summary line, but click's runner combines output. Try to
        # locate JSON within the output.
        # First, attempt strict parse:
        try:
            payload = json.loads(result.output)
        except json.JSONDecodeError:
            # find first { ... } block
            start = result.output.find("{")
            end = result.output.rfind("}")
            assert start != -1 and end != -1
            payload = json.loads(result.output[start:end + 1])
        assert "overall_verdict" in payload
        assert payload["n_panels"] == 2

    def test_target_balanced_via_cli(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "novelty-scout",
                "--candidate-recipe",
                "biophysics_scaling.compartment_paired_delta_scatter",
                "--mock",
                "--target", "balanced",
            ],
        )
        assert result.exit_code == 0

    def test_output_path_writes_file(self, tmp_path: Path) -> None:
        out_path = tmp_path / "report.md"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "novelty-scout",
                "--candidate-recipe",
                "biophysics_scaling.compartment_paired_delta_scatter",
                "--mock",
                "--output", str(out_path),
            ],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        assert "Novelty Scout Report" in out_path.read_text()


# ─────────────────── 10. Suggestion lookup edge cases ───────────────────


class TestSuggestionRouting:
    """Direct tests of the suggestion router for completeness."""

    def test_supporting_overrides_target(self) -> None:
        from panelforge_figures.manifest.novelty_scout import _suggestion_for
        # Even with permissive, supporting wins
        for tgt in TargetNovelty:
            for cls in NoveltyClass:
                assert _suggestion_for(cls, True, tgt) == "keep_protected"

    def test_permissive_never_demotes(self) -> None:
        from panelforge_figures.manifest.novelty_scout import _suggestion_for
        for cls in NoveltyClass:
            assert _suggestion_for(cls, False, TargetNovelty.permissive) == \
                   "informational"

    def test_balanced_promotes_ultra_keeps_others_except_repetition(self) -> None:
        from panelforge_figures.manifest.novelty_scout import _suggestion_for
        assert _suggestion_for(
            NoveltyClass.ultra_novelty, False, TargetNovelty.balanced,
        ) == "promote"
        assert _suggestion_for(
            NoveltyClass.hidden_novelty, False, TargetNovelty.balanced,
        ) == "keep"
        assert _suggestion_for(
            NoveltyClass.incremental, False, TargetNovelty.balanced,
        ) == "keep"
        assert _suggestion_for(
            NoveltyClass.repetition, False, TargetNovelty.balanced,
        ) == "demote_to_supplementary"


# ─────────────────── 11. Consensus client error paths ───────────────────


class TestConsensusErrorPaths:
    def test_consensus_api_error_on_request_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If `requests` is installed but the call raises, ConsensusAPIError fires."""
        try:
            import requests  # noqa: F401
        except ImportError:
            pytest.skip("requests not installed")

        monkeypatch.delenv("CONSENSUS_API_KEY", raising=False)
        client = ConsensusProClient(api_key="k")

        class _BadResponse:
            def raise_for_status(self) -> None:
                import requests as _r
                raise _r.RequestException("simulated network error")

            def json(self) -> dict:  # pragma: no cover
                return {}

        def _fake_post(*a, **kw) -> _BadResponse:
            return _BadResponse()

        import requests as _r
        monkeypatch.setattr(_r, "post", _fake_post)
        with pytest.raises(ConsensusAPIError):
            client.search("q")
