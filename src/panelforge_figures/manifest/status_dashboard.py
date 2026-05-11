"""Reproducibility / audit status dashboard (Elevation 20 — v3.14.0).

``figures status`` produces a single-screen overview of the entire
panelforge project state — cache hit rate, provenance coverage, audit
verdicts, telemetry status, registry membership, lock freshness.

Designed to fit comfortably in a 24-line / 80-col terminal but degrades
gracefully on smaller terminals. Optional ``--json`` / ``--html`` /
``--markdown`` outputs allow embedding in CI dashboards or hosted
artifacts.

The dashboard is *informational*: every section collector is sandboxed
so a transient I/O error in one section becomes a single ``unknown``
entry rather than a top-level failure. ``figures status`` must never
crash — that is its key contract.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "StatusLevel",
    "DashboardSection",
    "DashboardEntry",
    "StatusDashboard",
    "DashboardError",
    "collect_status",
    "render_dashboard_text",
    "render_dashboard_html",
    "render_dashboard_markdown",
]


# ─────────────────────────── enums / dataclasses ──────────────────────────


class StatusLevel(StrEnum):
    """One-character status for each dashboard entry."""

    ok = "ok"
    info = "info"
    warn = "warn"
    fail = "fail"
    skipped = "skipped"
    unknown = "unknown"


class DashboardSection(StrEnum):
    """Display-order grouping for dashboard entries."""

    project = "project"
    inventory = "inventory"
    cache = "cache"
    provenance = "provenance"
    audits = "audits"
    artifacts = "artifacts"
    safety = "safety"
    telemetry = "telemetry"


# Severity ranking used to compute the overall verdict — higher = worse.
_SEVERITY_RANK: dict[StatusLevel, int] = {
    StatusLevel.ok: 0,
    StatusLevel.info: 0,
    StatusLevel.skipped: 0,
    StatusLevel.unknown: 1,
    StatusLevel.warn: 2,
    StatusLevel.fail: 3,
}


@dataclass(frozen=True)
class DashboardEntry:
    """A single line of the dashboard."""

    section: DashboardSection
    label: str
    value: str
    level: StatusLevel
    detail: str = ""


@dataclass(frozen=True)
class StatusDashboard:
    """End-to-end dashboard snapshot.

    The dashboard is structured for both human (terminal) and machine
    (JSON / CI artifact) consumption; ``to_dict`` produces stable,
    JSON-safe output.
    """

    project_root: Path
    panelforge_version: str
    timestamp: str
    entries: tuple[DashboardEntry, ...]
    overall_level: StatusLevel
    summary_line: str

    def to_dict(self) -> dict[str, Any]:
        """Render the dashboard as a JSON-friendly dict."""
        return {
            "project_root": str(self.project_root),
            "panelforge_version": self.panelforge_version,
            "timestamp": self.timestamp,
            "overall_level": self.overall_level.value,
            "summary_line": self.summary_line,
            "entries": [
                {
                    "section": e.section.value,
                    "label": e.label,
                    "value": e.value,
                    "level": e.level.value,
                    "detail": e.detail,
                }
                for e in self.entries
            ],
        }


class DashboardError(RuntimeError):
    """Raised on dashboard collection failures (rare — most sections are tolerant)."""


# ─────────────────────────── small helpers ────────────────────────────────


_WORKSPACE_DIR = "panelforge_workspace"


def _utc_now_iso() -> str:
    """ISO-8601 UTC timestamp with the spec-mandated ``Z`` suffix."""
    return (
        datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _safe_age_days(timestamp: str | None) -> int | None:
    """Parse an ISO-Z timestamp and return whole days since it.

    Returns ``None`` on any parse failure — the dashboard never raises.
    """
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - dt
    return max(0, delta.days)


def _safe_path_age_days(path: Path) -> int | None:
    """Whole days since the file's mtime, or ``None`` if unreadable."""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    dt = datetime.fromtimestamp(mtime, tz=UTC)
    delta = datetime.now(UTC) - dt
    return max(0, delta.days)


def _load_project_yaml(project_root: Path) -> dict[str, Any]:
    """Read ``panelforge.project.yaml`` if present; return ``{}`` on any failure."""
    for name in ("panelforge.project.yaml", "panelforge.project.yml"):
        candidate = project_root / name
        if candidate.is_file():
            try:
                from panelforge_figures.manifest.project_scan import _load_yaml
                return _load_yaml(candidate)
            except Exception:  # noqa: BLE001 — dashboard tolerance
                return {}
    return {}


def _count_files(directory: Path, suffixes: tuple[str, ...] | None = None) -> int:
    """Count files (recursively) under ``directory``, optionally filtered by suffix.

    Returns 0 if the directory is absent or unreadable.
    """
    if not directory.is_dir():
        return 0
    try:
        if suffixes is None:
            return sum(1 for p in directory.rglob("*") if p.is_file())
        return sum(
            1
            for p in directory.rglob("*")
            if p.is_file() and p.suffix.lower() in suffixes
        )
    except OSError:
        return 0


def _dir_size_bytes(directory: Path) -> int:
    """Total size of all files in ``directory`` (recursive). 0 on error."""
    if not directory.is_dir():
        return 0
    total = 0
    try:
        for p in directory.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    continue
    except OSError:
        return 0
    return total


def _format_bytes(n: int) -> str:
    """Human-readable size: ``243 MB``, ``1.2 GB``."""
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n_div = n / 1024.0
        if n_div < 1024:
            return f"{n_div:.0f} {unit}" if n_div >= 10 else f"{n_div:.1f} {unit}"
        n = int(n_div)
    return f"{n} PB"


# ─────────────────────────── section collectors ───────────────────────────


def _collect_project_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Read ``panelforge.project.yaml`` and registry membership."""
    del manuscript_path, figures_dir, verbose  # unused — kept for uniform signature

    entries: list[DashboardEntry] = []
    cfg = _load_project_yaml(project_root)
    yaml_present = bool(cfg)

    project_id = str(cfg.get("project_id", "")) if yaml_present else ""
    modality = str(cfg.get("modality", "")) if yaml_present else ""
    data_class = str(cfg.get("data_class", "")) if yaml_present else ""

    if not yaml_present:
        entries.append(DashboardEntry(
            section=DashboardSection.project,
            label="panelforge.project.yaml",
            value="absent",
            level=StatusLevel.warn,
            detail="run `figures intake` to scaffold one",
        ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.project,
            label="project_id",
            value=project_id or "(unset)",
            level=StatusLevel.ok if project_id else StatusLevel.warn,
        ))
        entries.append(DashboardEntry(
            section=DashboardSection.project,
            label="modality",
            value=modality or "(unset)",
            level=StatusLevel.ok if modality else StatusLevel.info,
        ))
        entries.append(DashboardEntry(
            section=DashboardSection.project,
            label="data_class",
            value=data_class or "research (default)",
            level=StatusLevel.ok,
        ))

    # Cross-project registry membership.
    registered = False
    is_default = False
    try:
        from panelforge_figures.projects import load_registry
        registry = load_registry()
        resolved = project_root.resolve()
        for entry in registry.projects.values():
            try:
                if Path(entry.path).resolve() == resolved:
                    registered = True
                    is_default = registry.default_project == entry.id
                    break
            except OSError:
                continue
    except Exception:  # noqa: BLE001
        registered = False

    if registered:
        suffix = " (default)" if is_default else ""
        entries.append(DashboardEntry(
            section=DashboardSection.project,
            label="registry",
            value=f"registered{suffix}",
            level=StatusLevel.info,
        ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.project,
            label="registry",
            value="not registered",
            level=StatusLevel.info,
            detail="run `figures intake` or `figures projects register` to add",
        ))

    return entries


def _collect_inventory_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Count data files, models, notebooks; detect manuscript existence."""
    del figures_dir, verbose
    entries: list[DashboardEntry] = []

    data_dir = project_root / "data"
    n_data = _count_files(data_dir)
    size = _dir_size_bytes(data_dir)
    if n_data > 0:
        entries.append(DashboardEntry(
            section=DashboardSection.inventory,
            label="data files",
            value=f"{n_data} ({_format_bytes(size)})",
            level=StatusLevel.ok,
        ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.inventory,
            label="data files",
            value="0",
            level=StatusLevel.warn,
            detail="no data/ directory or empty",
        ))

    # Models & notebooks — counts only.
    models_dir = project_root / "models"
    n_models = _count_files(models_dir)
    if n_models > 0:
        entries.append(DashboardEntry(
            section=DashboardSection.inventory,
            label="models",
            value=str(n_models),
            level=StatusLevel.ok,
        ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.inventory,
            label="models",
            value="0",
            level=StatusLevel.info,
        ))

    notebooks_dir = project_root / "notebooks"
    n_nb = _count_files(notebooks_dir, suffixes=(".ipynb",))
    # Also check top-level
    if n_nb == 0:
        n_nb = _count_files(project_root, suffixes=(".ipynb",))
    entries.append(DashboardEntry(
        section=DashboardSection.inventory,
        label="notebooks",
        value=str(n_nb),
        level=StatusLevel.ok if n_nb > 0 else StatusLevel.info,
    ))

    # Manuscript detection.
    if manuscript_path is not None and manuscript_path.is_file():
        entries.append(DashboardEntry(
            section=DashboardSection.inventory,
            label="manuscript",
            value=str(manuscript_path.relative_to(project_root)
                      if manuscript_path.is_absolute()
                      and project_root in manuscript_path.parents
                      else manuscript_path),
            level=StatusLevel.ok,
        ))
    else:
        # Auto-detect canonical paths.
        for candidate in (
            project_root / "manuscript" / "main.tex",
            project_root / "manuscript.tex",
            project_root / "manuscript.md",
            project_root / "manuscript" / "manuscript.tex",
        ):
            if candidate.is_file():
                entries.append(DashboardEntry(
                    section=DashboardSection.inventory,
                    label="manuscript",
                    value=str(candidate.relative_to(project_root)),
                    level=StatusLevel.ok,
                ))
                break
        else:
            entries.append(DashboardEntry(
                section=DashboardSection.inventory,
                label="manuscript",
                value="absent",
                level=StatusLevel.info,
                detail="no manuscript.{tex,md} found",
            ))

    return entries


def _collect_cache_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Read render_cache.json; emit entry count, oldest age, hit-rate."""
    del manuscript_path, figures_dir, verbose
    entries: list[DashboardEntry] = []

    try:
        from panelforge_figures.manifest.render_cache import (
            cache_path_for_project,
            load_cache,
        )
    except Exception as exc:  # noqa: BLE001
        return [DashboardEntry(
            section=DashboardSection.cache,
            label="render cache",
            value="?",
            level=StatusLevel.unknown,
            detail=f"import failed: {exc}",
        )]

    path = cache_path_for_project(project_root)
    if not path.is_file():
        entries.append(DashboardEntry(
            section=DashboardSection.cache,
            label="render cache",
            value="absent",
            level=StatusLevel.info,
            detail="no panelforge_workspace/render_cache.json (first run?)",
        ))
        return entries

    cache = load_cache(project_root)
    n_total = len(cache.entries)
    if n_total == 0:
        entries.append(DashboardEntry(
            section=DashboardSection.cache,
            label="render cache",
            value="0 entries",
            level=StatusLevel.info,
        ))
        return entries

    # Hit rate: entries whose output_path still exists on disk.
    n_fresh = 0
    oldest_age: int | None = None
    for entry in cache.entries.values():
        try:
            out_path = project_root / entry.output_path
            if out_path.is_file():
                n_fresh += 1
        except OSError:
            pass
        age = _safe_age_days(entry.rendered_at)
        if age is not None:
            if oldest_age is None or age > oldest_age:
                oldest_age = age

    pct = round(100.0 * n_fresh / n_total) if n_total > 0 else 0
    if pct == 100:
        cache_level = StatusLevel.ok
    elif pct >= 75:
        cache_level = StatusLevel.ok
    elif pct >= 50:
        cache_level = StatusLevel.warn
    else:
        cache_level = StatusLevel.warn
    entries.append(DashboardEntry(
        section=DashboardSection.cache,
        label="render cache",
        value=f"{n_fresh}/{n_total} fresh ({pct}%)",
        level=cache_level,
    ))

    if oldest_age is not None:
        entries.append(DashboardEntry(
            section=DashboardSection.cache,
            label="oldest entry",
            value=f"{oldest_age} day{'s' if oldest_age != 1 else ''} old",
            level=StatusLevel.info,
        ))

    return entries


def _collect_provenance_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Walk *.provenance.json sidecars; emit coverage statistics."""
    del manuscript_path, verbose
    entries: list[DashboardEntry] = []

    figs_dir = figures_dir or (project_root / _WORKSPACE_DIR / "figures")
    if not figs_dir.is_dir():
        entries.append(DashboardEntry(
            section=DashboardSection.provenance,
            label="figures w/ sidecar",
            value="0/0",
            level=StatusLevel.info,
            detail=f"{figs_dir} does not exist",
        ))
        return entries

    # Count actual rendered figures + sidecars.
    fig_exts = {".pdf", ".png", ".svg"}
    fig_files = [
        p for p in figs_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in fig_exts
    ]
    sidecar_files = list(figs_dir.rglob("*.provenance.json"))

    n_fig = len(fig_files)
    n_sidecar = len(sidecar_files)

    if n_fig == 0:
        entries.append(DashboardEntry(
            section=DashboardSection.provenance,
            label="figures w/ sidecar",
            value="0/0",
            level=StatusLevel.info,
            detail="no figures rendered yet",
        ))
        return entries

    pct = round(100.0 * n_sidecar / n_fig) if n_fig > 0 else 0
    if pct >= 100:
        level = StatusLevel.ok
    elif pct >= 75:
        level = StatusLevel.warn
    else:
        level = StatusLevel.warn
    entries.append(DashboardEntry(
        section=DashboardSection.provenance,
        label="figures w/ sidecar",
        value=f"{n_sidecar}/{n_fig} ({pct}%)",
        level=level,
    ))

    # Sidecar-with-audit-block coverage.
    n_with_audit = 0
    oldest_render: int | None = None
    try:
        from panelforge_figures.manifest.provenance import load_provenance_json
        for sidecar in sidecar_files:
            try:
                rec = load_provenance_json(sidecar)
            except Exception:  # noqa: BLE001
                continue
            if rec.audit:
                n_with_audit += 1
            age = _safe_age_days(rec.rendered_at)
            if age is not None and (oldest_render is None or age > oldest_render):
                oldest_render = age
    except Exception:  # noqa: BLE001
        pass

    if n_sidecar > 0:
        pct_audit = round(100.0 * n_with_audit / n_sidecar)
        entries.append(DashboardEntry(
            section=DashboardSection.provenance,
            label="figures w/ audit",
            value=f"{n_with_audit}/{n_sidecar} ({pct_audit}%)",
            level=StatusLevel.ok if pct_audit >= 75 else StatusLevel.info,
        ))

    if oldest_render is not None:
        entries.append(DashboardEntry(
            section=DashboardSection.provenance,
            label="oldest figure",
            value=f"{oldest_render} day{'s' if oldest_render != 1 else ''} old",
            level=StatusLevel.info,
        ))

    return entries


def _collect_audits_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Run best-effort audits and emit one-line verdicts."""
    del verbose
    entries: list[DashboardEntry] = []
    figs_dir = figures_dir or (project_root / _WORKSPACE_DIR / "figures")
    cfg = _load_project_yaml(project_root)

    # Detect manuscript if not provided.
    if manuscript_path is None or not manuscript_path.is_file():
        for candidate in (
            project_root / "manuscript" / "main.tex",
            project_root / "manuscript.tex",
            project_root / "manuscript.md",
        ):
            if candidate.is_file():
                manuscript_path = candidate
                break

    # 1. verify-claims (E2)
    if manuscript_path and manuscript_path.is_file() and figs_dir.is_dir():
        try:
            from panelforge_figures.manifest.claim_check import verify_manuscript
            report = verify_manuscript(manuscript_path, figs_dir)
            if report.n_claims == 0:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="verify-claims",
                    value="0 claims",
                    level=StatusLevel.info,
                ))
            elif report.n_unsupported > 0:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="verify-claims",
                    value=f"{report.n_unsupported} unsupported / "
                          f"{report.n_supported} supported",
                    level=StatusLevel.fail,
                ))
            elif report.n_unverifiable > 0:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="verify-claims",
                    value=f"{report.n_supported} supported / "
                          f"{report.n_unverifiable} unverifiable",
                    level=StatusLevel.warn,
                ))
            else:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="verify-claims",
                    value=f"{report.n_supported} supported",
                    level=StatusLevel.ok,
                ))
        except Exception as exc:  # noqa: BLE001
            entries.append(DashboardEntry(
                section=DashboardSection.audits,
                label="verify-claims",
                value="?",
                level=StatusLevel.unknown,
                detail=f"{type(exc).__name__}: {exc}",
            ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.audits,
            label="verify-claims",
            value="skipped",
            level=StatusLevel.skipped,
            detail="no manuscript or figures dir",
        ))

    # 2. lint-xrefs (E13)
    if manuscript_path and manuscript_path.is_file():
        try:
            from panelforge_figures.manifest.xref_linter import lint_xrefs
            fdir = figs_dir if figs_dir.is_dir() else None
            report = lint_xrefs(manuscript_path, figures_dir=fdir)
            if report.verdict == "clean":
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="xref-linter",
                    value="clean",
                    level=StatusLevel.ok,
                ))
            elif report.verdict == "errors":
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="xref-linter",
                    value=f"{report.n_errors} error"
                          f"{'s' if report.n_errors != 1 else ''}",
                    level=StatusLevel.fail,
                ))
            else:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="xref-linter",
                    value=f"{report.n_warnings} warning"
                          f"{'s' if report.n_warnings != 1 else ''}",
                    level=StatusLevel.warn,
                ))
        except Exception as exc:  # noqa: BLE001
            entries.append(DashboardEntry(
                section=DashboardSection.audits,
                label="xref-linter",
                value="?",
                level=StatusLevel.unknown,
                detail=f"{type(exc).__name__}: {exc}",
            ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.audits,
            label="xref-linter",
            value="skipped",
            level=StatusLevel.skipped,
            detail="no manuscript",
        ))

    # 3. audit-bias (E17)
    if figs_dir.is_dir():
        try:
            from panelforge_figures.manifest.bias_auditor import (
                audit_bias_across_directory,
            )
            report = audit_bias_across_directory(figs_dir)
            if report.n_figures_inspected == 0:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="audit-bias",
                    value="no figures",
                    level=StatusLevel.info,
                ))
            elif report.overall_verdict == "honest":
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="audit-bias",
                    value="honest",
                    level=StatusLevel.ok,
                ))
            elif report.overall_verdict == "concerning":
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="audit-bias",
                    value=f"{report.n_errors} error"
                          f"{'s' if report.n_errors != 1 else ''}",
                    level=StatusLevel.fail,
                ))
            else:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label="audit-bias",
                    value=f"{report.n_warnings} warning"
                          f"{'s' if report.n_warnings != 1 else ''}",
                    level=StatusLevel.warn,
                ))
        except Exception as exc:  # noqa: BLE001
            entries.append(DashboardEntry(
                section=DashboardSection.audits,
                label="audit-bias",
                value="?",
                level=StatusLevel.unknown,
                detail=f"{type(exc).__name__}: {exc}",
            ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.audits,
            label="audit-bias",
            value="skipped",
            level=StatusLevel.skipped,
            detail="no figures directory",
        ))

    # 4. audit-venue (E16) — only when both manuscript and a venue are set.
    venue = cfg.get("venue") if cfg else None
    if manuscript_path and manuscript_path.is_file() and venue:
        try:
            from panelforge_figures.manifest.venue_auditor import audit_venue
            fdir = figs_dir if figs_dir.is_dir() else None
            report = audit_venue(
                manuscript_path,
                venue=str(venue),
                figures_dir=fdir,
            )
            label = f"audit-venue ({venue})"
            if report.overall_verdict == "ready_to_submit":
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label=label,
                    value="ready_to_submit",
                    level=StatusLevel.ok,
                ))
            elif report.overall_verdict == "blocked":
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label=label,
                    value=f"blocked ({report.n_errors})",
                    level=StatusLevel.fail,
                ))
            else:
                entries.append(DashboardEntry(
                    section=DashboardSection.audits,
                    label=label,
                    value=f"needs_revision ({report.n_warnings})",
                    level=StatusLevel.warn,
                ))
        except Exception as exc:  # noqa: BLE001
            entries.append(DashboardEntry(
                section=DashboardSection.audits,
                label="audit-venue",
                value="?",
                level=StatusLevel.unknown,
                detail=f"{type(exc).__name__}: {exc}",
            ))
    else:
        reason = "no venue in project.yaml" if not venue else "no manuscript"
        entries.append(DashboardEntry(
            section=DashboardSection.audits,
            label="audit-venue",
            value="skipped",
            level=StatusLevel.skipped,
            detail=reason,
        ))

    return entries


def _collect_artifacts_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Count workspace artifacts: figures, captions, plan, lock."""
    del manuscript_path, verbose
    entries: list[DashboardEntry] = []

    figs_dir = figures_dir or (project_root / _WORKSPACE_DIR / "figures")
    captions_dir = project_root / _WORKSPACE_DIR / "captions"
    plan_path = project_root / "figures_plan.yaml"
    lock_path = project_root / "panelforge.lock.json"

    n_pdfs = _count_files(figs_dir, suffixes=(".pdf",))
    n_captions = _count_files(captions_dir, suffixes=(".md",))

    entries.append(DashboardEntry(
        section=DashboardSection.artifacts,
        label="figures",
        value=f"{n_pdfs} PDF{'s' if n_pdfs != 1 else ''}",
        level=StatusLevel.ok if n_pdfs > 0 else StatusLevel.info,
    ))
    entries.append(DashboardEntry(
        section=DashboardSection.artifacts,
        label="captions",
        value=f"{n_captions} drafted",
        level=StatusLevel.ok if n_captions > 0 else StatusLevel.info,
    ))

    if plan_path.is_file():
        age = _safe_path_age_days(plan_path)
        suffix = f" ({age} day{'s' if age != 1 else ''} old)" if age is not None else ""
        entries.append(DashboardEntry(
            section=DashboardSection.artifacts,
            label="figures_plan.yaml",
            value=f"present{suffix}",
            level=StatusLevel.ok,
        ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.artifacts,
            label="figures_plan.yaml",
            value="absent",
            level=StatusLevel.info,
            detail="run `figures scout` to produce one",
        ))

    if lock_path.is_file():
        age = _safe_path_age_days(lock_path)
        suffix = f" ({age} day{'s' if age != 1 else ''} old)" if age is not None else ""
        entries.append(DashboardEntry(
            section=DashboardSection.artifacts,
            label="lock file",
            value=f"present{suffix}",
            level=StatusLevel.ok,
        ))
    else:
        entries.append(DashboardEntry(
            section=DashboardSection.artifacts,
            label="lock file",
            value="absent",
            level=StatusLevel.info,
            detail="run `figures lock` to produce one",
        ))

    return entries


def _collect_safety_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Emit runtime data_class + policy summary entries."""
    del manuscript_path, figures_dir, verbose
    entries: list[DashboardEntry] = []

    try:
        from panelforge_figures.safety import (
            get_data_class,
            get_policy,
            is_llm_allowed,
            is_plugin_network_allowed,
            is_telemetry_allowed,
            is_vision_allowed,
        )
    except Exception as exc:  # noqa: BLE001
        return [DashboardEntry(
            section=DashboardSection.safety,
            label="safety policy",
            value="?",
            level=StatusLevel.unknown,
            detail=f"{type(exc).__name__}: {exc}",
        )]

    dc = get_data_class()
    policy = get_policy()
    entries.append(DashboardEntry(
        section=DashboardSection.safety,
        label="data_class",
        value=str(dc.value),
        level=StatusLevel.ok,
    ))

    llm_allowed = is_llm_allowed()
    if policy.llm_pass3 == "disabled":
        llm_value = "disabled"
        llm_level = StatusLevel.ok
    elif llm_allowed:
        llm_value = "allowed"
        llm_level = StatusLevel.info
    else:
        llm_value = "opt-in (no API key)"
        llm_level = StatusLevel.info
    entries.append(DashboardEntry(
        section=DashboardSection.safety,
        label="LLM channel",
        value=llm_value,
        level=llm_level,
    ))

    vision_allowed = is_vision_allowed()
    if policy.vision == "disabled":
        vision_value = "disabled"
        vision_level = StatusLevel.ok
    elif vision_allowed:
        vision_value = "allowed"
        vision_level = StatusLevel.info
    else:
        vision_value = "opt-in (no API key)"
        vision_level = StatusLevel.info
    entries.append(DashboardEntry(
        section=DashboardSection.safety,
        label="vision channel",
        value=vision_value,
        level=vision_level,
    ))

    if is_telemetry_allowed():
        tel_value = "on"
    else:
        tel_value = "off"
    entries.append(DashboardEntry(
        section=DashboardSection.safety,
        label="telemetry",
        value=tel_value,
        level=StatusLevel.ok,
    ))

    entries.append(DashboardEntry(
        section=DashboardSection.safety,
        label="plugin network",
        value="allowed" if is_plugin_network_allowed() else "disallowed",
        level=StatusLevel.ok,
    ))

    return entries


def _collect_telemetry_section(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> list[DashboardEntry]:
    """Read panelforge_workspace/usage.jsonl row count."""
    del manuscript_path, figures_dir, verbose
    entries: list[DashboardEntry] = []

    try:
        from panelforge_figures.manifest.telemetry import (
            is_telemetry_enabled,
            telemetry_log_path,
        )
    except Exception as exc:  # noqa: BLE001
        return [DashboardEntry(
            section=DashboardSection.telemetry,
            label="usage.jsonl",
            value="?",
            level=StatusLevel.unknown,
            detail=f"{type(exc).__name__}: {exc}",
        )]

    log_path = telemetry_log_path(project_root)
    project_opt_in = is_telemetry_enabled(project_root)

    if not log_path.is_file():
        entries.append(DashboardEntry(
            section=DashboardSection.telemetry,
            label="usage.jsonl",
            value="not present",
            level=StatusLevel.skipped,
            detail="telemetry off" if not project_opt_in else "no rows yet",
        ))
        return entries

    # Count rows safely.
    n_rows = 0
    n_picked = 0
    oldest_age: int | None = None
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n_rows += 1
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if row.get("user_picked"):
                    n_picked += 1
                ts = row.get("timestamp") or row.get("invoked_at")
                age = _safe_age_days(ts)
                if age is not None and (oldest_age is None or age > oldest_age):
                    oldest_age = age
    except OSError as exc:
        return [DashboardEntry(
            section=DashboardSection.telemetry,
            label="usage.jsonl",
            value="?",
            level=StatusLevel.unknown,
            detail=f"read error: {exc}",
        )]

    entries.append(DashboardEntry(
        section=DashboardSection.telemetry,
        label="usage.jsonl",
        value=f"{n_rows} row{'s' if n_rows != 1 else ''}",
        level=StatusLevel.ok if n_rows > 0 else StatusLevel.info,
    ))
    if n_rows > 0:
        entries.append(DashboardEntry(
            section=DashboardSection.telemetry,
            label="user picks",
            value=f"{n_picked} marked",
            level=StatusLevel.info,
        ))
    if oldest_age is not None:
        entries.append(DashboardEntry(
            section=DashboardSection.telemetry,
            label="oldest row",
            value=f"{oldest_age} day{'s' if oldest_age != 1 else ''} old",
            level=StatusLevel.info,
        ))

    return entries


# ─────────────────────────── orchestration ────────────────────────────────


_CollectorFn = Callable[..., list[DashboardEntry]]


_SECTION_NAMES: dict[_CollectorFn, DashboardSection] = {}


def _compute_overall_level(entries: list[DashboardEntry]) -> StatusLevel:
    """Worst level across all entries by ``_SEVERITY_RANK``."""
    if not entries:
        return StatusLevel.ok
    worst = StatusLevel.ok
    worst_rank = -1
    for e in entries:
        rank = _SEVERITY_RANK.get(e.level, 0)
        if rank > worst_rank:
            worst = e.level
            worst_rank = rank
    return worst


def _compute_summary_line(
    entries: list[DashboardEntry],
    overall: StatusLevel,
) -> str:
    """Pithy one-liner for the top of the dashboard.

    Tries to mention the most-actionable counters (failed claims, warnings,
    etc.) before falling back to a generic verdict.
    """
    if overall == StatusLevel.fail:
        n_fail = sum(1 for e in entries if e.level == StatusLevel.fail)
        return f"FAIL — {n_fail} blocking issue{'s' if n_fail != 1 else ''}"
    if overall == StatusLevel.warn:
        n_warn = sum(1 for e in entries if e.level == StatusLevel.warn)
        return f"warnings — {n_warn} item{'s' if n_warn != 1 else ''} needs attention"
    if overall == StatusLevel.unknown:
        return "incomplete — one or more sections could not be inspected"
    return "all checks passing"


def collect_status(
    project_root: Path,
    *,
    manuscript_path: Path | None = None,
    figures_dir: Path | None = None,
    verbose: bool = False,
) -> StatusDashboard:
    """Walk the project + cache + provenance + workspace state.

    Each section is sandboxed: a collector raising an exception becomes
    a single ``unknown`` :class:`DashboardEntry` rather than a top-level
    failure. The dashboard is informational; it must not fail.
    """
    from panelforge_figures import __version__

    project_root = Path(project_root).resolve()
    entries: list[DashboardEntry] = []

    collectors: tuple[tuple[DashboardSection, _CollectorFn], ...] = (
        (DashboardSection.project, _collect_project_section),
        (DashboardSection.inventory, _collect_inventory_section),
        (DashboardSection.cache, _collect_cache_section),
        (DashboardSection.provenance, _collect_provenance_section),
        (DashboardSection.audits, _collect_audits_section),
        (DashboardSection.artifacts, _collect_artifacts_section),
        (DashboardSection.safety, _collect_safety_section),
        (DashboardSection.telemetry, _collect_telemetry_section),
    )

    for section, collector in collectors:
        try:
            section_entries = collector(
                project_root,
                manuscript_path=manuscript_path,
                figures_dir=figures_dir,
                verbose=verbose,
            )
            entries.extend(section_entries)
        except Exception as exc:  # noqa: BLE001 — dashboard must never fail
            entries.append(DashboardEntry(
                section=section,
                label=f"{section.value} (error)",
                value="?",
                level=StatusLevel.unknown,
                detail=f"{type(exc).__name__}: {exc}",
            ))

    overall = _compute_overall_level(entries)
    summary = _compute_summary_line(entries, overall)

    return StatusDashboard(
        project_root=project_root,
        panelforge_version=__version__,
        timestamp=_utc_now_iso(),
        entries=tuple(entries),
        overall_level=overall,
        summary_line=summary,
    )


# ─────────────────────────── renderers ────────────────────────────────────


# ANSI color codes (no external dep — we don't want click here for testability).
_ANSI = {
    "reset": "\x1b[0m",
    "bold": "\x1b[1m",
    "dim": "\x1b[2m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "gray": "\x1b[90m",
}

_LEVEL_GLYPH: dict[StatusLevel, str] = {
    StatusLevel.ok: "OK",
    StatusLevel.info: "ii",
    StatusLevel.warn: "!!",
    StatusLevel.fail: "XX",
    StatusLevel.skipped: "--",
    StatusLevel.unknown: "??",
}

_LEVEL_COLOR: dict[StatusLevel, str] = {
    StatusLevel.ok: "green",
    StatusLevel.info: "blue",
    StatusLevel.warn: "yellow",
    StatusLevel.fail: "red",
    StatusLevel.skipped: "gray",
    StatusLevel.unknown: "gray",
}


def _colorize(text: str, color: str, *, enabled: bool) -> str:
    """ANSI-wrap text if colour is enabled, otherwise return unchanged."""
    if not enabled or color not in _ANSI:
        return text
    return f"{_ANSI[color]}{text}{_ANSI['reset']}"


def _section_title(section: DashboardSection) -> str:
    return section.value


def render_dashboard_text(
    dashboard: StatusDashboard,
    *,
    color: bool = True,
    verbose: bool = False,
) -> str:
    """Render the dashboard for a typical 80x24 terminal.

    Uses ASCII box drawing so the output survives ``tee | cat`` without
    requiring a Unicode-capable terminal.
    """
    use_color = color and os.environ.get("NO_COLOR") is None

    lines: list[str] = []
    default_width = 78
    # Auto-grow the box to fit the project_root + header lines so the
    # path is never truncated; the user-facing contract is "the project
    # root is always present in full" because the dashboard is meant to
    # be unambiguous about *which* project it described.
    header_text = (
        f"panelforge status . v{dashboard.panelforge_version} . "
        f"{dashboard.timestamp}"
    )
    project_text = str(dashboard.project_root)
    inner = max(default_width - 2, len(header_text) + 1, len(project_text) + 1)
    width = inner + 2

    header_top = "+" + "-" * (width - 2) + "+"
    header_l1 = "| " + header_text
    header_l1 = (header_l1 + " " * width)[: width - 1] + "|"
    project_line = "| " + project_text
    project_line = (project_line + " " * width)[: width - 1] + "|"

    lines.append(header_top)
    lines.append(header_l1)
    lines.append(project_line)
    lines.append(header_top)
    lines.append("")

    # Overall summary line.
    summary_color = _LEVEL_COLOR.get(dashboard.overall_level, "gray")
    glyph = _LEVEL_GLYPH.get(dashboard.overall_level, "??")
    summary_text = f"overall: {glyph} {dashboard.summary_line}"
    lines.append(_colorize(summary_text, summary_color, enabled=use_color))
    lines.append("")

    # Group entries by section in display order.
    seen_sections: list[DashboardSection] = []
    section_entries: dict[DashboardSection, list[DashboardEntry]] = {}
    for entry in dashboard.entries:
        if entry.section not in section_entries:
            seen_sections.append(entry.section)
            section_entries[entry.section] = []
        section_entries[entry.section].append(entry)

    # Layout: label column is 22 chars, value follows on the same line.
    label_width = 22
    for section in seen_sections:
        lines.append(_colorize(_section_title(section), "bold", enabled=use_color))
        for entry in section_entries[section]:
            glyph = _LEVEL_GLYPH.get(entry.level, "??")
            colored_glyph = _colorize(
                glyph, _LEVEL_COLOR.get(entry.level, "gray"), enabled=use_color
            )
            label = entry.label
            if len(label) > label_width:
                label = label[: label_width - 1] + "."
            padding = " " * max(1, label_width - len(label))
            lines.append(f"  {colored_glyph} {label}{padding}{entry.value}")
            if verbose and entry.detail:
                lines.append(
                    _colorize(
                        f"      -> {entry.detail}",
                        "gray",
                        enabled=use_color,
                    )
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_dashboard_html(dashboard: StatusDashboard) -> str:
    """Render a styled-HTML dashboard for docs-site embedding.

    Self-contained: a single ``<style>`` block, no external CSS, valid
    HTML5 fragment that an HTML parser can round-trip.
    """
    # Map levels to CSS classes / background colours.
    level_class = {
        StatusLevel.ok: "ok",
        StatusLevel.info: "info",
        StatusLevel.warn: "warn",
        StatusLevel.fail: "fail",
        StatusLevel.skipped: "skipped",
        StatusLevel.unknown: "unknown",
    }

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang=\"en\">")
    parts.append("<head>")
    parts.append("<meta charset=\"utf-8\">")
    parts.append(
        f"<title>panelforge status — {_escape_html(str(dashboard.project_root))}</title>"
    )
    parts.append("<style>")
    parts.append(_DASHBOARD_CSS)
    parts.append("</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append("<div class=\"dashboard\">")
    parts.append("<header>")
    parts.append(
        f"<h1>panelforge status v{_escape_html(dashboard.panelforge_version)}</h1>"
    )
    parts.append(
        f"<div class=\"meta\">{_escape_html(str(dashboard.project_root))} "
        f"<span class=\"ts\">{_escape_html(dashboard.timestamp)}</span></div>"
    )
    overall_cls = level_class.get(dashboard.overall_level, "unknown")
    parts.append(
        f"<div class=\"overall {overall_cls}\">"
        f"{_escape_html(dashboard.summary_line)}</div>"
    )
    parts.append("</header>")

    # Group entries by section.
    section_entries: dict[DashboardSection, list[DashboardEntry]] = {}
    seen_sections: list[DashboardSection] = []
    for entry in dashboard.entries:
        if entry.section not in section_entries:
            seen_sections.append(entry.section)
            section_entries[entry.section] = []
        section_entries[entry.section].append(entry)

    for section in seen_sections:
        parts.append(f"<section class=\"section section-{section.value}\">")
        parts.append(f"<h2>{_escape_html(section.value)}</h2>")
        parts.append("<table>")
        for entry in section_entries[section]:
            cls = level_class.get(entry.level, "unknown")
            parts.append("<tr>")
            parts.append(f"<td class=\"glyph {cls}\">{_escape_html(entry.level.value)}</td>")
            parts.append(f"<td class=\"label\">{_escape_html(entry.label)}</td>")
            parts.append(f"<td class=\"value\">{_escape_html(entry.value)}</td>")
            if entry.detail:
                parts.append(
                    f"<td class=\"detail\">{_escape_html(entry.detail)}</td>"
                )
            else:
                parts.append("<td class=\"detail\"></td>")
            parts.append("</tr>")
        parts.append("</table>")
        parts.append("</section>")

    parts.append("</div>")
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)


_DASHBOARD_CSS = """
body { font: 14px/1.45 -apple-system, system-ui, sans-serif; background: #fafafa;
       margin: 0; padding: 24px; color: #222; }
.dashboard { max-width: 900px; margin: 0 auto; }
header h1 { margin: 0 0 4px; font-size: 18px; }
.meta { color: #666; font-size: 12px; }
.meta .ts { margin-left: 8px; color: #999; }
.overall { margin-top: 16px; padding: 8px 12px; border-radius: 4px; font-weight: 600; }
.overall.ok { background: #e6f4ea; color: #137333; }
.overall.warn { background: #fef7e0; color: #b06000; }
.overall.fail { background: #fce8e6; color: #b00020; }
.overall.info, .overall.skipped, .overall.unknown { background: #eee; color: #555; }
.section { margin-top: 24px; background: #fff; border-radius: 6px; padding: 12px 16px;
           box-shadow: 0 1px 2px rgba(0,0,0,.06); }
.section h2 { margin: 0 0 8px; font-size: 14px; text-transform: uppercase;
              letter-spacing: 1px; color: #555; }
table { width: 100%; border-collapse: collapse; }
td { padding: 4px 6px; vertical-align: top; }
td.glyph { width: 32px; text-align: center; font-family: monospace; border-radius: 3px;
           font-weight: 700; }
td.glyph.ok { background: #e6f4ea; color: #137333; }
td.glyph.info { background: #e8f0fe; color: #1a73e8; }
td.glyph.warn { background: #fef7e0; color: #b06000; }
td.glyph.fail { background: #fce8e6; color: #b00020; }
td.glyph.skipped, td.glyph.unknown { background: #eee; color: #666; }
td.label { width: 200px; font-weight: 600; }
td.value { color: #333; }
td.detail { color: #888; font-size: 12px; }
"""


def _escape_html(text: str) -> str:
    """Minimal HTML escape — enough for status values."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\"", "&quot;")
    )


_MARKDOWN_LEVEL_MARK: dict[StatusLevel, str] = {
    StatusLevel.ok: "[x]",
    StatusLevel.info: "[i]",
    StatusLevel.warn: "[!]",
    StatusLevel.fail: "[ ]",
    StatusLevel.skipped: "[-]",
    StatusLevel.unknown: "[?]",
}


def render_dashboard_markdown(dashboard: StatusDashboard) -> str:
    """Render as GitHub-flavoured Markdown using ``[x]`` / ``[ ]`` task markers.

    Suitable for posting as a PR comment or pasting into an issue body.
    """
    lines: list[str] = []
    lines.append(f"# panelforge status — v{dashboard.panelforge_version}")
    lines.append("")
    lines.append(f"**project**: `{dashboard.project_root}`  ")
    lines.append(f"**timestamp**: `{dashboard.timestamp}`  ")
    lines.append(f"**overall**: {dashboard.summary_line}")
    lines.append("")

    section_entries: dict[DashboardSection, list[DashboardEntry]] = {}
    seen_sections: list[DashboardSection] = []
    for entry in dashboard.entries:
        if entry.section not in section_entries:
            seen_sections.append(entry.section)
            section_entries[entry.section] = []
        section_entries[entry.section].append(entry)

    for section in seen_sections:
        lines.append(f"## {section.value}")
        lines.append("")
        for entry in section_entries[section]:
            mark = _MARKDOWN_LEVEL_MARK.get(entry.level, "[?]")
            line = f"- {mark} **{entry.label}** — {entry.value}"
            if entry.detail:
                line += f"  \n  _{entry.detail}_"
            lines.append(line)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
