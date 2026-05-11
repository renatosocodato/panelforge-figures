"""Bundled CI audit runner.

Runs the canonical audit chain in one operation, returns a structured report
suitable for PR-comment rendering. Each step is opt-out-able and sandboxed:
exceptions in a single step become a ``StepStatus.error`` entry and do not
abort the chain.

Pipeline
--------
* ``scout``                     — read-only project inventory + figure plan
* ``verify-claims``             — Figure-N claim consistency (requires manuscript)
* ``lint-xrefs``                — cross-reference linter (requires manuscript)
* ``checklist-{arrive,consort,stard,miqe}`` — reporting checklists
* ``audit-venue``               — venue-specific audit (E16)
* ``audit-bias``                — figure-bias audit (E17; structural,
  metadata-driven)

Each step lazy-imports its module so missing optional dependencies in
unrelated chains do not propagate.  The overall verdict is the worst severity
across all steps that actually ran.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

__all__ = [
    "CIAuditStep",
    "CIStepResult",
    "CIAuditReport",
    "StepStatus",
    "CIRunnerError",
    "run_ci_audit",
    "render_ci_report_markdown",
    "render_ci_report_github_comment",
    "render_ci_report_junit_xml",
]


# --------------------------------------------------------------------------- #
# Enums + dataclasses                                                          #
# --------------------------------------------------------------------------- #


class StepStatus(StrEnum):
    """Verdict for a single CI step.

    Ordering by severity (low → high):
    ``skipped`` < ``pass_`` < ``warn`` < ``fail`` ≈ ``error``.
    ``error`` is an internal exception, ``fail`` is a domain-level failure.
    """

    pass_ = "pass"
    warn = "warn"
    fail = "fail"
    skipped = "skipped"
    error = "error"


class CIAuditStep(StrEnum):
    """Discriminator for a step in the audit chain."""

    scout = "scout"
    verify_claims = "verify-claims"
    lint_xrefs = "lint-xrefs"
    checklist_arrive = "checklist-arrive"
    checklist_consort = "checklist-consort"
    checklist_stard = "checklist-stard"
    checklist_miqe = "checklist-miqe"
    audit_venue = "audit-venue"           # E16
    audit_bias = "audit-bias"             # E17 — figure-bias audit


@dataclass(frozen=True)
class CIStepResult:
    """Outcome of a single CI step.

    Attributes
    ----------
    step
        Which step ran.
    status
        Triage verdict; see :class:`StepStatus`.
    n_errors, n_warnings, n_info
        Optional finding counts so the PR comment can render a summary table.
    summary
        One-line human verdict (e.g. ``"3 errors, 1 warning"``).
    details
        Per-finding lines for the Markdown report.  Bounded (caller decides).
    duration_ms
        Wall-clock time spent in this step.
    error_message
        Populated when ``status == StepStatus.error``.
    """

    step: CIAuditStep
    status: StepStatus
    n_errors: int = 0
    n_warnings: int = 0
    n_info: int = 0
    summary: str = ""
    details: tuple[str, ...] = ()
    duration_ms: int = 0
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step.value,
            "status": self.status.value,
            "n_errors": self.n_errors,
            "n_warnings": self.n_warnings,
            "n_info": self.n_info,
            "summary": self.summary,
            "details": list(self.details),
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class CIAuditReport:
    """End-to-end audit report.

    Aggregates per-step :class:`CIStepResult` objects with a top-level
    severity verdict and per-status counters.  JSON-serialisable via
    :meth:`to_dict`.
    """

    project_root: Path
    manuscript_path: Path | None
    panelforge_version: str
    timestamp: str
    steps: tuple[CIStepResult, ...]
    overall_status: StepStatus
    n_steps_run: int
    n_steps_passed: int
    n_steps_warned: int
    n_steps_failed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": str(self.project_root),
            "manuscript_path": (
                str(self.manuscript_path) if self.manuscript_path is not None else None
            ),
            "panelforge_version": self.panelforge_version,
            "timestamp": self.timestamp,
            "steps": [s.to_dict() for s in self.steps],
            "overall_status": self.overall_status.value,
            "n_steps_run": self.n_steps_run,
            "n_steps_passed": self.n_steps_passed,
            "n_steps_warned": self.n_steps_warned,
            "n_steps_failed": self.n_steps_failed,
        }


class CIRunnerError(RuntimeError):
    """Raised on configuration errors before any step runs."""


# --------------------------------------------------------------------------- #
# Severity ranking                                                             #
# --------------------------------------------------------------------------- #


_SEVERITY_RANK: dict[StepStatus, int] = {
    StepStatus.skipped: 0,
    StepStatus.pass_: 1,
    StepStatus.warn: 2,
    StepStatus.fail: 3,
    StepStatus.error: 4,
}


def _compute_overall_status(
    results: Sequence[CIStepResult],
    *,
    fail_on_warning: bool = False,
) -> StepStatus:
    """Return the worst severity across ``results``.

    If ``fail_on_warning`` is ``True`` and the worst seen is ``warn``,
    the result is promoted to ``fail``.
    """
    if not results:
        return StepStatus.pass_

    worst = StepStatus.skipped
    for r in results:
        if _SEVERITY_RANK[r.status] > _SEVERITY_RANK[worst]:
            worst = r.status

    if fail_on_warning and worst == StepStatus.warn:
        return StepStatus.fail
    return worst


# --------------------------------------------------------------------------- #
# Default-step selection                                                       #
# --------------------------------------------------------------------------- #


def _default_steps(
    manuscript_path: Path | None,
) -> tuple[CIAuditStep, ...]:
    """Pick a sensible default chain.

    * No manuscript → scout only.
    * Has manuscript → scout + verify-claims + lint-xrefs + ARRIVE checklist.
    """
    if manuscript_path is None:
        return (CIAuditStep.scout,)
    return (
        CIAuditStep.scout,
        CIAuditStep.verify_claims,
        CIAuditStep.lint_xrefs,
        CIAuditStep.checklist_arrive,
    )


# --------------------------------------------------------------------------- #
# Per-step runners                                                             #
# --------------------------------------------------------------------------- #


def _run_scout(
    *,
    project_root: Path,
    venue: str | None,
    **_: Any,
) -> CIStepResult:
    """Run the read-only scout pipeline.  Failure = exception from scout."""
    from panelforge_figures.manifest.scout import scout_project

    report = scout_project(
        project_root,
        venue=venue or "cell",
        use_mock_novelty=True,
        target_novelty="none",
        manuscript_policy="preserve",
    )

    n_data_files = len(report.inventory.data_files)
    n_figures = len(report.figure_plan.figures)
    notes = list(report.notes)

    # Verdict: pass if scout produced any figure plan; warn if we have no
    # data files (likely a setup issue); pass otherwise.
    if n_data_files == 0:
        status = StepStatus.warn
        summary = "no data files discovered"
    elif n_figures == 0:
        status = StepStatus.warn
        summary = f"{n_data_files} data files but no figures planned"
    else:
        status = StepStatus.pass_
        summary = f"{n_figures} figures planned across {n_data_files} data files"

    details: list[str] = []
    for fig in report.figure_plan.figures:
        title = getattr(fig, "title", "") or getattr(fig, "figure_id", "fig")
        details.append(f"- {title}")
    for n in notes:
        details.append(f"note: {n}")

    return CIStepResult(
        step=CIAuditStep.scout,
        status=status,
        n_info=n_figures,
        summary=summary,
        details=tuple(details),
    )


def _run_verify_claims(
    *,
    manuscript_path: Path | None,
    figures_dir: Path | None,
    skip_missing_inputs: bool,
    **_: Any,
) -> CIStepResult:
    """Run the claim-check pipeline."""
    if manuscript_path is None:
        if skip_missing_inputs:
            return CIStepResult(
                step=CIAuditStep.verify_claims,
                status=StepStatus.skipped,
                summary="no manuscript provided",
            )
        return CIStepResult(
            step=CIAuditStep.verify_claims,
            status=StepStatus.fail,
            summary="manuscript_path is required",
        )

    if not manuscript_path.exists():
        if skip_missing_inputs:
            return CIStepResult(
                step=CIAuditStep.verify_claims,
                status=StepStatus.skipped,
                summary=f"manuscript not found: {manuscript_path}",
            )
        return CIStepResult(
            step=CIAuditStep.verify_claims,
            status=StepStatus.fail,
            summary=f"manuscript not found: {manuscript_path}",
        )

    figures = figures_dir or (manuscript_path.parent / "panelforge_workspace" / "figures")
    if not figures.exists() and skip_missing_inputs:
        return CIStepResult(
            step=CIAuditStep.verify_claims,
            status=StepStatus.skipped,
            summary=f"figures dir missing: {figures}",
        )

    from panelforge_figures.manifest.claim_check import verify_manuscript

    report = verify_manuscript(manuscript_path, figures)

    n_unsupported = report.n_unsupported
    n_unverifiable = report.n_unverifiable
    n_supported = report.n_supported

    if n_unsupported > 0:
        status = StepStatus.fail
    elif n_unverifiable > 0:
        status = StepStatus.warn
    else:
        status = StepStatus.pass_

    summary = (
        f"{report.n_claims} claims; "
        f"{n_supported} supported, "
        f"{n_unsupported} unsupported, "
        f"{n_unverifiable} unverifiable"
    )

    details: list[str] = []
    for v in report.claims:
        if v.verdict.value in ("unsupported", "unverifiable"):
            details.append(
                f"- [{v.verdict.value}] {v.claim.figure_id}: {v.rationale}"
            )

    return CIStepResult(
        step=CIAuditStep.verify_claims,
        status=status,
        n_errors=n_unsupported,
        n_warnings=n_unverifiable,
        n_info=n_supported,
        summary=summary,
        details=tuple(details),
    )


def _run_lint_xrefs(
    *,
    manuscript_path: Path | None,
    figures_dir: Path | None,
    skip_missing_inputs: bool,
    **_: Any,
) -> CIStepResult:
    """Run the cross-reference linter."""
    if manuscript_path is None:
        if skip_missing_inputs:
            return CIStepResult(
                step=CIAuditStep.lint_xrefs,
                status=StepStatus.skipped,
                summary="no manuscript provided",
            )
        return CIStepResult(
            step=CIAuditStep.lint_xrefs,
            status=StepStatus.fail,
            summary="manuscript_path is required",
        )

    if not manuscript_path.exists():
        if skip_missing_inputs:
            return CIStepResult(
                step=CIAuditStep.lint_xrefs,
                status=StepStatus.skipped,
                summary=f"manuscript not found: {manuscript_path}",
            )
        return CIStepResult(
            step=CIAuditStep.lint_xrefs,
            status=StepStatus.fail,
            summary=f"manuscript not found: {manuscript_path}",
        )

    from panelforge_figures.manifest.xref_linter import lint_xrefs

    fdir = figures_dir if (figures_dir and figures_dir.exists()) else None
    report = lint_xrefs(manuscript_path, figures_dir=fdir)

    if report.n_errors > 0:
        status = StepStatus.fail
    elif report.n_warnings > 0:
        status = StepStatus.warn
    else:
        status = StepStatus.pass_

    summary = (
        f"{report.n_errors} errors, "
        f"{report.n_warnings} warnings, "
        f"{report.n_info} info"
    )

    details: list[str] = [
        f"- [{f.severity.value}] {f.figure_id}: {f.message}"
        for f in report.findings
    ]

    return CIStepResult(
        step=CIAuditStep.lint_xrefs,
        status=status,
        n_errors=report.n_errors,
        n_warnings=report.n_warnings,
        n_info=report.n_info,
        summary=summary,
        details=tuple(details),
    )


def _run_checklist(
    step: CIAuditStep,
    *,
    project_root: Path,
    manuscript_path: Path | None,
    plan_path: Path | None,
    **_: Any,
) -> CIStepResult:
    """Run one of the reporting checklists (ARRIVE / CONSORT / STARD / MIQE)."""
    from panelforge_figures.manifest.reporting_checklists import (
        ChecklistError,
        generate_arrive_checklist,
        generate_consort_checklist,
        generate_miqe_checklist,
        generate_stard_checklist,
    )

    generators = {
        CIAuditStep.checklist_arrive: generate_arrive_checklist,
        CIAuditStep.checklist_consort: generate_consort_checklist,
        CIAuditStep.checklist_stard: generate_stard_checklist,
        CIAuditStep.checklist_miqe: generate_miqe_checklist,
    }
    generator = generators[step]

    plan = None
    if plan_path is not None and plan_path.exists():
        try:
            from panelforge_figures.manifest.scout import load_figure_plan_yaml

            plan = load_figure_plan_yaml(plan_path)
        except Exception:
            plan = None

    try:
        checklist = generator(
            project_root, manuscript_path=manuscript_path, figure_plan=plan
        )
    except ChecklistError as exc:
        return CIStepResult(
            step=step,
            status=StepStatus.error,
            summary=f"checklist error: {exc}",
            error_message=str(exc),
        )

    total = (
        checklist.n_present
        + checklist.n_absent
        + checklist.n_not_applicable
        + checklist.n_unknown
    )
    relevant = max(total - checklist.n_not_applicable, 1)
    score = checklist.n_present / relevant
    threshold = checklist.pass_threshold

    if checklist.n_absent > 0:
        status = StepStatus.warn
    elif score < threshold:
        status = StepStatus.warn
    else:
        status = StepStatus.pass_

    summary = (
        f"{checklist.kind.value}: "
        f"{checklist.n_present}/{total} present "
        f"({checklist.n_absent} absent, "
        f"{checklist.n_not_applicable} n/a, "
        f"{checklist.n_unknown} unknown)"
    )

    details: list[str] = []
    for item in checklist.items:
        if item.status.value in ("absent", "unknown"):
            details.append(f"- [{item.status.value}] {item.item_id}: {item.description[:80]}")

    return CIStepResult(
        step=step,
        status=status,
        n_errors=0,
        n_warnings=checklist.n_absent + checklist.n_unknown,
        n_info=checklist.n_present,
        summary=summary,
        details=tuple(details),
    )


def _run_audit_venue(
    *,
    manuscript_path: Path | None,
    figures_dir: Path | None,
    venue: str | None,
    skip_missing_inputs: bool,
    **_: Any,
) -> CIStepResult:
    """E16 — venue-specific audit (figure caps, abstract, statements, etc.).

    Skipped when no manuscript or no venue is supplied.  Errors map to
    ``StepStatus.fail``; warnings map to ``StepStatus.warn``; otherwise
    ``StepStatus.pass_``.
    """
    if manuscript_path is None:
        return CIStepResult(
            step=CIAuditStep.audit_venue,
            status=StepStatus.skipped if skip_missing_inputs else StepStatus.fail,
            summary="no manuscript provided",
        )
    if not manuscript_path.exists():
        return CIStepResult(
            step=CIAuditStep.audit_venue,
            status=StepStatus.skipped if skip_missing_inputs else StepStatus.fail,
            summary=f"manuscript not found: {manuscript_path}",
        )
    if not venue:
        return CIStepResult(
            step=CIAuditStep.audit_venue,
            status=StepStatus.skipped if skip_missing_inputs else StepStatus.fail,
            summary="no venue provided (pass --venue)",
        )

    from panelforge_figures.manifest.venue_auditor import (
        Venue,
        VenueAuditorError,
        audit_venue,
    )

    # Resolve venue string to the enum (default unknown values to "plain").
    try:
        venue_enum = Venue(venue)
    except ValueError:
        return CIStepResult(
            step=CIAuditStep.audit_venue,
            status=StepStatus.skipped if skip_missing_inputs else StepStatus.fail,
            summary=(
                f"unknown venue: {venue!r}; "
                f"expected one of {[v.value for v in Venue]}"
            ),
        )

    fdir = figures_dir if (figures_dir and figures_dir.exists()) else None

    try:
        report = audit_venue(
            manuscript_path,
            venue=venue_enum,
            figures_dir=fdir,
        )
    except VenueAuditorError as exc:
        return CIStepResult(
            step=CIAuditStep.audit_venue,
            status=StepStatus.error,
            summary=f"venue auditor error: {exc}",
            error_message=str(exc),
        )

    if report.n_errors > 0:
        status = StepStatus.fail
    elif report.n_warnings > 0:
        status = StepStatus.warn
    else:
        status = StepStatus.pass_

    summary = (
        f"{report.venue.value}: {report.n_errors} error(s), "
        f"{report.n_warnings} warning(s), {report.n_info} info "
        f"({report.overall_verdict})"
    )

    details: list[str] = [
        f"- [{v.severity.value}] {v.rule_id}: {v.message}"
        for v in report.violations
    ]

    return CIStepResult(
        step=CIAuditStep.audit_venue,
        status=status,
        n_errors=report.n_errors,
        n_warnings=report.n_warnings,
        n_info=report.n_info,
        summary=summary,
        details=tuple(details),
    )


def _run_audit_bias(
    *,
    figures_dir: Path | None = None,
    skip_missing_inputs: bool = True,
    **_: Any,
) -> CIStepResult:
    """Run E17 figure-bias auditor across rendered figures."""
    from panelforge_figures.manifest.bias_auditor import audit_bias_across_directory

    if figures_dir is None or not Path(figures_dir).exists():
        if skip_missing_inputs:
            return CIStepResult(
                step=CIAuditStep.audit_bias,
                status=StepStatus.skipped,
                summary="no figures directory",
            )
        return CIStepResult(
            step=CIAuditStep.audit_bias,
            status=StepStatus.error,
            summary="figures directory missing",
            error_message=f"path not found: {figures_dir}",
        )

    report = audit_bias_across_directory(Path(figures_dir))
    if report.overall_verdict == "honest":
        status = StepStatus.pass_
    elif report.overall_verdict == "needs_review":
        status = StepStatus.warn
    else:  # concerning
        status = StepStatus.fail

    details = tuple(
        f"[{f.severity.value}] {f.figure_id}: {f.message}"
        for f in report.findings[:10]
    )
    return CIStepResult(
        step=CIAuditStep.audit_bias,
        status=status,
        n_errors=report.n_errors,
        n_warnings=report.n_warnings,
        n_info=report.n_info,
        summary=(
            f"verdict: {report.overall_verdict} · "
            f"{report.n_figures_inspected} figures: "
            f"{report.n_errors} errors, {report.n_warnings} warnings"
        ),
        details=details,
    )


def _run_step(
    step: CIAuditStep,
    *,
    project_root: Path,
    manuscript_path: Path | None,
    figures_dir: Path | None,
    plan_path: Path | None,
    venue: str | None,
    skip_missing_inputs: bool,
) -> CIStepResult:
    """Dispatch one step.  Caller wraps in try/except for global sandboxing."""
    kwargs = {
        "project_root": project_root,
        "manuscript_path": manuscript_path,
        "figures_dir": figures_dir,
        "plan_path": plan_path,
        "venue": venue,
        "skip_missing_inputs": skip_missing_inputs,
    }

    if step == CIAuditStep.scout:
        return _run_scout(**kwargs)
    if step == CIAuditStep.verify_claims:
        return _run_verify_claims(**kwargs)
    if step == CIAuditStep.lint_xrefs:
        return _run_lint_xrefs(**kwargs)
    if step in (
        CIAuditStep.checklist_arrive,
        CIAuditStep.checklist_consort,
        CIAuditStep.checklist_stard,
        CIAuditStep.checklist_miqe,
    ):
        return _run_checklist(step, **kwargs)
    if step == CIAuditStep.audit_venue:
        return _run_audit_venue(**kwargs)
    if step == CIAuditStep.audit_bias:
        return _run_audit_bias(**kwargs)

    return CIStepResult(
        step=step,
        status=StepStatus.error,
        summary=f"unknown step: {step}",
        error_message=f"no dispatcher for {step}",
    )


# --------------------------------------------------------------------------- #
# Orchestrator                                                                 #
# --------------------------------------------------------------------------- #


def run_ci_audit(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    plan_path: Path | None = None,
    steps: tuple[CIAuditStep, ...] | None = None,
    venue: str | None = None,
    fail_on_warning: bool = False,
    skip_missing_inputs: bool = True,
) -> CIAuditReport:
    """Run the bundled CI audit chain.

    Parameters
    ----------
    project_root
        Path to a panelforge project root (directory).
    manuscript_path
        Optional path to the manuscript ``.tex`` / ``.md``.  When ``None``,
        steps that need a manuscript are skipped (see ``skip_missing_inputs``).
    figures_dir
        Directory containing rendered figures (defaults to
        ``project_root/panelforge_workspace/figures`` when relevant).
    plan_path
        Optional path to an existing ``figures_plan.yaml`` (passed into
        the checklist generators for contract-evidence classification).
    steps
        Explicit step list.  When ``None``, picks a default based on whether
        ``manuscript_path`` is provided (see :func:`_default_steps`).
    venue
        Target venue for venue-specific audits.  Currently consumed only by
        scout's plan synthesis.
    fail_on_warning
        Promote a ``warn`` overall verdict to ``fail`` (for stricter CI).
    skip_missing_inputs
        When ``True`` (default), steps with absent inputs are reported as
        ``skipped`` rather than ``fail``.  Useful for projects in early
        phases where the manuscript is intentionally absent.

    Returns
    -------
    CIAuditReport
        JSON-serialisable structured report.  Per-step exceptions are
        captured as ``StepStatus.error`` and do not propagate.
    """
    from panelforge_figures import __version__

    steps_to_run = steps if steps is not None else _default_steps(manuscript_path)
    results: list[CIStepResult] = []

    for step in steps_to_run:
        t0 = time.monotonic()
        try:
            result = _run_step(
                step,
                project_root=project_root,
                manuscript_path=manuscript_path,
                figures_dir=figures_dir,
                plan_path=plan_path,
                venue=venue,
                skip_missing_inputs=skip_missing_inputs,
            )
        except Exception as exc:  # noqa: BLE001 — each step is sandboxed
            duration = int((time.monotonic() - t0) * 1000)
            results.append(
                CIStepResult(
                    step=step,
                    status=StepStatus.error,
                    summary=f"exception: {exc}",
                    error_message=str(exc),
                    duration_ms=duration,
                )
            )
            continue

        duration = int((time.monotonic() - t0) * 1000)
        results.append(replace(result, duration_ms=duration))

    overall = _compute_overall_status(results, fail_on_warning=fail_on_warning)
    timestamp = (
        datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    )

    return CIAuditReport(
        project_root=project_root,
        manuscript_path=manuscript_path,
        panelforge_version=__version__,
        timestamp=timestamp,
        steps=tuple(results),
        overall_status=overall,
        n_steps_run=len(results),
        n_steps_passed=sum(1 for r in results if r.status == StepStatus.pass_),
        n_steps_warned=sum(1 for r in results if r.status == StepStatus.warn),
        n_steps_failed=sum(
            1 for r in results if r.status in (StepStatus.fail, StepStatus.error)
        ),
    )


# --------------------------------------------------------------------------- #
# Renderers                                                                    #
# --------------------------------------------------------------------------- #


_STATUS_EMOJI: dict[StepStatus, str] = {
    StepStatus.pass_: "PASS",
    StepStatus.warn: "WARN",
    StepStatus.fail: "FAIL",
    StepStatus.error: "ERROR",
    StepStatus.skipped: "SKIP",
}


def _status_symbol(status: StepStatus) -> str:
    return _STATUS_EMOJI.get(status, status.value.upper())


def render_ci_report_markdown(report: CIAuditReport) -> str:
    """Render the full Markdown report (used for stdout / artifact)."""
    lines: list[str] = []
    lines.append("# panelforge-figures CI audit")
    lines.append("")
    lines.append(f"- **Overall**: `{report.overall_status.value}`")
    lines.append(f"- **panelforge-figures**: `{report.panelforge_version}`")
    lines.append(f"- **timestamp**: `{report.timestamp}`")
    lines.append(f"- **project root**: `{report.project_root}`")
    if report.manuscript_path is not None:
        lines.append(f"- **manuscript**: `{report.manuscript_path}`")
    lines.append(
        f"- **steps**: {report.n_steps_run} run "
        f"({report.n_steps_passed} pass, "
        f"{report.n_steps_warned} warn, "
        f"{report.n_steps_failed} fail/error)"
    )
    lines.append("")

    # ── Summary table ───────────────────────────────────────────────────
    lines.append("| Step | Status | Errors | Warnings | Duration (ms) |")
    lines.append("|------|--------|-------:|---------:|--------------:|")
    for s in report.steps:
        lines.append(
            f"| `{s.step.value}` | "
            f"{_status_symbol(s.status)} | "
            f"{s.n_errors} | "
            f"{s.n_warnings} | "
            f"{s.duration_ms} |"
        )
    lines.append("")

    # ── Per-step details ────────────────────────────────────────────────
    for s in report.steps:
        lines.append(f"## {s.step.value} — {_status_symbol(s.status)}")
        lines.append("")
        if s.summary:
            lines.append(f"_{s.summary}_")
            lines.append("")
        if s.error_message:
            lines.append(f"**error**: `{s.error_message}`")
            lines.append("")
        for d in s.details:
            lines.append(d)
        if not s.details:
            lines.append("(no findings)")
        lines.append("")

    return "\n".join(lines)


def render_ci_report_github_comment(report: CIAuditReport) -> str:
    """Render a PR-comment-sized Markdown report.

    Truncates per-finding lines past 50 chars and caps each step's details at
    10 entries.  Includes a summary table + per-step breakdown but trims the
    long-form prose.
    """
    detail_max_chars = 50
    detail_cap = 10

    lines: list[str] = []
    lines.append(f"**Overall**: `{report.overall_status.value}`  ")
    lines.append(
        f"_panelforge-figures {report.panelforge_version}_ — "
        f"{report.n_steps_run} steps, "
        f"{report.n_steps_passed} pass, "
        f"{report.n_steps_warned} warn, "
        f"{report.n_steps_failed} fail/error"
    )
    lines.append("")

    lines.append("| Step | Status | Errors | Warnings |")
    lines.append("|------|--------|-------:|---------:|")
    for s in report.steps:
        lines.append(
            f"| `{s.step.value}` | "
            f"{_status_symbol(s.status)} | "
            f"{s.n_errors} | "
            f"{s.n_warnings} |"
        )
    lines.append("")

    for s in report.steps:
        if s.status == StepStatus.skipped:
            continue
        lines.append(f"<details><summary><code>{s.step.value}</code> — {_status_symbol(s.status)} — {s.summary}</summary>")
        lines.append("")
        truncated = s.details[:detail_cap]
        for d in truncated:
            if len(d) > detail_max_chars:
                d = d[: detail_max_chars - 1] + "…"
            lines.append(d)
        if len(s.details) > detail_cap:
            lines.append(f"_… {len(s.details) - detail_cap} more (see full artifact)_")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def render_ci_report_junit_xml(report: CIAuditReport) -> str:
    """Render the report as JUnit XML (one ``<testcase>`` per step).

    Failures and errors emit ``<failure>`` / ``<error>`` children carrying
    the step's summary as the message.  Skipped steps emit ``<skipped>``.
    """
    suite_n = report.n_steps_run
    failures = sum(1 for s in report.steps if s.status == StepStatus.fail)
    errors = sum(1 for s in report.steps if s.status == StepStatus.error)
    skipped = sum(1 for s in report.steps if s.status == StepStatus.skipped)
    duration_s = sum(s.duration_ms for s in report.steps) / 1000.0

    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<testsuite name="panelforge-figures.ci-audit" '
        f'tests="{suite_n}" '
        f'failures="{failures}" '
        f'errors="{errors}" '
        f'skipped="{skipped}" '
        f'time="{duration_s:.3f}" '
        f'timestamp="{_xml_escape(report.timestamp)}">'
    )

    for s in report.steps:
        classname = "panelforge_figures.ci_audit"
        case_time = s.duration_ms / 1000.0
        lines.append(
            f'  <testcase classname="{classname}" '
            f'name="{_xml_escape(s.step.value)}" '
            f'time="{case_time:.3f}">'
        )
        if s.status == StepStatus.fail:
            lines.append(
                f'    <failure message="{_xml_escape(s.summary)}">'
                f"{_xml_escape(chr(10).join(s.details))}"
                f"</failure>"
            )
        elif s.status == StepStatus.error:
            msg = s.error_message or s.summary
            lines.append(
                f'    <error message="{_xml_escape(msg)}">'
                f"{_xml_escape(s.summary)}"
                f"</error>"
            )
        elif s.status == StepStatus.skipped:
            lines.append(
                f'    <skipped message="{_xml_escape(s.summary)}"/>'
            )
        lines.append("  </testcase>")

    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"
