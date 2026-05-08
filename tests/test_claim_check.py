"""Tests for the figure-claim consistency engine (E2).

Covers:

1. ``extract_claims`` finds every ``Figure N`` reference.
2. ``extract_claims`` classifies "significantly higher" → ``significant_difference``.
3. ``extract_claims`` classifies "no significant difference" → ``no_difference``.
4. ``extract_claims`` captures direction (higher/lower).
5. ``verify_claim`` with no evidence → ``unverifiable``.
6. ``verify_claim`` with ``p < alpha`` + significance claim → ``supported``.
7. ``verify_claim`` with ``p >= alpha`` + significance claim → ``unsupported``.
8. ``verify_claim`` with ``no_difference`` + ``p < alpha`` → ``unsupported``.
9. ``verify_manuscript`` end-to-end with synthetic manuscript + audit JSON.
10. ``render_markdown_report`` contains "Unsupported" when ``n_unsupported > 0``.
11. CLI smoke: ``figures verify-claims --help``.
12. CLI exits 1 when unsupported claims are found.
13. ``report_to_dict`` round-trips via ``json.dumps``.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.claim_check import (
    Claim,
    ClaimAssertion,
    ClaimReport,
    ClaimVerdict,
    FigureEvidence,
    VerifiedClaim,
    extract_claims,
    render_markdown_report,
    report_to_dict,
    verify_claim,
    verify_manuscript,
)

# ───────────────────── 1. extract_claims: figure references ─────────────────


def test_extract_claims_finds_all_figure_references() -> None:
    """Every ``Figure N`` reference yields a Claim, including subletters
    and ``Fig.`` abbreviations."""
    text = (
        "Figure 1 shows the distribution. "
        "As demonstrated in Fig. 2, the trend persists. "
        "Figure 3a depicts a different effect. "
        "Figure 3b is the contrasting condition."
    )
    claims = extract_claims(text)
    ids = [c.figure_id for c in claims]
    assert ids == ["Figure 1", "Figure 2", "Figure 3a", "Figure 3b"]


def test_extract_claims_two_refs_in_one_sentence() -> None:
    """Two figure refs in one sentence yield two claims with the same sentence."""
    text = "Figure 1 and Figure 2 both show similar distributions."
    claims = extract_claims(text)
    assert len(claims) == 2
    assert claims[0].sentence == claims[1].sentence
    assert claims[0].figure_id == "Figure 1"
    assert claims[1].figure_id == "Figure 2"


def test_extract_claims_empty_text() -> None:
    """No figure refs → empty list, not crash."""
    assert extract_claims("") == []
    assert extract_claims("Hello world. No figures here.") == []


# ───────────────── 2 & 3. extract_claims: assertion classification ───────────


def test_significantly_higher_classifies_as_significant_difference() -> None:
    text = "In Figure 1, group A is significantly higher than group B."
    [c] = extract_claims(text)
    assert c.assertion == ClaimAssertion.significant_difference


def test_no_significant_classifies_as_no_difference() -> None:
    """'no significant' must beat 'significantly' — order matters."""
    text = "Figure 1 reveals no significant difference between groups."
    [c] = extract_claims(text)
    assert c.assertion == ClaimAssertion.no_difference


def test_p_value_inline_classifies_as_significant() -> None:
    """``p < 0.05`` triggers significant_difference."""
    text = "Figure 1 shows the effect (p < 0.01)."
    [c] = extract_claims(text)
    assert c.assertion == ClaimAssertion.significant_difference


def test_correlation_classifies_as_correlation_present() -> None:
    text = "Figure 2 shows that X correlates with Y."
    [c] = extract_claims(text)
    assert c.assertion == ClaimAssertion.correlation_present


def test_descriptive_classifies_as_descriptive() -> None:
    text = "Figure 1 shows the overall distribution of values."
    [c] = extract_claims(text)
    # "shows" alone (without significance/correlation/no-difference markers)
    # should classify as descriptive.
    assert c.assertion == ClaimAssertion.descriptive


def test_unparseable_classifies_as_unparseable() -> None:
    """A bare reference with no verb falls through to unparseable."""
    text = "See Figure 4."
    [c] = extract_claims(text)
    assert c.assertion == ClaimAssertion.unparseable


# ───────────────────── 4. extract_claims: direction & magnitude ──────────────


def test_extract_claims_direction_higher() -> None:
    text = "Figure 1 shows that A is significantly higher than B."
    [c] = extract_claims(text)
    assert c.direction == "higher"
    assert c.magnitude_qualifier == "significantly"


def test_extract_claims_direction_lower() -> None:
    text = "Figure 1 shows that C is markedly lower than D."
    [c] = extract_claims(text)
    assert c.direction == "lower"
    assert c.magnitude_qualifier == "markedly"


def test_extract_claims_no_direction() -> None:
    text = "Figure 1 shows the distribution."
    [c] = extract_claims(text)
    assert c.direction is None


# ───────────────────── 5. verify_claim: no evidence ─────────────────────────


def test_verify_claim_no_evidence_is_unverifiable() -> None:
    claim = Claim(
        figure_id="Figure 1",
        sentence="Figure 1 shows X.",
        assertion=ClaimAssertion.significant_difference,
        direction=None,
        magnitude_qualifier=None,
    )
    v = verify_claim(claim, evidence=None)
    assert v.verdict == ClaimVerdict.unverifiable
    assert "no figure" in v.rationale or "no audit" in v.rationale


def test_verify_claim_evidence_without_audit_is_unverifiable(tmp_path: Path) -> None:
    claim = Claim(
        figure_id="Figure 1",
        sentence="Figure 1 shows significantly higher values.",
        assertion=ClaimAssertion.significant_difference,
        direction="higher",
        magnitude_qualifier="significantly",
    )
    ev = FigureEvidence(
        figure_path=tmp_path / "figure_1.png",
        provenance_path=None,
        audit_findings=None,
        statistical_contract=None,
    )
    v = verify_claim(claim, ev)
    assert v.verdict == ClaimVerdict.unverifiable


# ───────────────────── 6 & 7. verify_claim: p-value gating ──────────────────


def _sig_claim() -> Claim:
    return Claim(
        figure_id="Figure 1",
        sentence="Figure 1 shows significantly higher values.",
        assertion=ClaimAssertion.significant_difference,
        direction="higher",
        magnitude_qualifier="significantly",
    )


def test_verify_claim_p_below_alpha_supports_significance() -> None:
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"p_value": 0.01},
        statistical_contract=None,
    )
    v = verify_claim(_sig_claim(), ev, alpha=0.05)
    assert v.verdict == ClaimVerdict.supported
    assert v.evidence["p_value"] == 0.01


def test_verify_claim_p_above_alpha_unsupports_significance() -> None:
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"p_value": 0.42},
        statistical_contract=None,
    )
    v = verify_claim(_sig_claim(), ev, alpha=0.05)
    assert v.verdict == ClaimVerdict.unsupported
    assert v.evidence["p_value"] == 0.42


def test_verify_claim_min_p_value_field_is_used() -> None:
    """Audit dicts that store ``min_p_value`` (instead of ``p_value``) work."""
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"min_p_value": 0.001},
        statistical_contract=None,
    )
    v = verify_claim(_sig_claim(), ev)
    assert v.verdict == ClaimVerdict.supported


# ───────────────────── 8. verify_claim: no_difference contradiction ─────────


def test_verify_claim_no_difference_with_p_below_alpha_is_unsupported() -> None:
    """Author claims null result; data show significance → UNSUPPORTED."""
    claim = Claim(
        figure_id="Figure 1",
        sentence="Figure 1 reveals no significant difference between groups.",
        assertion=ClaimAssertion.no_difference,
        direction=None,
        magnitude_qualifier=None,
    )
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"p_value": 0.001},
        statistical_contract=None,
    )
    v = verify_claim(claim, ev, alpha=0.05)
    assert v.verdict == ClaimVerdict.unsupported
    assert "contradicted" in v.rationale.lower() or "not" in v.rationale.lower()


def test_verify_claim_no_difference_with_p_above_alpha_is_supported() -> None:
    claim = Claim(
        figure_id="Figure 1",
        sentence="Figure 1 reveals no significant difference between groups.",
        assertion=ClaimAssertion.no_difference,
        direction=None,
        magnitude_qualifier=None,
    )
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"p_value": 0.42},
        statistical_contract=None,
    )
    v = verify_claim(claim, ev, alpha=0.05)
    assert v.verdict == ClaimVerdict.supported


# ───────────────────── verify_claim: correlation paths ──────────────────────


def test_verify_claim_correlation_supported() -> None:
    claim = Claim(
        figure_id="Figure 2",
        sentence="Figure 2 shows that X correlates with Y.",
        assertion=ClaimAssertion.correlation_present,
        direction=None,
        magnitude_qualifier=None,
    )
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"correlation_coefficient": 0.6},
        statistical_contract=None,
    )
    v = verify_claim(claim, ev)
    assert v.verdict == ClaimVerdict.supported


def test_verify_claim_correlation_unsupported_when_r_tiny() -> None:
    claim = Claim(
        figure_id="Figure 2",
        sentence="Figure 2 shows that X correlates with Y.",
        assertion=ClaimAssertion.correlation_present,
        direction=None,
        magnitude_qualifier=None,
    )
    ev = FigureEvidence(
        figure_path=Path("dummy.png"),
        provenance_path=None,
        audit_findings={"pearson_r": 0.02},
        statistical_contract=None,
    )
    v = verify_claim(claim, ev)
    assert v.verdict == ClaimVerdict.unsupported


# ───────────────────── 9. verify_manuscript end-to-end ──────────────────────


def _write_provenance(figures_dir: Path, fig_stem: str, audit: dict) -> None:
    """Helper: drop ``<fig_stem>.png`` (zero bytes is fine) plus its sidecar."""
    fig_path = figures_dir / f"{fig_stem}.png"
    fig_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    sidecar = figures_dir / f"{fig_stem}.png.provenance.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "figure_path": str(fig_path),
                "figure_sha256": "deadbeef",
                "rendered_at": "2026-05-07T00:00:00+00:00",
                "recipe": {
                    "full_name": "test.fake",
                    "statistical_contract": {"primary_test": "t-test"},
                },
                "data": {"sources": [], "column_mapping": {}},
                "audit": audit,
                "rendering_environment": {},
            }
        )
    )


def test_verify_manuscript_end_to_end(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    # Figure 1: claimed significant; data confirm (p=0.001) → supported.
    _write_provenance(figs, "figure_1", {"p_value": 0.001})
    # Figure 2: claimed null; data contradict (p=0.001) → unsupported.
    _write_provenance(figs, "figure_2", {"p_value": 0.001})
    # Figure 3: claimed correlation; no audit field → unverifiable.
    _write_provenance(figs, "figure_3", {})

    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text(
        "Figure 1 shows that group A is significantly higher than group B. "
        "Figure 2 reveals no significant difference between conditions. "
        "Figure 3 shows that X correlates with Y."
    )
    report = verify_manuscript(manuscript, figs)
    assert report.n_claims == 3
    assert report.n_supported == 1
    assert report.n_unsupported == 1
    assert report.n_unverifiable == 1


def test_verify_manuscript_no_figures_dir_files(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    manuscript = tmp_path / "m.tex"
    manuscript.write_text("Figure 1 shows significantly higher values.")
    report = verify_manuscript(manuscript, figs)
    assert report.n_claims == 1
    assert report.n_unverifiable == 1
    assert report.n_supported == 0


# ───────────────────── 10. render_markdown_report ──────────────────────────


def test_render_markdown_lists_unsupported_section() -> None:
    claim = Claim(
        figure_id="Figure 1",
        sentence="Figure 1 shows significantly higher values.",
        assertion=ClaimAssertion.significant_difference,
        direction="higher",
        magnitude_qualifier="significantly",
    )
    v = VerifiedClaim(
        claim=claim,
        verdict=ClaimVerdict.unsupported,
        evidence={"p_value": 0.42, "alpha": 0.05},
        rationale="audit p_value=0.42 >= alpha=0.05; significance claim NOT supported",
    )
    report = ClaimReport(
        n_claims=1, n_supported=0, n_unsupported=1, n_unverifiable=0, claims=(v,),
    )
    md = render_markdown_report(report)
    assert "# Claim Report" in md
    assert "Unsupported" in md
    assert "Figure 1" in md
    assert "UNSUPPORTED" in md


def test_render_markdown_no_unsupported_section_when_all_clean() -> None:
    """When n_unsupported == 0 the 'Unsupported claims' header isn't emitted."""
    report = ClaimReport(
        n_claims=0, n_supported=0, n_unsupported=0, n_unverifiable=0, claims=(),
    )
    md = render_markdown_report(report)
    assert "Unsupported claims" not in md
    assert "# Claim Report" in md


# ───────────────────── 11 & 12. CLI ─────────────────────────────────────────


def test_cli_verify_claims_help() -> None:
    r = CliRunner().invoke(main, ["verify-claims", "--help"])
    assert r.exit_code == 0
    assert "MANUSCRIPT" in r.output
    assert "--figures" in r.output
    assert "--alpha" in r.output


def test_cli_verify_claims_exits_1_on_unsupported(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _write_provenance(figs, "figure_1", {"p_value": 0.42})

    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text(
        "Figure 1 shows that group A is significantly higher than group B."
    )

    r = CliRunner().invoke(
        main,
        ["verify-claims", str(manuscript), "--figures", str(figs)],
    )
    assert r.exit_code == 1
    assert "unsupported" in r.output.lower() or "unsupported" in (r.stderr or "").lower()


def test_cli_verify_claims_exits_0_when_clean(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _write_provenance(figs, "figure_1", {"p_value": 0.001})

    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text(
        "Figure 1 shows that group A is significantly higher than group B."
    )

    r = CliRunner().invoke(
        main,
        ["verify-claims", str(manuscript), "--figures", str(figs)],
    )
    assert r.exit_code == 0


def test_cli_verify_claims_json_output(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _write_provenance(figs, "figure_1", {"p_value": 0.001})

    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text("Figure 1 shows significantly higher values.")

    r = CliRunner().invoke(
        main,
        ["verify-claims", str(manuscript), "--figures", str(figs), "--json"],
    )
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["n_claims"] == 1
    assert data["n_supported"] == 1


def test_cli_verify_claims_writes_to_output_file(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _write_provenance(figs, "figure_1", {"p_value": 0.001})

    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text("Figure 1 shows significantly higher values.")

    out = tmp_path / "report.md"
    r = CliRunner().invoke(
        main,
        [
            "verify-claims",
            str(manuscript),
            "--figures",
            str(figs),
            "--output",
            str(out),
        ],
    )
    assert r.exit_code == 0
    assert out.exists()
    assert "# Claim Report" in out.read_text()


# ───────────────────── 13. report_to_dict round-trip ────────────────────────


def test_report_to_dict_round_trips_via_json(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    _write_provenance(figs, "figure_1", {"p_value": 0.001})

    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text("Figure 1 shows significantly higher values.")

    report = verify_manuscript(manuscript, figs)
    d = report_to_dict(report)
    # Every field is JSON-serializable.
    s = json.dumps(d, indent=2)
    parsed = json.loads(s)
    assert parsed["n_claims"] == 1
    assert parsed["n_supported"] == 1
    assert parsed["claims"][0]["figure_id"] == "Figure 1"
    assert parsed["claims"][0]["verdict"] == "supported"
    assert parsed["claims"][0]["assertion"] == "significant_difference"


def test_report_to_dict_keys_complete() -> None:
    """The dict has all five top-level fields the JSON consumers expect."""
    report = ClaimReport(
        n_claims=0, n_supported=0, n_unsupported=0, n_unverifiable=0, claims=(),
    )
    d = report_to_dict(report)
    assert set(d.keys()) == {
        "n_claims",
        "n_supported",
        "n_unsupported",
        "n_unverifiable",
        "claims",
    }
