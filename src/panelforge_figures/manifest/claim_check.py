"""Figure-claim consistency engine.

Parses manuscript text, extracts every "Figure N shows X" sentence,
cross-references against the figure's audit_findings + provenance,
emits a CLAIM_REPORT with per-claim verdicts.

The engine is *best-effort*: it only marks a claim UNSUPPORTED when the
audit_findings contradict the claim (e.g. authors say "significantly
higher" but ``p_value >= alpha``). When no audit is available, or the
assertion type cannot be auto-verified, the claim is marked
UNVERIFIABLE rather than UNSUPPORTED — this keeps the false-positive
rate of the screen low so reviewers focus on the (rare) red verdicts.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

__all__ = [
    "Claim",
    "ClaimAssertion",
    "ClaimReport",
    "ClaimVerdict",
    "FigureEvidence",
    "VerifiedClaim",
    "extract_claims",
    "render_markdown_report",
    "report_to_dict",
    "verify_claim",
    "verify_manuscript",
]


class ClaimVerdict(StrEnum):
    """Outcome of comparing a claim to its figure's audit findings."""

    supported = "supported"
    unsupported = "unsupported"
    unverifiable = "unverifiable"  # no figure / no audit / assertion not auto-checkable


class ClaimAssertion(StrEnum):
    """Type of claim made about a figure."""

    significant_difference = "significant_difference"  # "...significantly higher/lower than..."
    no_difference = "no_difference"                     # "...no significant difference between..."
    correlation_present = "correlation_present"        # "...positively/negatively correlates..."
    no_correlation = "no_correlation"                  # "...uncorrelated..."
    effect_size_above = "effect_size_above"            # "...moderate effect (d > 0.5)..."
    descriptive = "descriptive"                         # "...shows the distribution..."
    unparseable = "unparseable"                         # heuristic couldn't classify


@dataclass(frozen=True)
class Claim:
    """A single claim about a figure, extracted from a manuscript sentence.

    Attributes
    ----------
    figure_id
        Canonical "Figure N[sub]" id (lowercased subletter), e.g. ``"Figure 3a"``.
    sentence
        The raw sentence containing the figure reference.
    assertion
        Heuristic classification of *what* the sentence claims.
    direction
        ``"higher"``, ``"lower"``, or ``None`` when no comparator is found.
    magnitude_qualifier
        Adverbs such as ``"significantly"``, ``"weakly"`` (lowercased), or
        ``None``.
    """

    figure_id: str
    sentence: str
    assertion: ClaimAssertion
    direction: str | None
    magnitude_qualifier: str | None


@dataclass(frozen=True)
class FigureEvidence:
    """Evidence loaded from a figure's provenance sidecar."""

    figure_path: Path
    provenance_path: Path | None
    audit_findings: dict | None
    statistical_contract: dict | None


@dataclass(frozen=True)
class VerifiedClaim:
    """A claim plus its verdict, evidence dict, and human-readable rationale."""

    claim: Claim
    verdict: ClaimVerdict
    evidence: dict
    rationale: str


@dataclass(frozen=True)
class ClaimReport:
    """Aggregate report for one manuscript × figures-directory pair."""

    n_claims: int
    n_supported: int
    n_unsupported: int
    n_unverifiable: int
    claims: tuple[VerifiedClaim, ...]


# ─────────────────────────── regex patterns ────────────────────────────────

_FIGURE_REF_PATTERN = re.compile(
    r"\b(?:Figure|Fig\.?)\s*(\d+)([a-zA-Z]?)\b",
    re.IGNORECASE,
)

# Order matters — _NO_DIFFERENCE is checked before _SIGNIFICANT so phrases
# like "no significant difference" classify as no_difference, not as
# significant_difference (the word "significant" appears in both).
_NO_DIFFERENCE_PATTERN = re.compile(
    r"\b(?:no\s+significant|not\s+significant|no\s+difference|"
    r"no\s+effect|null\s+result|n\.s\.)\b",
    re.IGNORECASE,
)
_SIGNIFICANT_PATTERN = re.compile(
    r"\b(?:significantly|p\s*[<≤]\s*0?\.0\d|highly\s+significant)\b",
    re.IGNORECASE,
)
_NO_CORRELATION_PATTERN = re.compile(
    r"\b(?:uncorrelated|no\s+correlation|no\s+association)\b",
    re.IGNORECASE,
)
# No trailing \b: stems like "correlat" appear inside words ("correlates",
# "correlation"), so we anchor only at the start of the word.
_CORRELATION_PATTERN = re.compile(
    r"\b(?:correlat|associat|relationship|cor=)",
    re.IGNORECASE,
)
_DESCRIPTIVE_PATTERN = re.compile(
    r"\b(?:shows|depicts|illustrates|displays|presents|visualizes)\b",
    re.IGNORECASE,
)

_DIRECTION_HIGHER = re.compile(
    r"\b(?:higher|greater|elevated|increased|larger|more)\b",
    re.IGNORECASE,
)
_DIRECTION_LOWER = re.compile(
    r"\b(?:lower|reduced|decreased|smaller|less)\b",
    re.IGNORECASE,
)

_MAGNITUDE_PATTERN = re.compile(
    r"\b(significantly|substantially|markedly|slightly|weakly|strongly)\b",
    re.IGNORECASE,
)


def _classify_assertion(sentence: str) -> ClaimAssertion:
    """Classify a sentence into one of :class:`ClaimAssertion`'s values."""
    if _NO_DIFFERENCE_PATTERN.search(sentence):
        return ClaimAssertion.no_difference
    if _NO_CORRELATION_PATTERN.search(sentence):
        return ClaimAssertion.no_correlation
    if _SIGNIFICANT_PATTERN.search(sentence):
        return ClaimAssertion.significant_difference
    if _CORRELATION_PATTERN.search(sentence):
        return ClaimAssertion.correlation_present
    if _DESCRIPTIVE_PATTERN.search(sentence):
        return ClaimAssertion.descriptive
    return ClaimAssertion.unparseable


def _direction(sentence: str) -> str | None:
    if _DIRECTION_HIGHER.search(sentence):
        return "higher"
    if _DIRECTION_LOWER.search(sentence):
        return "lower"
    return None


def _magnitude(sentence: str) -> str | None:
    m = _MAGNITUDE_PATTERN.search(sentence)
    return m.group(1).lower() if m else None


def extract_claims(text: str) -> list[Claim]:
    """Walk every sentence in ``text``; for each ``Figure N`` reference,
    classify the assertion type and extract direction + magnitude.

    A single sentence containing two figure references (e.g. "Figure 1
    and Figure 2 both show...") yields two :class:`Claim` objects with
    the same sentence and the same assertion.

    Parameters
    ----------
    text
        The raw manuscript text (LaTeX or plain text). LaTeX commands
        are not stripped; the heuristics treat them as part of words.

    Returns
    -------
    list[Claim]
        One claim per (sentence, figure-reference) pair, in document
        order.
    """
    # Sentence boundary heuristic: split on ., !, ? followed by whitespace.
    # First protect common abbreviations (e.g. "Fig.") from being split:
    # we replace the abbreviation's period with a sentinel, split, then
    # restore. This keeps "Fig. 2" intact as a single sentence.
    protected = re.sub(r"\bFig\.", "Fig\x00", text, flags=re.IGNORECASE)
    sentences = [s.replace("\x00", ".") for s in re.split(r"(?<=[.!?])\s+", protected)]
    claims: list[Claim] = []
    for sent in sentences:
        for match in _FIGURE_REF_PATTERN.finditer(sent):
            n = match.group(1)
            sub = match.group(2) or ""
            fig_id = f"Figure {n}{sub.lower()}"
            claims.append(
                Claim(
                    figure_id=fig_id,
                    sentence=sent.strip(),
                    assertion=_classify_assertion(sent),
                    direction=_direction(sent),
                    magnitude_qualifier=_magnitude(sent),
                )
            )
    return claims


# ─────────────────────────── evidence loader ───────────────────────────────


def _figure_id_to_stem(figure_id: str) -> str | None:
    """Convert ``"Figure 3a"`` → ``"figure_3a"``; return None if not parseable."""
    m = re.search(r"\d+[a-z]?", figure_id.lower())
    return f"figure_{m.group(0)}" if m else None


def _load_figure_evidence(figures_dir: Path, figure_id: str) -> FigureEvidence | None:
    """Locate a rendered figure for ``figure_id`` under ``figures_dir`` and
    return its provenance-derived evidence (audit + statistical contract).

    Naming convention: ``Figure 3a`` resolves to ``figure_3a.png`` (or
    ``.pdf``); the provenance sidecar is ``figure_3a.png.provenance.json``.
    Returns ``None`` if no figure file exists; the audit / contract may
    still be ``None`` if the sidecar is absent or malformed.
    """
    stem = _figure_id_to_stem(figure_id)
    if stem is None:
        return None
    for ext in (".png", ".pdf"):
        candidate = figures_dir / (stem + ext)
        if not candidate.exists():
            continue
        prov_path = candidate.with_suffix(candidate.suffix + ".provenance.json")
        audit, contract = None, None
        if prov_path.exists():
            try:
                data = json.loads(prov_path.read_text(encoding="utf-8"))
                audit = data.get("audit")
                contract = data.get("recipe", {}).get("statistical_contract")
            except (json.JSONDecodeError, OSError):
                # Bad sidecar: surface as audit=None so the verdict is
                # UNVERIFIABLE, not crash.
                pass
        return FigureEvidence(
            figure_path=candidate,
            provenance_path=prov_path if prov_path.exists() else None,
            audit_findings=audit,
            statistical_contract=contract,
        )
    return None


# ─────────────────────────── verifier ──────────────────────────────────────


def _extract_p(audit: dict) -> float | None:
    """Pull a p-value out of an audit dict from any of the conventional fields."""
    for key in ("p_value", "min_p_value", "p"):
        v = audit.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def _extract_r(audit: dict) -> float | None:
    """Pull a correlation coefficient out of an audit dict."""
    for key in ("correlation_coefficient", "pearson_r", "spearman_r", "r"):
        v = audit.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def verify_claim(
    claim: Claim,
    evidence: FigureEvidence | None,
    *,
    alpha: float = 0.05,
    correlation_threshold: float = 0.1,
) -> VerifiedClaim:
    """Compare a single :class:`Claim` against its :class:`FigureEvidence`.

    Returns a :class:`VerifiedClaim` whose ``verdict`` is one of:

    * SUPPORTED — the audit corroborates the claim.
    * UNSUPPORTED — the audit *contradicts* the claim (e.g. authors
      claim significance but ``p >= alpha``).
    * UNVERIFIABLE — no figure, no audit, missing fields, or the
      assertion type isn't auto-checkable.

    Parameters
    ----------
    claim
        The claim to verify.
    evidence
        Output of :func:`_load_figure_evidence`; may be ``None``.
    alpha
        Significance threshold for p-value comparisons (default 0.05).
    correlation_threshold
        Minimum ``|r|`` for a correlation to be considered present
        (default 0.1).
    """
    if evidence is None or evidence.audit_findings is None:
        return VerifiedClaim(
            claim=claim,
            verdict=ClaimVerdict.unverifiable,
            evidence={},
            rationale="no figure or no audit findings available",
        )

    audit = evidence.audit_findings

    if claim.assertion == ClaimAssertion.significant_difference:
        p = _extract_p(audit)
        if p is None:
            return VerifiedClaim(
                claim,
                ClaimVerdict.unverifiable,
                {"reason": "no p_value in audit"},
                "audit findings have no p_value field",
            )
        if p < alpha:
            return VerifiedClaim(
                claim,
                ClaimVerdict.supported,
                {"p_value": p, "alpha": alpha},
                f"audit p_value={p:.4g} < alpha={alpha} supports significance claim",
            )
        return VerifiedClaim(
            claim,
            ClaimVerdict.unsupported,
            {"p_value": p, "alpha": alpha},
            f"audit p_value={p:.4g} >= alpha={alpha}; significance claim NOT supported",
        )

    if claim.assertion == ClaimAssertion.no_difference:
        p = _extract_p(audit)
        if p is None:
            return VerifiedClaim(
                claim,
                ClaimVerdict.unverifiable,
                {"reason": "no p_value in audit"},
                "audit findings have no p_value field",
            )
        if p >= alpha:
            return VerifiedClaim(
                claim,
                ClaimVerdict.supported,
                {"p_value": p, "alpha": alpha},
                f"audit p_value={p:.4g} >= alpha={alpha} supports null result claim",
            )
        return VerifiedClaim(
            claim,
            ClaimVerdict.unsupported,
            {"p_value": p, "alpha": alpha},
            f"audit p_value={p:.4g} < alpha={alpha}; null claim contradicted by data",
        )

    if claim.assertion == ClaimAssertion.correlation_present:
        r = _extract_r(audit)
        if r is None:
            return VerifiedClaim(
                claim,
                ClaimVerdict.unverifiable,
                {"reason": "no correlation_coefficient in audit"},
                "audit findings have no correlation field",
            )
        if abs(r) >= correlation_threshold:
            return VerifiedClaim(
                claim,
                ClaimVerdict.supported,
                {"r": r, "threshold": correlation_threshold},
                f"|r|={abs(r):.3g} >= {correlation_threshold} supports correlation claim",
            )
        return VerifiedClaim(
            claim,
            ClaimVerdict.unsupported,
            {"r": r, "threshold": correlation_threshold},
            f"|r|={abs(r):.3g} < {correlation_threshold}; correlation claim weak/absent",
        )

    if claim.assertion == ClaimAssertion.no_correlation:
        r = _extract_r(audit)
        if r is None:
            return VerifiedClaim(
                claim,
                ClaimVerdict.unverifiable,
                {"reason": "no correlation_coefficient in audit"},
                "audit findings have no correlation field",
            )
        if abs(r) < correlation_threshold:
            return VerifiedClaim(
                claim,
                ClaimVerdict.supported,
                {"r": r, "threshold": correlation_threshold},
                f"|r|={abs(r):.3g} < {correlation_threshold} supports no-correlation claim",
            )
        return VerifiedClaim(
            claim,
            ClaimVerdict.unsupported,
            {"r": r, "threshold": correlation_threshold},
            f"|r|={abs(r):.3g} >= {correlation_threshold}; no-correlation claim contradicted",
        )

    # descriptive / unparseable / effect_size_above: not auto-verifiable
    return VerifiedClaim(
        claim=claim,
        verdict=ClaimVerdict.unverifiable,
        evidence={},
        rationale=f"assertion type {claim.assertion.value!r} is not auto-verifiable",
    )


def verify_manuscript(
    manuscript_path: Path,
    figures_dir: Path,
    *,
    alpha: float = 0.05,
    correlation_threshold: float = 0.1,
) -> ClaimReport:
    """End-to-end pipeline: extract claims from ``manuscript_path``, load
    each figure's evidence from ``figures_dir``, verify each claim, and
    aggregate the verdicts.

    Parameters
    ----------
    manuscript_path
        Path to a UTF-8 text or LaTeX manuscript.
    figures_dir
        Directory containing rendered figures + provenance sidecars.
    alpha, correlation_threshold
        Forwarded to :func:`verify_claim`.

    Returns
    -------
    ClaimReport
        Aggregate report with per-claim verdicts.
    """
    text = manuscript_path.read_text(encoding="utf-8")
    claims = extract_claims(text)
    verified: list[VerifiedClaim] = []
    for claim in claims:
        ev = _load_figure_evidence(figures_dir, claim.figure_id)
        verified.append(
            verify_claim(
                claim,
                ev,
                alpha=alpha,
                correlation_threshold=correlation_threshold,
            )
        )

    n_sup = sum(1 for v in verified if v.verdict == ClaimVerdict.supported)
    n_uns = sum(1 for v in verified if v.verdict == ClaimVerdict.unsupported)
    n_unv = sum(1 for v in verified if v.verdict == ClaimVerdict.unverifiable)

    return ClaimReport(
        n_claims=len(verified),
        n_supported=n_sup,
        n_unsupported=n_uns,
        n_unverifiable=n_unv,
        claims=tuple(verified),
    )


# ─────────────────────────── rendering ──────────────────────────────────────


def render_markdown_report(report: ClaimReport) -> str:
    """Render a :class:`ClaimReport` as Markdown for human review."""
    lines = [
        "# Claim Report",
        "",
        f"- Total claims: **{report.n_claims}**",
        f"- Supported: **{report.n_supported}**",
        f"- Unsupported: **{report.n_unsupported}**",
        f"- Unverifiable: **{report.n_unverifiable}**",
        "",
    ]
    if report.n_unsupported > 0:
        lines.extend(["## Unsupported claims", ""])
        for v in report.claims:
            if v.verdict == ClaimVerdict.unsupported:
                lines.extend(
                    [
                        f"### {v.claim.figure_id}",
                        f"> {v.claim.sentence}",
                        "- **Verdict**: UNSUPPORTED",
                        f"- **Rationale**: {v.rationale}",
                        "",
                    ]
                )
    if report.n_unverifiable > 0:
        lines.extend(["## Unverifiable claims", ""])
        for v in report.claims:
            if v.verdict == ClaimVerdict.unverifiable:
                lines.extend(
                    [
                        f"- **{v.claim.figure_id}**: {v.rationale}",
                        f"  > {v.claim.sentence}",
                    ]
                )
        lines.append("")
    return "\n".join(lines)


def report_to_dict(report: ClaimReport) -> dict:
    """Render a :class:`ClaimReport` as a JSON-serializable dict."""
    return {
        "n_claims": report.n_claims,
        "n_supported": report.n_supported,
        "n_unsupported": report.n_unsupported,
        "n_unverifiable": report.n_unverifiable,
        "claims": [
            {
                "figure_id": v.claim.figure_id,
                "sentence": v.claim.sentence,
                "assertion": v.claim.assertion.value,
                "direction": v.claim.direction,
                "magnitude_qualifier": v.claim.magnitude_qualifier,
                "verdict": v.verdict.value,
                "evidence": v.evidence,
                "rationale": v.rationale,
            }
            for v in report.claims
        ],
    }
