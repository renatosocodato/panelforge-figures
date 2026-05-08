"""Elevation 9 (E9) — literature-novelty scout for figure plans.

Bounds figure-scaffolding plans to maximal-novelty work by classifying each
candidate panel against the literature via the Consensus.app Pro API. Each
panel falls into one of four classes:

- ``REPETITION``      — well-established (>=15 papers, strong consensus); demote / drop
- ``INCREMENTAL``     — partial overlap (5-14 papers, partial consensus); demote unless supporting
- ``HIDDEN_NOVELTY``  — niche / contested (1-4 papers, weak consensus); keep + flag
- ``ULTRA_NOVELTY``   — genuine gap (0 papers OR <=2 papers >=5 yrs old); promote

Supporting panels (controls, baselines, methodology, descriptive QC, provenance
cards) are PROTECTED from demotion regardless of novelty class — repetition is
acceptable when the data is needed for context.

Module structure
----------------

1. ``NoveltyClass`` / ``PanelRole`` / ``TargetNovelty`` — enums.
2. ``ConsensusPaper`` / ``ConsensusSearchResult`` — DTOs returned by clients.
3. ``ConsensusClient`` — abstract base; ``ConsensusProClient`` (live HTTP);
   ``MockConsensusClient`` (offline / test).
4. ``classify_novelty`` — pure function ``ConsensusSearchResult → NoveltyClass``.
5. ``is_supporting_panel`` — heuristic protector for controls / baselines / QC.
6. ``assess_panel_novelty`` — per-panel pipeline (query → search → classify → suggest).
7. ``score_figure_plan`` — plan-level holistic verdict + promote/drop/demote lists.
8. ``render_markdown_report`` — human-readable report.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "DEFAULT_THRESHOLDS",
    "ConsensusAPIError",
    "ConsensusClient",
    "ConsensusPaper",
    "ConsensusProClient",
    "ConsensusSearchResult",
    "ConsensusUnavailableError",
    "FigurePlanNoveltyReport",
    "MockConsensusClient",
    "NoveltyAssessment",
    "NoveltyClass",
    "NoveltyThresholds",
    "PanelCandidate",
    "PanelRole",
    "TargetNovelty",
    "assess_panel_novelty",
    "build_consensus_query",
    "classify_novelty",
    "is_supporting_panel",
    "render_markdown_report",
    "score_figure_plan",
]


# ─────────────────────── enums ───────────────────────


class NoveltyClass(StrEnum):
    """Four-way classification of a research claim against the literature."""

    repetition = "repetition"            # heavily covered → demote
    incremental = "incremental"          # partial overlap → demote unless supporting
    hidden_novelty = "hidden_novelty"    # niche / contested → keep, flag opportunity
    ultra_novelty = "ultra_novelty"      # genuine gap → promote


class PanelRole(StrEnum):
    """Role of a panel within the parent figure.

    ``supporting`` and ``methodology`` are protected from novelty demotion —
    they exist for context, controls, or QC and need not be novel claims.
    ``primary`` panels carry the main scientific message; ``auto`` lets the
    heuristic in :func:`is_supporting_panel` infer the role from the recipe
    name and modality.
    """

    primary = "primary"                  # main scientific claim, novelty matters
    supporting = "supporting"            # control / baseline / methodology QC — protected
    methodology = "methodology"          # diagnostic / provenance — protected
    auto = "auto"                        # heuristic-classified


class TargetNovelty(StrEnum):
    """How aggressively the planner should demote non-novel work.

    - ``maximal`` (default for the user's stated preference): drop REPETITION,
      demote INCREMENTAL to supplementary, keep+flag HIDDEN_NOVELTY, promote
      ULTRA_NOVELTY to main figure prominence.
    - ``balanced``: demote only REPETITION; keep INCREMENTAL.
    - ``permissive``: informational only, never demote.
    """

    maximal = "maximal"
    balanced = "balanced"
    permissive = "permissive"


# ─────────────────────── DTOs ───────────────────────


@dataclass(frozen=True)
class ConsensusPaper:
    """One paper returned by a Consensus search.

    All fields are populated tolerantly — missing values default to empty
    strings / 0 / None — so downstream classification cannot crash on a
    sparse response.
    """

    title: str
    authors: tuple[str, ...]
    year: int
    journal: str
    doi: str | None
    abstract_excerpt: str
    relevance_score: float  # 0..1


@dataclass(frozen=True)
class ConsensusSearchResult:
    """Aggregated response from a single Consensus search.

    ``consensus_meter`` mirrors the Consensus.app yes/no/mixed indicator for
    yes/no questions; for non-yes/no queries it is ``None``.
    ``consensus_strength`` is a 0..1 agreement-strength scalar.
    ``avg_year`` is the mean publication year across ``top_papers`` (None if
    no papers had a parseable year).
    """

    query: str
    n_matching_papers: int
    consensus_meter: str | None      # "yes" / "no" / "mixed" / None for non-yes/no
    consensus_strength: float        # 0..1 — agreement strength
    avg_year: float | None           # mean publication year of top hits
    top_papers: tuple[ConsensusPaper, ...]
    raw_response: dict[str, Any] = field(default_factory=dict, hash=False, compare=False)


# ─────────────────────── Consensus client interface ───────────────────────


class ConsensusAPIError(RuntimeError):
    """Raised on Consensus API HTTP errors / malformed responses."""


class ConsensusUnavailableError(RuntimeError):
    """Raised when CONSENSUS_API_KEY is missing or no client is configured."""


class ConsensusClient(ABC):
    """Abstract base for Consensus search backends.

    Implementations must return a :class:`ConsensusSearchResult` for any
    query. Failures should raise :class:`ConsensusAPIError` (network /
    response problems) or :class:`ConsensusUnavailableError` (missing
    credentials / dependency).
    """

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        year_min: int | None = None,
    ) -> ConsensusSearchResult:
        """Run a single search and return the aggregated result."""


class ConsensusProClient(ConsensusClient):
    """HTTP client for the Consensus Pro API.

    NOTE — the exact Consensus Pro API contract is documented as of 2026-05;
    if the live endpoint differs, override ``endpoint_url`` or subclass and
    override ``_parse_response``. The protocol assumed here is::

        POST {endpoint_url}/search
        Headers: Authorization: Bearer <api_key>
                 Content-Type: application/json
        Body:    {"query": "...", "limit": 20, "year_min": 2010}

        Response (JSON):
        {
          "query": "...",
          "n_matching_papers": 42,
          "consensus": {"meter": "yes", "strength": 0.78},
          "papers": [
            {"title": "...", "authors": ["..."], "year": 2024,
             "journal": "...", "doi": "10.../...",
             "abstract": "...", "relevance": 0.91},
            ...
          ]
        }

    The ``requests`` dependency is imported lazily inside :meth:`search` so
    the rest of the package works without it. Install with
    ``pip install panelforge-figures[novelty]``.
    """

    DEFAULT_ENDPOINT = "https://api.consensus.app/v1"
    DEFAULT_TIMEOUT_S = 30

    def __init__(
        self,
        api_key: str | None = None,
        *,
        endpoint_url: str | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self.api_key = api_key or os.environ.get("CONSENSUS_API_KEY")
        if not self.api_key:
            raise ConsensusUnavailableError(
                "CONSENSUS_API_KEY not set and no api_key passed to "
                "ConsensusProClient. Get a key from your Consensus.app Pro "
                "account at https://consensus.app/account or pass --mock to "
                "skip live calls."
            )
        self.endpoint_url = endpoint_url or self.DEFAULT_ENDPOINT
        self.timeout_s = timeout_s

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        year_min: int | None = None,
    ) -> ConsensusSearchResult:
        # Lazy import — keeps ``requests`` out of the base install.
        try:
            import requests
        except ImportError as exc:
            raise ConsensusUnavailableError(
                "`requests` not installed. Install with: "
                "pip install panelforge-figures[novelty]"
            ) from exc

        body: dict[str, Any] = {"query": query, "limit": limit}
        if year_min is not None:
            body["year_min"] = year_min

        try:
            r = requests.post(
                f"{self.endpoint_url}/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=self.timeout_s,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as exc:
            raise ConsensusAPIError(f"Consensus API error: {exc}") from exc

        return self._parse_response(query, data)

    def _parse_response(self, query: str, data: dict[str, Any]) -> ConsensusSearchResult:
        """Tolerant response parser.

        Soft-defaults missing fields rather than raising, so a partial
        Consensus response still produces a usable
        :class:`ConsensusSearchResult`.
        """
        papers_raw = data.get("papers", []) or []
        papers = tuple(
            ConsensusPaper(
                title=p.get("title", ""),
                authors=tuple(p.get("authors", []) or []),
                year=int(p.get("year", 0) or 0),
                journal=p.get("journal", ""),
                doi=p.get("doi"),
                abstract_excerpt=(p.get("abstract", "") or "")[:400],
                relevance_score=float(p.get("relevance", 0.0) or 0.0),
            )
            for p in papers_raw
        )
        consensus = data.get("consensus", {}) or {}
        years = [p.year for p in papers if p.year > 0]
        return ConsensusSearchResult(
            query=query,
            n_matching_papers=int(data.get("n_matching_papers", len(papers)) or 0),
            consensus_meter=consensus.get("meter"),
            consensus_strength=float(consensus.get("strength", 0.0) or 0.0),
            avg_year=(sum(years) / len(years)) if years else None,
            top_papers=papers,
            raw_response=data,
        )


class MockConsensusClient(ConsensusClient):
    """Offline / test client.

    Pre-loaded ``query → result`` map; falls back to ``default`` when the
    query is not in the map. Records every query in ``self.calls`` so tests
    can assert on call order.
    """

    def __init__(
        self,
        results_by_query: dict[str, ConsensusSearchResult] | None = None,
        default: ConsensusSearchResult | None = None,
    ) -> None:
        self.results_by_query = results_by_query or {}
        self.default = default or ConsensusSearchResult(
            query="default",
            n_matching_papers=0,
            consensus_meter=None,
            consensus_strength=0.0,
            avg_year=None,
            top_papers=(),
        )
        self.calls: list[str] = []  # for test inspection

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        year_min: int | None = None,
    ) -> ConsensusSearchResult:
        self.calls.append(query)
        return self.results_by_query.get(query, self.default)


# ─────────────────────── novelty classification ───────────────────────


@dataclass(frozen=True)
class NoveltyThresholds:
    """All thresholds in one place — use :data:`DEFAULT_THRESHOLDS` for
    the canonical set tuned in the v3.2.0 spec."""

    repetition_min_papers: int = 15
    repetition_min_consensus: float = 0.75
    incremental_min_papers: int = 5
    incremental_min_consensus: float = 0.5
    ultra_max_papers: int = 2
    ultra_min_age_years: int = 5
    current_year: int = 2026


DEFAULT_THRESHOLDS = NoveltyThresholds()


def classify_novelty(
    result: ConsensusSearchResult,
    *,
    thresholds: NoveltyThresholds = DEFAULT_THRESHOLDS,
) -> NoveltyClass:
    """Map a :class:`ConsensusSearchResult` to a :class:`NoveltyClass`.

    Rules (evaluated in order — first match wins):

    1. ``n >= 15 AND consensus >= 0.75`` → ``REPETITION``
    2. ``n >= 5  AND consensus >= 0.5``  → ``INCREMENTAL``
    3. ``n == 0``                         → ``ULTRA_NOVELTY``
    4. ``n <= 2 AND avg_year < (current_year - ultra_min_age_years)`` →
       ``ULTRA_NOVELTY`` (stale / pre-paradigm gap)
    5. fall through                       → ``HIDDEN_NOVELTY``

    The ``ultra_novelty`` rule for stale work is what distinguishes a
    genuine literature gap from a recent niche — a single 2024 paper is
    hidden novelty (someone already noticed the gap), but a single 2018
    paper with no follow-ups is ultra-novelty (the gap reopened).
    """
    n = result.n_matching_papers
    cs = result.consensus_strength

    if n >= thresholds.repetition_min_papers and cs >= thresholds.repetition_min_consensus:
        return NoveltyClass.repetition
    if n >= thresholds.incremental_min_papers and cs >= thresholds.incremental_min_consensus:
        return NoveltyClass.incremental
    if n == 0:
        return NoveltyClass.ultra_novelty
    if n <= thresholds.ultra_max_papers and result.avg_year is not None:
        if (thresholds.current_year - result.avg_year) >= thresholds.ultra_min_age_years:
            return NoveltyClass.ultra_novelty
    return NoveltyClass.hidden_novelty


# ─────────────────────── supporting-panel protection ───────────────────────


_SUPPORTING_FAMILY_HINTS: frozenset[str] = frozenset({
    "meta_and_diagnostic",   # provenance cards, audit summaries
    "qc",                    # quality-control panels
    "diagnostic",            # diagnostic-only families
})

_SUPPORTING_RECIPE_KEYWORDS: tuple[str, ...] = (
    "provenance",
    "audit",
    "control",
    "baseline",
    "qc_",
    "_qc",
    "diagnostic",
    "calibration",
    "negative_control",
    "positive_control",
    "methodology",
)


def is_supporting_panel(
    recipe_full_name: str,
    *,
    explicit_role: PanelRole = PanelRole.auto,
    modality: str | None = None,
) -> bool:
    """Decide whether a panel is *supporting* (protected from demotion).

    Decision order:

    1. Explicit role ``supporting`` or ``methodology`` → True.
    2. ``modality`` matches a SUPPORTING_FAMILY_HINT → True.
    3. ``recipe_full_name`` contains any SUPPORTING_RECIPE_KEYWORD → True.
    4. Otherwise → False (treated as primary novelty-bearing panel).

    The modality check is case-insensitive and the recipe-name check is
    case-insensitive substring matching. Returning True means the panel
    will keep its place in the figure regardless of how saturated the
    literature is for its claim.
    """
    if explicit_role in (PanelRole.supporting, PanelRole.methodology):
        return True
    if modality and modality.lower() in _SUPPORTING_FAMILY_HINTS:
        return True
    name_l = recipe_full_name.lower()
    return any(kw in name_l for kw in _SUPPORTING_RECIPE_KEYWORDS)


# ─────────────────────── per-panel + per-plan assessment ───────────────────────


@dataclass(frozen=True)
class PanelCandidate:
    """Input to the novelty assessment.

    ``research_question`` should be the plain-English claim the panel will
    support — ideally taken from the recipe's ``answers_question`` metadata.
    ``extra_query_terms`` are AND-joined onto the base query (use sparingly;
    too many AND clauses crater recall).
    """

    panel_id: str
    recipe_full_name: str
    research_question: str
    role: PanelRole = PanelRole.auto
    figure_id: str | None = None
    modality: str | None = None
    extra_query_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class NoveltyAssessment:
    """Per-panel novelty result, suitable for serialization."""

    panel_id: str
    recipe_full_name: str
    novelty_class: NoveltyClass
    is_supporting: bool
    consensus_n_papers: int
    consensus_strength: float
    avg_year: float | None
    suggestion: str                 # promote / keep / demote_to_supplementary / drop
    rationale: str
    top_paper_titles: tuple[str, ...] = ()
    target_novelty: TargetNovelty = TargetNovelty.maximal

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "recipe_full_name": self.recipe_full_name,
            "novelty_class": self.novelty_class.value,
            "is_supporting": self.is_supporting,
            "consensus_n_papers": self.consensus_n_papers,
            "consensus_strength": self.consensus_strength,
            "avg_year": self.avg_year,
            "suggestion": self.suggestion,
            "rationale": self.rationale,
            "top_paper_titles": list(self.top_paper_titles),
            "target_novelty": self.target_novelty.value,
        }


def build_consensus_query(panel: PanelCandidate) -> str:
    """Synthesize a single-line query from the panel's research question.

    Strips trailing punctuation (``? . !``) and trailing whitespace, then
    joins ``extra_query_terms`` with `` AND ``. Returns the bare research
    question if no extras are given.
    """
    base = panel.research_question.rstrip("?.! ").strip()
    if panel.extra_query_terms:
        extras = " AND ".join(t for t in panel.extra_query_terms if t)
        if extras:
            return f"{base} AND {extras}"
    return base


def _suggestion_for(
    novelty: NoveltyClass,
    is_supporting: bool,
    target: TargetNovelty,
) -> str:
    """Map (novelty, is_supporting, target) → action string."""
    if is_supporting:
        return "keep_protected"   # supporting panels are never demoted
    if target == TargetNovelty.permissive:
        return "informational"
    if target == TargetNovelty.balanced:
        # balanced: drop only repetition, keep incremental
        if novelty == NoveltyClass.repetition:
            return "demote_to_supplementary"
        if novelty == NoveltyClass.ultra_novelty:
            return "promote"
        return "keep"
    # maximal target: aggressive demotion
    if novelty == NoveltyClass.repetition:
        return "drop"
    if novelty == NoveltyClass.incremental:
        return "demote_to_supplementary"
    if novelty == NoveltyClass.hidden_novelty:
        return "keep_flag_opportunity"
    if novelty == NoveltyClass.ultra_novelty:
        return "promote"
    return "keep"


def _rationale_for(
    novelty: NoveltyClass,
    is_supporting: bool,
    result: ConsensusSearchResult,
    *,
    thresholds: NoveltyThresholds = DEFAULT_THRESHOLDS,
) -> str:
    """Render a one-sentence justification suitable for surface to the user."""
    if is_supporting:
        return (
            f"protected (supporting panel): {result.n_matching_papers} prior "
            "papers; supporting panels are not demoted regardless of "
            "literature density"
        )
    if novelty == NoveltyClass.repetition:
        return (
            f"{result.n_matching_papers} prior papers with strong consensus "
            f"(strength {result.consensus_strength:.2f}); claim is well-established"
        )
    if novelty == NoveltyClass.incremental:
        return (
            f"{result.n_matching_papers} prior papers with partial consensus "
            f"(strength {result.consensus_strength:.2f}); incremental work over "
            "existing literature"
        )
    if novelty == NoveltyClass.hidden_novelty:
        return (
            f"{result.n_matching_papers} prior papers with weak/divided "
            "consensus; niche or contested area — opportunity to clarify"
        )
    if novelty == NoveltyClass.ultra_novelty:
        if result.n_matching_papers == 0:
            return "no prior papers found — genuine literature gap"
        if result.avg_year is not None:
            age = thresholds.current_year - result.avg_year
            return (
                f"only {result.n_matching_papers} prior papers, all "
                f"~{int(age)} yrs old — stale or pre-paradigm gap"
            )
        return (
            f"only {result.n_matching_papers} prior papers; pre-paradigm gap"
        )
    return ""


def assess_panel_novelty(
    panel: PanelCandidate,
    client: ConsensusClient,
    *,
    target: TargetNovelty = TargetNovelty.maximal,
    thresholds: NoveltyThresholds = DEFAULT_THRESHOLDS,
) -> NoveltyAssessment:
    """Single-panel novelty assessment.

    Pipeline:

    1. Decide whether the panel is supporting (recipe + role + modality).
    2. Build the Consensus query from the research question + extras.
    3. ``client.search(query)``.
    4. ``classify_novelty(result, thresholds=thresholds)``.
    5. Compute the suggestion based on (novelty, is_supporting, target).
    """
    is_sup = is_supporting_panel(
        panel.recipe_full_name,
        explicit_role=panel.role,
        modality=panel.modality,
    )
    query = build_consensus_query(panel)
    result = client.search(query)
    novelty = classify_novelty(result, thresholds=thresholds)

    return NoveltyAssessment(
        panel_id=panel.panel_id,
        recipe_full_name=panel.recipe_full_name,
        novelty_class=novelty,
        is_supporting=is_sup,
        consensus_n_papers=result.n_matching_papers,
        consensus_strength=result.consensus_strength,
        avg_year=result.avg_year,
        suggestion=_suggestion_for(novelty, is_sup, target),
        rationale=_rationale_for(novelty, is_sup, result, thresholds=thresholds),
        top_paper_titles=tuple(p.title for p in result.top_papers[:3]),
        target_novelty=target,
    )


# ─────────────────────── plan-level holistic scoring ───────────────────────


@dataclass(frozen=True)
class FigurePlanNoveltyReport:
    """Plan-level novelty verdict + per-panel details + action lists."""

    panels: tuple[NoveltyAssessment, ...]
    n_panels: int
    n_protected: int
    n_repetition: int
    n_incremental: int
    n_hidden_novelty: int
    n_ultra_novelty: int
    novelty_density: float          # frac of non-supporting panels with >=hidden_novelty
    overall_verdict: str            # ultra-rich / novelty-rich / balanced / incremental-heavy / repetitive
    promote_panels: tuple[str, ...]  # panel_ids to promote
    drop_panels: tuple[str, ...]     # panel_ids suggested for dropping
    demote_panels: tuple[str, ...]   # panel_ids suggested for supplementary

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_panels": self.n_panels,
            "n_protected": self.n_protected,
            "n_repetition": self.n_repetition,
            "n_incremental": self.n_incremental,
            "n_hidden_novelty": self.n_hidden_novelty,
            "n_ultra_novelty": self.n_ultra_novelty,
            "novelty_density": self.novelty_density,
            "overall_verdict": self.overall_verdict,
            "promote_panels": list(self.promote_panels),
            "drop_panels": list(self.drop_panels),
            "demote_panels": list(self.demote_panels),
            "panels": [p.to_dict() for p in self.panels],
        }


def score_figure_plan(
    panels: list[PanelCandidate],
    client: ConsensusClient,
    *,
    target: TargetNovelty = TargetNovelty.maximal,
    thresholds: NoveltyThresholds = DEFAULT_THRESHOLDS,
) -> FigurePlanNoveltyReport:
    """Assess every panel + aggregate to a plan-level verdict.

    Density is computed over the non-supporting slice only — supporting
    panels (controls, baselines, methodology) are not the subject of the
    novelty verdict::

        novelty_density = (n_hidden_unprotected + n_ultra_unprotected)
                           / n_unprotected

    Verdict bands (evaluated in order — first match wins)::

        ultra-rich         density >= 0.6 AND ultra >= 30%
        novelty-rich       density >= 0.5
        balanced           density >= 0.3
        repetitive         density < 0.3 AND repetition_frac >= 0.3
        incremental-heavy  otherwise

    Action lists (``promote_panels`` / ``drop_panels`` / ``demote_panels``)
    are derived directly from each panel's ``suggestion`` string.
    """
    assessments = [
        assess_panel_novelty(p, client, target=target, thresholds=thresholds)
        for p in panels
    ]
    n_panels = len(assessments)
    n_protected = sum(1 for a in assessments if a.is_supporting)
    # Counts across the full plan (used in the report header / table).
    n_rep = sum(1 for a in assessments if a.novelty_class == NoveltyClass.repetition)
    n_inc = sum(1 for a in assessments if a.novelty_class == NoveltyClass.incremental)
    n_hid = sum(1 for a in assessments if a.novelty_class == NoveltyClass.hidden_novelty)
    n_ult = sum(1 for a in assessments if a.novelty_class == NoveltyClass.ultra_novelty)

    # Density / verdict are computed only over the non-supporting (= novelty-bearing)
    # slice — supporting panels are not the subject of the novelty verdict.
    unprotected = [a for a in assessments if not a.is_supporting]
    n_unprotected = len(unprotected)
    if n_unprotected == 0:
        # All-supporting plan: no novelty signal to assess; report as balanced.
        density = 0.0
        rep_frac = 0.0
        ultra_frac = 0.0
    else:
        n_rep_u = sum(1 for a in unprotected if a.novelty_class == NoveltyClass.repetition)
        n_hid_u = sum(1 for a in unprotected if a.novelty_class == NoveltyClass.hidden_novelty)
        n_ult_u = sum(1 for a in unprotected if a.novelty_class == NoveltyClass.ultra_novelty)
        density = (n_hid_u + n_ult_u) / n_unprotected
        rep_frac = n_rep_u / n_unprotected
        ultra_frac = n_ult_u / n_unprotected

    if density >= 0.6 and ultra_frac >= 0.3:
        verdict = "ultra-rich"
    elif density >= 0.5:
        verdict = "novelty-rich"
    elif density >= 0.3:
        verdict = "balanced"
    elif rep_frac >= 0.3:
        verdict = "repetitive"
    else:
        verdict = "incremental-heavy"

    promote = tuple(a.panel_id for a in assessments if a.suggestion == "promote")
    drop = tuple(a.panel_id for a in assessments if a.suggestion == "drop")
    demote = tuple(
        a.panel_id for a in assessments
        if a.suggestion == "demote_to_supplementary"
    )

    return FigurePlanNoveltyReport(
        panels=tuple(assessments),
        n_panels=n_panels,
        n_protected=n_protected,
        n_repetition=n_rep,
        n_incremental=n_inc,
        n_hidden_novelty=n_hid,
        n_ultra_novelty=n_ult,
        novelty_density=density,
        overall_verdict=verdict,
        promote_panels=promote,
        drop_panels=drop,
        demote_panels=demote,
    )


# ─────────────────────── markdown rendering ───────────────────────


_NOVELTY_LABEL: dict[NoveltyClass, str] = {
    NoveltyClass.ultra_novelty: "ultra-novelty",
    NoveltyClass.hidden_novelty: "hidden-novelty",
    NoveltyClass.incremental: "incremental",
    NoveltyClass.repetition: "repetition",
}


def _verdict_blurb(verdict: str) -> str:
    """One-line human-readable description of a verdict band."""
    return {
        "ultra-rich": "the plan is dominated by genuine literature gaps",
        "novelty-rich": "most panels probe niche or unmapped territory",
        "balanced": "mix of novel and incremental work",
        "incremental-heavy": "plan leans on incremental refinements",
        "repetitive": "plan duplicates well-established findings",
    }.get(verdict, "")


def render_markdown_report(report: FigurePlanNoveltyReport) -> str:
    """Render a Markdown report for human review.

    Sections:

    - Headline (verdict + density + blurb)
    - Distribution table (counts per class + supporting count)
    - Action lists (promote / demote / drop)
    - Per-panel details (one block per panel, ordered by panel_id)
    """
    lines: list[str] = []
    lines.append("# Novelty Scout Report")
    lines.append("")
    blurb = _verdict_blurb(report.overall_verdict)
    headline = (
        f"**Overall verdict**: {report.overall_verdict}  "
        f"(density {report.novelty_density:.2f})"
    )
    if blurb:
        headline += f" — {blurb}"
    lines.append(headline)
    lines.append("")

    lines.append(f"_n panels: {report.n_panels}; "
                  f"supporting-protected: {report.n_protected}_")
    lines.append("")

    # ────────── distribution ──────────
    lines.append("## Distribution")
    lines.append("")
    lines.append("| class            | count |")
    lines.append("|------------------|-------|")
    lines.append(f"| ultra-novelty    | {report.n_ultra_novelty:<5d} |")
    lines.append(f"| hidden-novelty   | {report.n_hidden_novelty:<5d} |")
    lines.append(f"| incremental      | {report.n_incremental:<5d} |")
    lines.append(f"| repetition       | {report.n_repetition:<5d} |")
    lines.append(f"| (supporting)     | {report.n_protected:<5d} |")
    lines.append("")

    # ────────── action lists ──────────
    lines.append("## Suggested actions")
    lines.append("")
    if report.promote_panels:
        lines.append("**Promote to main figure:**")
        for pid in report.promote_panels:
            lines.append(f"- `{pid}`")
        lines.append("")
    if report.demote_panels:
        lines.append("**Demote to supplementary:**")
        for pid in report.demote_panels:
            lines.append(f"- `{pid}`")
        lines.append("")
    if report.drop_panels:
        lines.append("**Drop (consider removing):**")
        for pid in report.drop_panels:
            lines.append(f"- `{pid}`")
        lines.append("")
    if not (report.promote_panels or report.demote_panels or report.drop_panels):
        lines.append("_No structural changes recommended._")
        lines.append("")

    # ────────── per-panel detail ──────────
    lines.append("## Panels")
    lines.append("")
    for a in report.panels:
        nl_label = _NOVELTY_LABEL.get(a.novelty_class, str(a.novelty_class))
        lines.append(f"### {a.panel_id} — `{a.recipe_full_name}`")
        lines.append("")
        protected_marker = "  [supporting-protected]" if a.is_supporting else ""
        lines.append(f"- **novelty class**: {nl_label}{protected_marker}")
        lines.append(f"- **n papers**: {a.consensus_n_papers}")
        lines.append(f"- **consensus strength**: {a.consensus_strength:.2f}")
        if a.avg_year is not None:
            lines.append(f"- **avg year**: {a.avg_year:.0f}")
        lines.append(f"- **suggestion**: {a.suggestion}")
        lines.append(f"- **rationale**: {a.rationale}")
        if a.top_paper_titles:
            lines.append("- **top prior papers**:")
            for t in a.top_paper_titles:
                if t:
                    lines.append(f"    - {t}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ─────────────────────── module-level convenience ───────────────────────


def report_to_json(report: FigurePlanNoveltyReport, *, indent: int = 2) -> str:
    """Convenience: round-trip a report through ``json.dumps``.

    Equivalent to ``json.dumps(report.to_dict(), indent=indent)`` but kept
    here so callers don't need to import ``json`` themselves.
    """
    return json.dumps(report.to_dict(), indent=indent)
