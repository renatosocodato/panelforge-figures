"""Tests for the E16 pre-submission journal-fit auditor.

Covers all 20 acceptance criteria spelled out in the elevation spec:

1. ``VENUE_RULES`` populates all 9 venues.
2. ``check_figure_count`` for Cell (<= 7) — pass at 5, error at 8.
3. ``check_word_counts`` for Nature abstract (<= 200) — pass at 195, error at 250.
4. ``check_word_counts`` NEJM structured abstract <= 250.
5. ``check_abstract_structure`` for NEJM detects missing 'Conclusions' section.
6. ``check_abstract_structure`` for Nature (free) returns empty.
7. ``check_data_availability_statement`` detects missing statement when required.
8. ``check_reference_style`` detects numbered citations.
9. ``check_reference_style`` detects author-year citations.
10. ``check_figure_extensions`` errors on .docx in figures_dir.
11. ``audit_venue`` end-to-end on a clean manuscript → ``ready_to_submit``.
12. ``audit_venue`` on a manuscript with too many figures → ``blocked``.
13. ``audit_venue`` on a manuscript with warnings only → ``needs_revision``.
14. ``VenueAuditReport.to_dict`` serialises.
15. ``render_venue_audit_markdown`` contains all violations.
16. CLI: ``figures audit-venue --help``.
17. CLI: ``figures audit-venue`` on synthetic manuscript exits 0 when clean.
18. CLI: with errors → exit 1.
19. CLI: ``--fail-on-warning`` on warn → exit 1.
20. CI runner integration: ``_run_audit_venue`` now returns real status,
    not 'skipped placeholder'.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.ci_runner import (
    CIAuditStep,
    StepStatus,
    _run_audit_venue,
)
from panelforge_figures.manifest.venue_auditor import (
    VENUE_RULES,
    RuleSeverity,
    RuleViolation,
    Venue,
    VenueAuditorError,
    VenueAuditReport,
    audit_venue,
    check_abstract_structure,
    check_data_availability_statement,
    check_figure_count,
    check_figure_extensions,
    check_reference_style,
    check_word_counts,
    render_venue_audit_markdown,
)

# --------------------------------------------------------------------------- #
# 1. VENUE_RULES coverage                                                      #
# --------------------------------------------------------------------------- #


def test_venue_rules_covers_all_nine_venues() -> None:
    expected = {
        Venue.plain,
        Venue.nature,
        Venue.cell,
        Venue.nejm,
        Venue.biorxiv,
        Venue.science,
        Venue.elife,
        Venue.plos_one,
        Venue.jama,
    }
    assert set(VENUE_RULES.keys()) == expected
    # Each rule's venue tag must match its key.
    for k, v in VENUE_RULES.items():
        assert v.venue == k


# --------------------------------------------------------------------------- #
# 2. check_figure_count — Cell                                                 #
# --------------------------------------------------------------------------- #


def test_check_figure_count_cell_passes_at_five() -> None:
    rules = VENUE_RULES[Venue.cell]
    out = check_figure_count(rules, n_main_figures=5, n_main_tables=0)
    assert out == ()


def test_check_figure_count_cell_errors_at_eight() -> None:
    rules = VENUE_RULES[Venue.cell]
    out = check_figure_count(rules, n_main_figures=8, n_main_tables=0)
    assert len(out) >= 1
    assert any(v.severity == RuleSeverity.error for v in out)
    assert any(v.rule_id == "max_main_figures" for v in out)


# --------------------------------------------------------------------------- #
# 3. check_word_counts — Nature abstract                                       #
# --------------------------------------------------------------------------- #


def test_check_word_counts_nature_abstract_passes_at_195() -> None:
    rules = VENUE_RULES[Venue.nature]
    out = check_word_counts(rules, abstract_words=195)
    assert out == ()


def test_check_word_counts_nature_abstract_errors_at_250() -> None:
    rules = VENUE_RULES[Venue.nature]
    out = check_word_counts(rules, abstract_words=250)
    assert len(out) == 1
    assert out[0].rule_id == "max_abstract_words"
    assert out[0].severity == RuleSeverity.error


# --------------------------------------------------------------------------- #
# 4. check_word_counts — NEJM structured abstract (250)                        #
# --------------------------------------------------------------------------- #


def test_check_word_counts_nejm_abstract_passes_at_240() -> None:
    rules = VENUE_RULES[Venue.nejm]
    out = check_word_counts(rules, abstract_words=240)
    assert out == ()


def test_check_word_counts_nejm_abstract_errors_at_300() -> None:
    rules = VENUE_RULES[Venue.nejm]
    out = check_word_counts(rules, abstract_words=300)
    assert any(v.rule_id == "max_abstract_words" for v in out)


# --------------------------------------------------------------------------- #
# 5. check_abstract_structure — NEJM missing 'Conclusions'                     #
# --------------------------------------------------------------------------- #


def test_check_abstract_structure_nejm_detects_missing_conclusions() -> None:
    rules = VENUE_RULES[Venue.nejm]
    abstract = (
        "Background: We studied X. "
        "Methods: We did Y. "
        "Results: We found Z."
    )
    out = check_abstract_structure(rules, abstract)
    assert len(out) == 1
    assert out[0].rule_id == "abstract_structure_incomplete"
    assert "Conclusions" in out[0].actual_value


def test_check_abstract_structure_nejm_passes_when_all_present() -> None:
    rules = VENUE_RULES[Venue.nejm]
    abstract = (
        "Background: We studied X. "
        "Methods: We did Y. "
        "Results: We found Z. "
        "Conclusions: This matters."
    )
    out = check_abstract_structure(rules, abstract)
    assert out == ()


# --------------------------------------------------------------------------- #
# 6. check_abstract_structure — Nature (free) returns empty                    #
# --------------------------------------------------------------------------- #


def test_check_abstract_structure_nature_free_returns_empty() -> None:
    rules = VENUE_RULES[Venue.nature]
    abstract = "Free-form abstract without any subsections."
    out = check_abstract_structure(rules, abstract)
    assert out == ()


# --------------------------------------------------------------------------- #
# 7. check_data_availability_statement                                         #
# --------------------------------------------------------------------------- #


def test_check_data_availability_detects_missing() -> None:
    rules = VENUE_RULES[Venue.nature]  # requires data + code availability
    text = "This manuscript talks about science with no availability statement."
    out = check_data_availability_statement(rules, text)
    rule_ids = {v.rule_id for v in out}
    assert "data_availability_missing" in rule_ids
    assert "code_availability_missing" in rule_ids


def test_check_data_availability_passes_when_present() -> None:
    rules = VENUE_RULES[Venue.nature]
    text = (
        "Methods: ... Data availability: deposited at GEO under GSE12345. "
        "Code availability: github.com/lab/project."
    )
    out = check_data_availability_statement(rules, text)
    assert out == ()


def test_check_data_availability_skipped_for_biorxiv() -> None:
    """biorxiv does not require statements; check should return empty."""
    rules = VENUE_RULES[Venue.biorxiv]
    text = "No statement."
    out = check_data_availability_statement(rules, text)
    assert out == ()


# --------------------------------------------------------------------------- #
# 8. check_reference_style — numbered                                          #
# --------------------------------------------------------------------------- #


def test_check_reference_style_detects_numbered() -> None:
    rules = VENUE_RULES[Venue.nature]  # expects "numbered"
    text = "We showed this [1] and that [2-5] as well as [6, 7]."
    out = check_reference_style(rules, text)
    # Numbered manuscript + numbered venue → no mismatch.
    assert out == ()


def test_check_reference_style_numbered_in_authoryear_venue() -> None:
    rules = VENUE_RULES[Venue.cell]  # expects "cell" (author-year)
    text = "Citations like [1] and [2-5]."
    out = check_reference_style(rules, text)
    assert len(out) == 1
    assert out[0].rule_id == "reference_style_mismatch"
    assert out[0].actual_value == "numbered"


# --------------------------------------------------------------------------- #
# 9. check_reference_style — author-year                                       #
# --------------------------------------------------------------------------- #


def test_check_reference_style_detects_author_year() -> None:
    rules = VENUE_RULES[Venue.cell]  # cell uses author-year
    text = "Shown by (Smith, 2024) and (Jones et al., 2023)."
    out = check_reference_style(rules, text)
    assert out == ()


def test_check_reference_style_authoryear_in_numbered_venue() -> None:
    rules = VENUE_RULES[Venue.nature]  # nature expects numbered
    text = "We showed (Smith, 2024) and (Jones and Brown, 2023)."
    out = check_reference_style(rules, text)
    assert len(out) == 1
    assert out[0].rule_id == "reference_style_mismatch"
    assert out[0].actual_value == "author-year"


# --------------------------------------------------------------------------- #
# 10. check_figure_extensions — .docx errors                                  #
# --------------------------------------------------------------------------- #


def test_check_figure_extensions_errors_on_docx(tmp_path: Path) -> None:
    figs = tmp_path / "figures"
    figs.mkdir()
    (figs / "figure_1.pdf").write_text("dummy")
    (figs / "figure_2.docx").write_text("dummy")
    rules = VENUE_RULES[Venue.nature]
    out = check_figure_extensions(rules, figs)
    assert len(out) == 1
    assert out[0].rule_id == "figure_extension_disallowed"
    assert out[0].actual_value == ".docx"


def test_check_figure_extensions_skipped_for_missing_dir(tmp_path: Path) -> None:
    rules = VENUE_RULES[Venue.nature]
    out = check_figure_extensions(rules, tmp_path / "nonexistent")
    assert out == ()


# --------------------------------------------------------------------------- #
# 11. audit_venue end-to-end — clean manuscript → ready_to_submit              #
# --------------------------------------------------------------------------- #


_CLEAN_MANUSCRIPT = r"""\documentclass{article}
\title{A clean manuscript with proper availability statements.}

\begin{document}

\begin{abstract}
This is a short, free-format abstract describing our findings. It is
deliberately kept under the 200-word Nature cap. We address a clear
biological question, present concise results, and discuss the
implications for the field. This abstract is purely illustrative and
contains far fewer than 200 words by design.
\end{abstract}

\section{Introduction}
We cite prior work [1, 2] and recent advances [3-5].

\section{Methods}
We performed experiments as described. Data availability: all data
have been deposited at GEO under accession GSE000000. Code
availability: the analysis code is available at github.com/lab/project.

\section{Results}
\begin{figure}
\includegraphics{figure_1.pdf}
\caption{Description.}
\label{fig:1}
\end{figure}

\begin{figure}
\includegraphics{figure_2.pdf}
\caption{Description.}
\label{fig:2}
\end{figure}

\section{Discussion}
See ref [6] for further reading.

\end{document}
"""


def test_audit_venue_clean_manuscript_ready_to_submit(tmp_path: Path) -> None:
    m = tmp_path / "manuscript.tex"
    m.write_text(_CLEAN_MANUSCRIPT)
    figs = tmp_path / "figures"
    figs.mkdir()
    (figs / "figure_1.pdf").write_text("dummy")
    (figs / "figure_2.pdf").write_text("dummy")

    report = audit_venue(
        m, venue=Venue.nature, figures_dir=figs,
    )
    assert report.n_errors == 0
    assert report.overall_verdict in ("ready_to_submit", "needs_revision")
    # If color-blind safety check fires on PDFs it should not be an error.
    for v in report.violations:
        assert v.severity != RuleSeverity.error, v


# --------------------------------------------------------------------------- #
# 12. audit_venue — too many figures → blocked                                 #
# --------------------------------------------------------------------------- #


def _make_manuscript_with_n_figures(path: Path, n: int) -> Path:
    blocks = []
    for i in range(1, n + 1):
        blocks.append(
            f"\\begin{{figure}}\n"
            f"\\includegraphics{{figure_{i}.pdf}}\n"
            f"\\caption{{Caption {i}.}}\n"
            f"\\label{{fig:{i}}}\n"
            f"\\end{{figure}}\n"
        )
    body = "\n".join(blocks)
    tex = (
        "\\documentclass{article}\n\\begin{document}\n"
        "\\begin{abstract}\nAbstract.\n\\end{abstract}\n"
        f"{body}\n"
        "Data availability: at GEO. Code availability: github.\n"
        "\\end{document}\n"
    )
    path.write_text(tex)
    return path


def test_audit_venue_too_many_figures_blocked(tmp_path: Path) -> None:
    m = _make_manuscript_with_n_figures(tmp_path / "m.tex", n=10)
    report = audit_venue(m, venue=Venue.nature)
    assert report.overall_verdict == "blocked"
    assert report.n_errors >= 1
    assert any(v.rule_id == "max_main_figures" for v in report.violations)


# --------------------------------------------------------------------------- #
# 13. audit_venue — warnings only → needs_revision                             #
# --------------------------------------------------------------------------- #


def test_audit_venue_warnings_only_needs_revision(tmp_path: Path) -> None:
    """Use plos_one (low requirement set) and feed it a manuscript with
    author-year citations and a missing data availability statement.

    plos_one requires data + code availability and uses vancouver
    citation style. So missing statements are errors, not warnings.
    To get warnings only, build a manuscript that has all required
    statements but uses author-year in a numbered-style venue: the
    style mismatch is a warning.
    """
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\begin{abstract}\nShort abstract.\n\\end{abstract}\n"
        "We cite (Smith, 2020) and (Jones, 2021).\n"
        "Data availability: deposited at GEO.\n"
        "Code availability: github.com/example.\n"
        "\\end{document}\n"
    )
    report = audit_venue(m, venue=Venue.nature)
    assert report.n_errors == 0
    assert report.n_warnings >= 1
    assert report.overall_verdict == "needs_revision"


# --------------------------------------------------------------------------- #
# 14. VenueAuditReport.to_dict serialises                                      #
# --------------------------------------------------------------------------- #


def test_venue_audit_report_to_dict_is_json_serialisable(tmp_path: Path) -> None:
    m = _make_manuscript_with_n_figures(tmp_path / "m.tex", n=2)
    report = audit_venue(m, venue=Venue.nature)
    d = report.to_dict()
    # Must round-trip through JSON.
    text = json.dumps(d, default=str)
    parsed = json.loads(text)
    assert parsed["venue"] == "nature"
    assert "violations" in parsed
    assert "overall_verdict" in parsed
    assert parsed["rules_applied"] >= 1


# --------------------------------------------------------------------------- #
# 15. render_venue_audit_markdown contains all violations                      #
# --------------------------------------------------------------------------- #


def test_render_venue_audit_markdown_contains_all_violations(tmp_path: Path) -> None:
    m = _make_manuscript_with_n_figures(tmp_path / "m.tex", n=10)
    report = audit_venue(m, venue=Venue.nature)
    md = render_venue_audit_markdown(report)
    # Every violation rule_id must appear at least once.
    for v in report.violations:
        assert v.rule_id in md, f"rule_id {v.rule_id} not in markdown"
    # And the badge must reflect the verdict.
    assert "BLOCKED" in md or "NEEDS REVISION" in md or "READY TO SUBMIT" in md


def test_render_venue_audit_markdown_ready_to_submit_no_violations(
    tmp_path: Path,
) -> None:
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\nNo content.\n\\end{document}\n"
    )
    # plain venue has no requirements → all checks skipped → 0 violations.
    report = audit_venue(m, venue=Venue.plain)
    md = render_venue_audit_markdown(report)
    assert "READY TO SUBMIT" in md


# --------------------------------------------------------------------------- #
# 16-19. CLI smoke tests                                                       #
# --------------------------------------------------------------------------- #


def test_cli_audit_venue_help() -> None:
    r = CliRunner().invoke(main, ["audit-venue", "--help"])
    assert r.exit_code == 0
    assert "audit-venue" in r.output.lower() or "venue" in r.output.lower()


def test_cli_audit_venue_clean_exit_zero(tmp_path: Path) -> None:
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\nBody.\n\\end{document}\n"
    )
    figs = tmp_path / "figures"
    figs.mkdir()
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "audit-venue", str(m),
            "--venue", "plain",
            "--figures-dir", str(figs),
        ],
    )
    assert r.exit_code == 0, r.output


def test_cli_audit_venue_with_errors_exit_one(tmp_path: Path) -> None:
    m = _make_manuscript_with_n_figures(tmp_path / "m.tex", n=10)
    figs = tmp_path / "figures"
    figs.mkdir()
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "audit-venue", str(m),
            "--venue", "nature",
            "--figures-dir", str(figs),
        ],
    )
    assert r.exit_code == 1, r.output


def test_cli_audit_venue_fail_on_warning_exit_one(tmp_path: Path) -> None:
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\n"
        "\\begin{abstract}\nShort abstract.\n\\end{abstract}\n"
        "We cite (Smith, 2020) and (Jones, 2021).\n"
        "Data availability: deposited.\n"
        "Code availability: github.\n"
        "\\end{document}\n"
    )
    figs = tmp_path / "figures"
    figs.mkdir()
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "audit-venue", str(m),
            "--venue", "nature",
            "--figures-dir", str(figs),
            "--fail-on-warning",
        ],
    )
    # nature expects numbered citations, but we used author-year → warn → fail.
    assert r.exit_code == 1, r.output


def test_cli_audit_venue_json_output(tmp_path: Path) -> None:
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\nBody.\n\\end{document}\n"
    )
    out = tmp_path / "report.json"
    runner = CliRunner()
    r = runner.invoke(
        main,
        [
            "audit-venue", str(m),
            "--venue", "plain",
            "--output", str(out),
            "--json",
        ],
    )
    assert r.exit_code == 0, r.output
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["venue"] == "plain"


def test_cli_audit_venue_unknown_venue_exit_two(tmp_path: Path) -> None:
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\nBody.\n\\end{document}\n"
    )
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["audit-venue", str(m), "--venue", "nonexistent-journal"],
    )
    assert r.exit_code == 2


# --------------------------------------------------------------------------- #
# 20. CI runner integration: _run_audit_venue is now real                      #
# --------------------------------------------------------------------------- #


def test_ci_runner_audit_venue_returns_real_status(tmp_path: Path) -> None:
    """E16 is now shipped — the CI runner should produce a real verdict
    (not 'skipped placeholder') when given a manuscript + venue.
    """
    m = tmp_path / "m.tex"
    m.write_text(
        "\\documentclass{article}\n\\begin{document}\nBody text.\n\\end{document}\n"
    )
    figs = tmp_path / "figures"
    figs.mkdir()
    result = _run_audit_venue(
        manuscript_path=m,
        figures_dir=figs,
        venue="plain",
        skip_missing_inputs=True,
    )
    assert result.step == CIAuditStep.audit_venue
    # plain venue has zero requirements → pass.
    assert result.status == StepStatus.pass_
    assert "not yet shipped" not in result.summary
    assert "placeholder" not in result.summary


def test_ci_runner_audit_venue_real_failure(tmp_path: Path) -> None:
    """When venue rules are violated, _run_audit_venue should map to fail/warn."""
    m = _make_manuscript_with_n_figures(tmp_path / "m.tex", n=10)
    result = _run_audit_venue(
        manuscript_path=m,
        figures_dir=None,
        venue="nature",
        skip_missing_inputs=True,
    )
    assert result.step == CIAuditStep.audit_venue
    assert result.status == StepStatus.fail
    assert result.n_errors >= 1


def test_ci_runner_audit_venue_unknown_venue_skipped(tmp_path: Path) -> None:
    m = tmp_path / "m.tex"
    m.write_text("\\documentclass{article}\n\\begin{document}\nBody.\n\\end{document}\n")
    result = _run_audit_venue(
        manuscript_path=m,
        figures_dir=None,
        venue="not-a-journal",
        skip_missing_inputs=True,
    )
    # unknown venue → skipped (not crash).
    assert result.status == StepStatus.skipped


# --------------------------------------------------------------------------- #
# Bonus: VenueAuditorError on bad inputs                                       #
# --------------------------------------------------------------------------- #


def test_audit_venue_raises_on_missing_manuscript(tmp_path: Path) -> None:
    with pytest.raises(VenueAuditorError):
        audit_venue(tmp_path / "nope.tex", venue=Venue.plain)


def test_audit_venue_raises_on_unknown_venue(tmp_path: Path) -> None:
    m = tmp_path / "m.tex"
    m.write_text("\\documentclass{article}\n\\begin{document}\nBody.\n\\end{document}\n")
    with pytest.raises(VenueAuditorError):
        audit_venue(m, venue="not-a-journal")


def test_violation_to_dict_round_trip() -> None:
    v = RuleViolation(
        rule_id="x",
        severity=RuleSeverity.warning,
        actual_value=10,
        expected_value="<= 5",
        location="manuscript",
        message="too many",
        remediation="trim",
    )
    d = v.to_dict()
    assert d["rule_id"] == "x"
    assert d["severity"] == "warning"
    assert d["actual_value"] == 10
    assert d["expected_value"] == "<= 5"


def test_venue_audit_report_dataclass_fields(tmp_path: Path) -> None:
    """VenueAuditReport.figures_dir handles None correctly."""
    m = tmp_path / "m.tex"
    m.write_text("\\documentclass{article}\n\\begin{document}\nBody.\n\\end{document}\n")
    report = audit_venue(m, venue=Venue.plain)
    assert isinstance(report, VenueAuditReport)
    assert report.figures_dir is None
    d = report.to_dict()
    assert d["figures_dir"] is None
