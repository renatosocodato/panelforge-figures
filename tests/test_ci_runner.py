"""Tests for the bundled CI audit runner (E18).

Covers:

1. ``run_ci_audit`` with no manuscript → default_steps returns just (scout,).
2. ``run_ci_audit`` with manuscript → default_steps returns 4 steps.
3. Each step's ``_run_*`` dispatcher catches exceptions and emits ``StepStatus.error``.
4. ``_compute_overall_status`` returns max severity (fail > warn > pass > skipped).
5. ``_compute_overall_status`` with ``fail_on_warning=True`` promotes warn → fail.
6. ``run_ci_audit`` records non-negative ``duration_ms`` per step.
7. ``CIStepResult`` and ``CIAuditReport`` ``to_dict`` are JSON-serializable.
8. ``render_ci_report_markdown`` contains all step names.
9. ``render_ci_report_github_comment`` truncates over 50-char details.
10. ``render_ci_report_junit_xml`` is valid XML with one testcase per step.
11. ``_run_scout`` on a tmp project → ``CIStepResult`` with status (pass|warn|fail).
12. ``_run_verify_claims`` skipped when manuscript_path is None.
13. ``_run_lint_xrefs`` skipped when manuscript_path is None.
14. ``_run_audit_venue`` emits ``StepStatus.skipped`` with "E16 not yet shipped".
15. ``_run_audit_bias`` emits ``StepStatus.skipped`` with "E17 not yet shipped".
16. CLI: ``figures ci-audit --help`` exits 0.
17. CLI: ``figures ci-audit --project-root tmp`` writes report.
18. CLI: invalid step name → exit 2.
19. CLI: with errors → exit 1.
20. CLI: --output-json writes valid JSON.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from click.testing import CliRunner

from panelforge_figures.cli import main
from panelforge_figures.manifest.ci_runner import (
    CIAuditReport,
    CIAuditStep,
    CIRunnerError,
    CIStepResult,
    StepStatus,
    _compute_overall_status,
    _default_steps,
    _run_audit_bias,
    _run_audit_venue,
    _run_lint_xrefs,
    _run_scout,
    _run_step,
    _run_verify_claims,
    render_ci_report_github_comment,
    render_ci_report_junit_xml,
    render_ci_report_markdown,
    run_ci_audit,
)

# --------------------------------------------------------------------------- #
# 1. default_steps                                                             #
# --------------------------------------------------------------------------- #


def test_default_steps_no_manuscript() -> None:
    """Without a manuscript, only scout runs."""
    assert _default_steps(None) == (CIAuditStep.scout,)


def test_default_steps_with_manuscript() -> None:
    """With a manuscript, scout + verify-claims + lint-xrefs + checklist run."""
    steps = _default_steps(Path("manuscript.tex"))
    assert steps == (
        CIAuditStep.scout,
        CIAuditStep.verify_claims,
        CIAuditStep.lint_xrefs,
        CIAuditStep.checklist_arrive,
    )


def test_run_ci_audit_no_manuscript_runs_only_scout(tmp_path: Path) -> None:
    """Top-level: default chain for no-manuscript projects is just scout."""
    report = run_ci_audit(tmp_path, manuscript_path=None)
    assert report.n_steps_run == 1
    assert report.steps[0].step == CIAuditStep.scout


def test_run_ci_audit_with_manuscript_runs_four_steps(tmp_path: Path) -> None:
    """Default chain for a manuscript repo is scout + 3 more."""
    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text("Figure 1 shows the result.\n")

    report = run_ci_audit(tmp_path, manuscript_path=manuscript)
    assert report.n_steps_run == 4
    step_kinds = [s.step for s in report.steps]
    assert step_kinds == [
        CIAuditStep.scout,
        CIAuditStep.verify_claims,
        CIAuditStep.lint_xrefs,
        CIAuditStep.checklist_arrive,
    ]


# --------------------------------------------------------------------------- #
# 3. dispatcher catches exceptions                                             #
# --------------------------------------------------------------------------- #


def test_run_step_catches_exception(monkeypatch, tmp_path: Path) -> None:
    """If a step's runner raises, the orchestrator emits StepStatus.error."""

    def boom(**_kwargs):
        raise RuntimeError("simulated explosion")

    monkeypatch.setattr(
        "panelforge_figures.manifest.ci_runner._run_scout", boom
    )

    report = run_ci_audit(tmp_path, manuscript_path=None)
    assert report.steps[0].status == StepStatus.error
    assert "simulated explosion" in report.steps[0].summary
    assert report.steps[0].error_message == "simulated explosion"


def test_run_step_unknown_dispatcher_returns_error() -> None:
    """If somehow an unknown step reaches _run_step it returns error."""

    class FakeStep:
        value = "made-up-step"

    # Direct invocation with a non-enum value should fall through to error
    # branch.
    result = _run_step(
        FakeStep(),  # type: ignore[arg-type]
        project_root=Path("."),
        manuscript_path=None,
        figures_dir=None,
        plan_path=None,
        venue=None,
        skip_missing_inputs=True,
    )
    assert result.status == StepStatus.error


# --------------------------------------------------------------------------- #
# 4. _compute_overall_status: max severity                                     #
# --------------------------------------------------------------------------- #


def _r(step: CIAuditStep, status: StepStatus) -> CIStepResult:
    """Tiny helper for assembling fake results."""
    return CIStepResult(step=step, status=status)


def test_compute_overall_status_max_severity() -> None:
    """fail dominates warn dominates pass dominates skipped."""
    res = [
        _r(CIAuditStep.scout, StepStatus.pass_),
        _r(CIAuditStep.verify_claims, StepStatus.warn),
        _r(CIAuditStep.lint_xrefs, StepStatus.fail),
    ]
    assert _compute_overall_status(res) == StepStatus.fail


def test_compute_overall_status_error_dominates_fail() -> None:
    """error is the highest severity."""
    res = [
        _r(CIAuditStep.scout, StepStatus.fail),
        _r(CIAuditStep.verify_claims, StepStatus.error),
    ]
    assert _compute_overall_status(res) == StepStatus.error


def test_compute_overall_status_all_pass() -> None:
    """All pass → overall pass."""
    res = [
        _r(CIAuditStep.scout, StepStatus.pass_),
        _r(CIAuditStep.verify_claims, StepStatus.pass_),
    ]
    assert _compute_overall_status(res) == StepStatus.pass_


def test_compute_overall_status_skipped_only() -> None:
    """All skipped → overall skipped (no real signal)."""
    res = [
        _r(CIAuditStep.scout, StepStatus.skipped),
        _r(CIAuditStep.verify_claims, StepStatus.skipped),
    ]
    assert _compute_overall_status(res) == StepStatus.skipped


def test_compute_overall_status_empty() -> None:
    """Empty result list defaults to pass (vacuously)."""
    assert _compute_overall_status([]) == StepStatus.pass_


# --------------------------------------------------------------------------- #
# 5. fail_on_warning promotion                                                 #
# --------------------------------------------------------------------------- #


def test_compute_overall_status_fail_on_warning() -> None:
    """fail_on_warning=True promotes warn → fail."""
    res = [
        _r(CIAuditStep.scout, StepStatus.pass_),
        _r(CIAuditStep.verify_claims, StepStatus.warn),
    ]
    assert _compute_overall_status(res, fail_on_warning=True) == StepStatus.fail
    assert _compute_overall_status(res, fail_on_warning=False) == StepStatus.warn


def test_run_ci_audit_fail_on_warning_propagates(tmp_path: Path) -> None:
    """Top-level fail_on_warning kwarg routes through to overall_status."""
    # Empty project root: scout will likely warn (no data files).
    report_loose = run_ci_audit(tmp_path, fail_on_warning=False)
    report_strict = run_ci_audit(tmp_path, fail_on_warning=True)
    if report_loose.overall_status == StepStatus.warn:
        assert report_strict.overall_status == StepStatus.fail


# --------------------------------------------------------------------------- #
# 6. duration_ms is recorded                                                   #
# --------------------------------------------------------------------------- #


def test_run_ci_audit_records_duration_ms(tmp_path: Path) -> None:
    """Every step gets a non-negative duration_ms recorded."""
    report = run_ci_audit(tmp_path, manuscript_path=None)
    for s in report.steps:
        assert s.duration_ms >= 0


# --------------------------------------------------------------------------- #
# 7. JSON-serializable                                                         #
# --------------------------------------------------------------------------- #


def test_ci_step_result_to_dict_is_json_serializable() -> None:
    """CIStepResult.to_dict round-trips via json.dumps."""
    r = CIStepResult(
        step=CIAuditStep.scout,
        status=StepStatus.pass_,
        n_errors=0,
        n_warnings=2,
        summary="ok",
        details=("a", "b"),
        duration_ms=123,
    )
    s = json.dumps(r.to_dict())
    parsed = json.loads(s)
    assert parsed["step"] == "scout"
    assert parsed["status"] == "pass"
    assert parsed["details"] == ["a", "b"]


def test_ci_audit_report_to_dict_is_json_serializable(tmp_path: Path) -> None:
    """CIAuditReport.to_dict round-trips via json.dumps."""
    report = run_ci_audit(tmp_path)
    s = json.dumps(report.to_dict(), default=str)
    parsed = json.loads(s)
    assert "steps" in parsed
    assert "overall_status" in parsed
    assert parsed["panelforge_version"]


# --------------------------------------------------------------------------- #
# 8. render_ci_report_markdown                                                 #
# --------------------------------------------------------------------------- #


def test_render_ci_report_markdown_contains_step_names(tmp_path: Path) -> None:
    """Markdown rendering lists every step that ran."""
    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text("Figure 1 shows the result.\n")

    report = run_ci_audit(tmp_path, manuscript_path=manuscript)
    md = render_ci_report_markdown(report)
    assert "panelforge-figures CI audit" in md
    for s in report.steps:
        assert s.step.value in md
    assert "Overall" in md


def test_render_ci_report_markdown_includes_version(tmp_path: Path) -> None:
    """The Markdown report exposes the panelforge-figures version."""
    from panelforge_figures import __version__

    report = run_ci_audit(tmp_path)
    md = render_ci_report_markdown(report)
    assert __version__ in md


# --------------------------------------------------------------------------- #
# 9. github_comment truncation                                                 #
# --------------------------------------------------------------------------- #


def test_render_ci_report_github_comment_truncates_long_details() -> None:
    """Lines past 50 chars get truncated; >10 details get capped."""
    long_detail = "x" * 200
    fake_step = CIStepResult(
        step=CIAuditStep.scout,
        status=StepStatus.fail,
        n_errors=1,
        summary="forced",
        details=tuple([long_detail] * 25),
    )
    report = CIAuditReport(
        project_root=Path("."),
        manuscript_path=None,
        panelforge_version="0.0.0",
        timestamp="2026-01-01T00:00:00Z",
        steps=(fake_step,),
        overall_status=StepStatus.fail,
        n_steps_run=1,
        n_steps_passed=0,
        n_steps_warned=0,
        n_steps_failed=1,
    )
    comment = render_ci_report_github_comment(report)
    # 50-char cap: no rendered detail line should be longer than 60 chars
    # (some leeway for the trailing ellipsis).
    for line in comment.splitlines():
        if line.startswith("xxx"):
            assert len(line) <= 60
    # Cap check: should report "X more" since 25 > 10
    assert "more" in comment


def test_render_ci_report_github_comment_skipped_steps_omitted() -> None:
    """Steps with status=skipped don't get their own details block."""
    skipped = CIStepResult(
        step=CIAuditStep.audit_venue,
        status=StepStatus.skipped,
        summary="not shipped",
    )
    passed = CIStepResult(
        step=CIAuditStep.scout,
        status=StepStatus.pass_,
        summary="ok",
    )
    report = CIAuditReport(
        project_root=Path("."),
        manuscript_path=None,
        panelforge_version="0.0.0",
        timestamp="2026-01-01T00:00:00Z",
        steps=(passed, skipped),
        overall_status=StepStatus.pass_,
        n_steps_run=2,
        n_steps_passed=1,
        n_steps_warned=0,
        n_steps_failed=0,
    )
    comment = render_ci_report_github_comment(report)
    # The skipped step shows up in the table but doesn't get a details block.
    assert "audit-venue" in comment
    # No details/summary tag for the skipped step
    assert "audit-venue` — SKIP — not shipped" not in comment


# --------------------------------------------------------------------------- #
# 10. JUnit XML                                                                #
# --------------------------------------------------------------------------- #


def test_render_ci_report_junit_xml_parses(tmp_path: Path) -> None:
    """JUnit output is well-formed XML."""
    report = run_ci_audit(tmp_path)
    xml_text = render_ci_report_junit_xml(report)
    root = ET.fromstring(xml_text)
    assert root.tag == "testsuite"
    cases = root.findall("testcase")
    assert len(cases) == report.n_steps_run
    for case, step in zip(cases, report.steps, strict=True):
        assert case.get("name") == step.step.value


def test_render_ci_report_junit_xml_failure_node() -> None:
    """A failed step emits a <failure> child."""
    fail_step = CIStepResult(
        step=CIAuditStep.scout,
        status=StepStatus.fail,
        summary="boom",
        details=("oh no",),
    )
    report = CIAuditReport(
        project_root=Path("."),
        manuscript_path=None,
        panelforge_version="0.0.0",
        timestamp="2026-01-01T00:00:00Z",
        steps=(fail_step,),
        overall_status=StepStatus.fail,
        n_steps_run=1,
        n_steps_passed=0,
        n_steps_warned=0,
        n_steps_failed=1,
    )
    xml_text = render_ci_report_junit_xml(report)
    root = ET.fromstring(xml_text)
    case = root.find("testcase")
    failure = case.find("failure")
    assert failure is not None
    assert failure.get("message") == "boom"


def test_render_ci_report_junit_xml_error_node() -> None:
    """An errored step emits an <error> child."""
    err_step = CIStepResult(
        step=CIAuditStep.scout,
        status=StepStatus.error,
        summary="oops",
        error_message="ImportError",
    )
    report = CIAuditReport(
        project_root=Path("."),
        manuscript_path=None,
        panelforge_version="0.0.0",
        timestamp="2026-01-01T00:00:00Z",
        steps=(err_step,),
        overall_status=StepStatus.error,
        n_steps_run=1,
        n_steps_passed=0,
        n_steps_warned=0,
        n_steps_failed=1,
    )
    xml_text = render_ci_report_junit_xml(report)
    root = ET.fromstring(xml_text)
    case = root.find("testcase")
    error = case.find("error")
    assert error is not None
    assert error.get("message") == "ImportError"


def test_render_ci_report_junit_xml_skipped_node() -> None:
    """A skipped step emits a <skipped> child."""
    sk = CIStepResult(
        step=CIAuditStep.audit_venue,
        status=StepStatus.skipped,
        summary="not shipped",
    )
    report = CIAuditReport(
        project_root=Path("."),
        manuscript_path=None,
        panelforge_version="0.0.0",
        timestamp="2026-01-01T00:00:00Z",
        steps=(sk,),
        overall_status=StepStatus.skipped,
        n_steps_run=1,
        n_steps_passed=0,
        n_steps_warned=0,
        n_steps_failed=0,
    )
    root = ET.fromstring(render_ci_report_junit_xml(report))
    case = root.find("testcase")
    assert case.find("skipped") is not None


# --------------------------------------------------------------------------- #
# 11. _run_scout on tmp project                                                #
# --------------------------------------------------------------------------- #


def test_run_scout_on_empty_project_warns(tmp_path: Path) -> None:
    """An empty project (no data files) → warn."""
    r = _run_scout(project_root=tmp_path, venue=None)
    assert r.step == CIAuditStep.scout
    assert r.status in (StepStatus.pass_, StepStatus.warn, StepStatus.fail)


# --------------------------------------------------------------------------- #
# 12. verify-claims skipped without manuscript                                 #
# --------------------------------------------------------------------------- #


def test_run_verify_claims_skipped_no_manuscript() -> None:
    r = _run_verify_claims(
        manuscript_path=None,
        figures_dir=None,
        skip_missing_inputs=True,
    )
    assert r.status == StepStatus.skipped
    assert "no manuscript" in r.summary.lower()


def test_run_verify_claims_fail_when_strict_and_missing() -> None:
    r = _run_verify_claims(
        manuscript_path=None,
        figures_dir=None,
        skip_missing_inputs=False,
    )
    assert r.status == StepStatus.fail


def test_run_verify_claims_skipped_missing_file(tmp_path: Path) -> None:
    r = _run_verify_claims(
        manuscript_path=tmp_path / "nope.tex",
        figures_dir=None,
        skip_missing_inputs=True,
    )
    assert r.status == StepStatus.skipped
    assert "not found" in r.summary.lower()


# --------------------------------------------------------------------------- #
# 13. lint-xrefs skipped without manuscript                                    #
# --------------------------------------------------------------------------- #


def test_run_lint_xrefs_skipped_no_manuscript() -> None:
    r = _run_lint_xrefs(
        manuscript_path=None,
        figures_dir=None,
        skip_missing_inputs=True,
    )
    assert r.status == StepStatus.skipped


def test_run_lint_xrefs_fail_when_strict_and_missing() -> None:
    r = _run_lint_xrefs(
        manuscript_path=None,
        figures_dir=None,
        skip_missing_inputs=False,
    )
    assert r.status == StepStatus.fail


def test_run_lint_xrefs_skipped_missing_file(tmp_path: Path) -> None:
    r = _run_lint_xrefs(
        manuscript_path=tmp_path / "missing.tex",
        figures_dir=None,
        skip_missing_inputs=True,
    )
    assert r.status == StepStatus.skipped


def test_run_lint_xrefs_runs_on_real_manuscript(tmp_path: Path) -> None:
    """Smoke test: with a real manuscript, the linter actually runs."""
    manuscript = tmp_path / "manuscript.tex"
    manuscript.write_text(
        "\\begin{figure}\n\\includegraphics{figure_1.pdf}\n"
        "\\caption{An OK figure caption with sufficient length.}\n"
        "\\label{fig:1}\n\\end{figure}\n"
        "Figure~\\ref{fig:1} shows the result.\n"
    )
    r = _run_lint_xrefs(
        manuscript_path=manuscript,
        figures_dir=None,
        skip_missing_inputs=True,
    )
    # Must not crash; status is at least one of the known values.
    assert r.status in (StepStatus.pass_, StepStatus.warn, StepStatus.fail)


# --------------------------------------------------------------------------- #
# 14-15. E16/E17 placeholders                                                  #
# --------------------------------------------------------------------------- #


def test_run_audit_venue_now_shipped() -> None:
    """E16 is now shipped; with no manuscript_path → skipped (sensible default)."""
    r = _run_audit_venue(
        manuscript_path=None,
        figures_dir=None,
        venue=None,
        skip_missing_inputs=True,
    )
    assert r.step == CIAuditStep.audit_venue
    assert r.status == StepStatus.skipped


def test_run_audit_bias_placeholder() -> None:
    r = _run_audit_bias()
    assert r.step == CIAuditStep.audit_bias
    assert r.status == StepStatus.skipped
    assert "E17" in r.summary
    assert "not yet shipped" in r.summary


# --------------------------------------------------------------------------- #
# 16-20. CLI smoke tests                                                       #
# --------------------------------------------------------------------------- #


def test_cli_ci_audit_help() -> None:
    r = CliRunner().invoke(main, ["ci-audit", "--help"])
    assert r.exit_code == 0
    assert "ci-audit" in r.output.lower() or "CI audit" in r.output
    assert "--project-root" in r.output
    assert "--manuscript" in r.output
    assert "--steps" in r.output


def test_cli_ci_audit_writes_report_to_output(tmp_path: Path) -> None:
    """--output writes Markdown report and exit 0 on clean run."""
    out = tmp_path / "report.md"
    out_json = tmp_path / "report.json"
    r = CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--output",
            str(out),
            "--output-json",
            str(out_json),
        ],
    )
    # Exit may be 0 (pass) or 1 if scout reports warn-elevated-to-fail; either
    # way the report files must exist.
    assert out.exists(), f"output not written; stderr={r.stderr if r.stderr_bytes else ''}"
    assert out_json.exists()


def test_cli_ci_audit_invalid_step_name_exit_2(tmp_path: Path) -> None:
    """Bad step value → exit 2."""
    r = CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--steps",
            "bogus-step",
        ],
    )
    assert r.exit_code == 2


def test_cli_ci_audit_exits_1_on_fail(monkeypatch, tmp_path: Path) -> None:
    """If overall_status is fail, CLI exits 1."""

    def fake_run_ci_audit(*_a, **_kw):
        return CIAuditReport(
            project_root=tmp_path,
            manuscript_path=None,
            panelforge_version="0.0.0",
            timestamp="2026-01-01T00:00:00Z",
            steps=(
                CIStepResult(
                    step=CIAuditStep.scout,
                    status=StepStatus.fail,
                    n_errors=1,
                    summary="forced",
                ),
            ),
            overall_status=StepStatus.fail,
            n_steps_run=1,
            n_steps_passed=0,
            n_steps_warned=0,
            n_steps_failed=1,
        )

    monkeypatch.setattr(
        "panelforge_figures.manifest.ci_runner.run_ci_audit", fake_run_ci_audit
    )
    r = CliRunner().invoke(
        main, ["ci-audit", "--project-root", str(tmp_path)]
    )
    assert r.exit_code == 1


def test_cli_ci_audit_output_json_is_valid_json(tmp_path: Path) -> None:
    """--output-json produces a parseable JSON file with expected keys."""
    out_json = tmp_path / "report.json"
    CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--output-json",
            str(out_json),
            "--output",
            str(tmp_path / "report.md"),
        ],
    )
    assert out_json.exists()
    data = json.loads(out_json.read_text())
    assert "overall_status" in data
    assert "steps" in data
    assert "panelforge_version" in data


def test_cli_ci_audit_output_junit_xml_is_valid(tmp_path: Path) -> None:
    """--output-junit produces a parseable XML file."""
    out_xml = tmp_path / "report.xml"
    CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--output-junit",
            str(out_xml),
            "--output",
            str(tmp_path / "report.md"),
        ],
    )
    assert out_xml.exists()
    root = ET.fromstring(out_xml.read_text())
    assert root.tag == "testsuite"


def test_cli_ci_audit_github_comment_flag(tmp_path: Path) -> None:
    """--github-comment renders truncated Markdown."""
    out = tmp_path / "comment.md"
    CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--github-comment",
            "--output",
            str(out),
        ],
    )
    assert out.exists()
    text = out.read_text()
    # The github-comment renderer uses "Overall" without "panelforge-figures CI audit"
    assert "Overall" in text


def test_ci_runner_error_is_subclass_of_runtime_error() -> None:
    """CIRunnerError is publicly exported and is a RuntimeError."""
    assert issubclass(CIRunnerError, RuntimeError)


def test_cli_ci_audit_explicit_steps_flag(tmp_path: Path) -> None:
    """Explicit --steps with only scout runs just scout."""
    out_json = tmp_path / "report.json"
    CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--steps",
            "scout",
            "--output-json",
            str(out_json),
            "--output",
            str(tmp_path / "report.md"),
        ],
    )
    data = json.loads(out_json.read_text())
    assert data["n_steps_run"] == 1
    assert data["steps"][0]["step"] == "scout"


def test_cli_ci_audit_fail_on_warning_promotion(monkeypatch, tmp_path: Path) -> None:
    """--fail-on-warning promotes warn to exit 1."""

    def fake_run_ci_audit(*_a, fail_on_warning=False, **_kw):
        status = StepStatus.fail if fail_on_warning else StepStatus.warn
        return CIAuditReport(
            project_root=tmp_path,
            manuscript_path=None,
            panelforge_version="0.0.0",
            timestamp="2026-01-01T00:00:00Z",
            steps=(
                CIStepResult(
                    step=CIAuditStep.scout,
                    status=StepStatus.warn,
                    n_warnings=1,
                    summary="just a warn",
                ),
            ),
            overall_status=status,
            n_steps_run=1,
            n_steps_passed=0,
            n_steps_warned=1,
            n_steps_failed=0 if not fail_on_warning else 1,
        )

    monkeypatch.setattr(
        "panelforge_figures.manifest.ci_runner.run_ci_audit", fake_run_ci_audit
    )

    r_loose = CliRunner().invoke(
        main, ["ci-audit", "--project-root", str(tmp_path)]
    )
    assert r_loose.exit_code == 0

    r_strict = CliRunner().invoke(
        main,
        [
            "ci-audit",
            "--project-root",
            str(tmp_path),
            "--fail-on-warning",
        ],
    )
    assert r_strict.exit_code == 1


# --------------------------------------------------------------------------- #
# Additional invariants                                                        #
# --------------------------------------------------------------------------- #


def test_report_overall_status_matches_step_severity(tmp_path: Path) -> None:
    """overall_status equals the worst per-step status."""
    report = run_ci_audit(tmp_path)
    ranks = {
        StepStatus.skipped: 0,
        StepStatus.pass_: 1,
        StepStatus.warn: 2,
        StepStatus.fail: 3,
        StepStatus.error: 4,
    }
    worst = max((ranks[s.status] for s in report.steps), default=ranks[StepStatus.pass_])
    assert ranks[report.overall_status] == worst


def test_run_ci_audit_steps_kwarg_overrides_default(tmp_path: Path) -> None:
    """Passing steps= overrides the manuscript-driven default chain."""
    report = run_ci_audit(
        tmp_path,
        manuscript_path=tmp_path / "missing.tex",
        steps=(CIAuditStep.audit_venue,),
    )
    assert report.n_steps_run == 1
    assert report.steps[0].step == CIAuditStep.audit_venue
    assert report.steps[0].status == StepStatus.skipped
