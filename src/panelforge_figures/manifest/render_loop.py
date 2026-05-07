"""Per-recipe render iterator with non-fatal error capture.

Wave 3 — see ``CLAUDE_CODE_AUTONOMOUS.md`` §6.

The render loop iterates over a confirmed shortlist of bound recipes and,
for each one, builds a Pydantic contract from the user's data, calls the
recipe's ``render`` function on a fresh ``plt.subplots()`` axes, and saves
both ``<recipe_name>.pdf`` (vector) and ``<recipe_name>.png`` (300 DPI
raster).  Failures fall into two buckets:

* **Per-recipe failures are NEVER fatal.**  ``ContractValidationError``
  (Pydantic ``ValidationError``) and any generic ``Exception`` raised by
  the renderer are captured into a :class:`RenderOutcome`; the loop
  continues with the next recipe.
* **Environmental failures ARE fatal.**  ``ImportError`` /
  ``ModuleNotFoundError`` and ``OSError`` (write-permission, disk-full,
  etc.) halt the loop and raise :class:`EnvironmentalFailure`.
  ``KeyboardInterrupt`` propagates unchanged.

After the loop completes, :func:`write_render_report` emits a Markdown
``RENDER_REPORT.md`` with per-recipe status tables plus remediation
hints.  Both APIs are imported by ``cli.figures generate`` (Wave 3).

The module avoids tight coupling to ``data_bridge`` by typing its inputs
structurally — ``RenderBinding`` need only expose ``full_name``,
``fully_bound``, ``column_mapping``, ``data_file_per_field`` (or the
legacy single-source ``data_file_id``), and (when unbound)
``unbound_reason``; ``RenderDataFile`` need only expose ``file_id`` and
``path``.  This means the test suite can drive the loop with simple
dataclasses, and the eventual ``data_bridge`` module can re-export the
same shape transparently.
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .. import __version__
from ..core.contract import get_recipe
from ..core.statistical_contract import DEFAULT_CONTRACT, StatisticalContract
from .provenance import build_provenance, write_provenance_json

# ─────────────────────────── public exceptions ──────────────────────────


class EnvironmentalFailure(RuntimeError):
    """Raised when the render loop hits a non-recoverable environment problem.

    Triggered by ``ImportError`` / ``ModuleNotFoundError`` (a recipe
    module can't be imported) or ``OSError`` (write permission denied,
    disk full, etc.).  The loop halts immediately and any remaining
    recipes in the shortlist are NOT attempted.
    """


# ─────────────────────────── data classes ───────────────────────────────


@dataclass(frozen=True)
class RenderBinding:
    """Structural shape consumed by the render loop.

    Mirrors the ``data_bridge.RenderBinding`` produced upstream.  Kept
    here so this module is independently testable; the real
    ``data_bridge`` may import from here or define a compatible shape.

    Multi-source support: ``data_file_per_field`` maps each contract
    field to the path of the data file that supplies it.  This lets a
    single recipe pull columns from multiple files (e.g. ``cell_id``
    from ``morphometry.csv`` and ``velocity`` from ``tracks.csv``).

    ``data_file_id`` is retained for backward compatibility; if
    ``data_file_per_field`` is empty, the loop falls back to loading
    every column from the single file referenced by ``data_file_id``.
    """

    full_name: str
    fully_bound: bool
    column_mapping: dict[str, str] = field(default_factory=dict)
    data_file_per_field: dict[str, Path] = field(default_factory=dict)
    data_file_id: str | None = None
    unbound_reason: str | None = None


@dataclass(frozen=True)
class RenderDataFile:
    """Structural shape for a data file referenced by a binding."""

    file_id: str
    path: Path


@dataclass(frozen=True)
class RenderOutcome:
    """Per-recipe render result captured by the loop.

    ``status`` is one of:

    * ``"success"`` — recipe rendered to PDF + PNG.
    * ``"skipped_unbound"`` — binding was incomplete; render was not attempted.
    * ``"error_contract"`` — Pydantic ``ValidationError`` while building
      the recipe's input contract from user data.
    * ``"error_render"`` — generic exception raised by the renderer or
      inside ``_load_data_for_binding``.
    * ``"error_audit_refuse"`` — Sprint 1A (v1.7.0): the per-recipe
      :class:`StatisticalContract` audit returned ``overall == "refuse"``;
      the renderer was NOT invoked.  ``error_message`` carries the
      formatted findings; ``audit_findings`` carries the structured form.

    ``audit_findings`` is a tuple of structural :class:`AuditFinding`
    objects (rule_id, severity, message). It is populated for every
    audited recipe — both refused (status ``error_audit_refuse``) and
    warned (status ``success`` with warnings riding along) — so the
    report writer can surface them under "Statistical warnings".
    """

    full_name: str
    status: str
    pdf_path: Path | None
    png_path: Path | None
    error_class: str | None
    error_message: str | None
    traceback_excerpt: str | None  # last 5 lines if applicable
    elapsed_seconds: float
    audit_findings: tuple[Any, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RenderLog:
    """Aggregate result of a render-loop pass."""

    project_root: Path
    n_attempted: int
    n_success: int
    n_skipped: int
    n_failed: int
    outcomes: tuple[RenderOutcome, ...]
    started_at: str  # ISO-8601 UTC
    finished_at: str


# ─────────────────────────── helpers ────────────────────────────────────


def _utc_iso() -> str:
    """Return the current UTC time as a stable ISO-8601 string (seconds)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _excerpt_traceback(exc: BaseException, n_lines: int = 5) -> str:
    """Return the last ``n_lines`` of the formatted traceback for ``exc``."""
    formatted = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    lines = [ln for ln in formatted.splitlines() if ln.strip()]
    return "\n".join(lines[-n_lines:]) if lines else ""


def _git_commit_short(repo_root: Path | None = None) -> str:
    """Return the short git commit hash for the panelforge repo, or ``unknown``.

    Reads ``.git/HEAD`` and the referenced ref directly — no subprocess.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[3]
    head = repo_root / ".git" / "HEAD"
    try:
        head_text = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    if head_text.startswith("ref:"):
        ref = head_text.split(" ", 1)[1].strip()
        ref_path = repo_root / ".git" / ref
        try:
            return ref_path.read_text(encoding="utf-8").strip()[:8]
        except OSError:
            packed = repo_root / ".git" / "packed-refs"
            try:
                for raw in packed.read_text(encoding="utf-8").splitlines():
                    if raw.endswith(" " + ref):
                        return raw.split(" ", 1)[0][:8]
            except OSError:
                return "unknown"
            return "unknown"
    return head_text[:8] if head_text else "unknown"


def _load_columns_from_path(
    path: Path,
    fields_to_columns: dict[str, str],
) -> dict[str, Any]:
    """Read selected columns from a single data file.

    Supports CSV, Parquet, and NPZ.  Returns a dict keyed by contract
    field name; values are Python lists (CSV/parquet) or numpy arrays
    (npz).  Columns absent from the file are silently skipped — the
    contract validator catches the resulting incomplete kwargs.
    """
    suffix = path.suffix.lower()

    if suffix == ".csv":
        import pandas as pd

        df = pd.read_csv(path)
        return {
            field_name: df[col].tolist()
            for field_name, col in fields_to_columns.items()
            if col in df.columns
        }

    if suffix in (".parquet", ".pq"):
        import pandas as pd

        df = pd.read_parquet(path)
        return {
            field_name: df[col].tolist()
            for field_name, col in fields_to_columns.items()
            if col in df.columns
        }

    if suffix == ".npz":
        import numpy as np

        with np.load(path) as bundle:
            return {
                field_name: bundle[col]
                for field_name, col in fields_to_columns.items()
                if col in bundle.files
            }

    raise ValueError(f"unsupported data file format: {path.suffix!r}")


def _load_data_for_binding(
    binding: RenderBinding,
    data_file: RenderDataFile | None,
) -> dict[str, Any]:
    """Read the data file(s) referenced by ``binding`` and return mapped kwargs.

    Multi-source path: when ``binding.data_file_per_field`` is populated,
    fields are grouped by source path and each file is loaded once; the
    per-file results are then merged.  Single-source legacy path: when
    only ``data_file`` (matching ``binding.data_file_id``) is provided,
    every column is loaded from that one file.

    Returned dict is keyed by contract field name; values are Python
    lists (CSV/parquet) or numpy arrays (npz).
    """
    # Multi-source path — preferred when populated by data_bridge.
    if binding.data_file_per_field:
        # Group contract fields by source path.
        fields_by_path: dict[Path, dict[str, str]] = {}
        for field_name, col in binding.column_mapping.items():
            src = binding.data_file_per_field.get(field_name)
            if src is None:
                continue
            fields_by_path.setdefault(src, {})[field_name] = col
        merged: dict[str, Any] = {}
        for path, mapping in fields_by_path.items():
            merged.update(_load_columns_from_path(path, mapping))
        return merged

    # Single-source legacy path — used by tests and back-compat callers.
    if data_file is None:
        return {}
    return _load_columns_from_path(data_file.path, binding.column_mapping)


def _is_permissive(contract: StatisticalContract) -> bool:
    """Return True if ``contract`` is the all-permissive default.

    Used by the render-loop audit step to short-circuit recipes whose
    authors have NOT yet declared an explicit statistical contract — the
    default ``StatisticalContract()`` instance carries no rules to check
    so running the audit machinery against it is wasted work.

    The check is structural (compares the dataclass to the module-level
    ``DEFAULT_CONTRACT`` sentinel) so it survives equality checks across
    pickling and registry import order.
    """
    return contract == DEFAULT_CONTRACT


def _format_audit_findings(report: Any) -> str:
    """Format an ``AuditReport`` (or compatible object) as a single-line message.

    Used for ``RenderOutcome.error_message`` when the audit refuses a
    recipe; keeps the message dense enough to fit one report-table cell
    while preserving the rule_id + severity vocabulary so a downstream
    parser can recover the verdict structure.
    """
    pieces: list[str] = []
    findings = getattr(report, "findings", ()) or ()
    for f in findings:
        sev = getattr(f, "severity", "")
        rule = getattr(f, "rule_id", "")
        msg = getattr(f, "message", "")
        if sev in {"warn", "refuse"}:
            pieces.append(f"[{str(sev).upper()}] {rule}: {msg}")
    if not pieces:
        return "statistical-contract audit refused this recipe"
    return " | ".join(pieces)


def _safe_filename(full_name: str) -> str:
    """Convert ``modality.recipe`` to a filesystem-safe stem.

    The dot separator is preserved so the report links are
    unambiguous, but any other suspicious character is replaced.
    """
    cleaned = []
    for ch in full_name:
        if ch.isalnum() or ch in {".", "_", "-"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    return "".join(cleaned)


# ─────────────────────────── render loop ────────────────────────────────


def _run_audit_for_binding(
    binding: RenderBinding,
    entry: Any,
    data_file: RenderDataFile | None,
) -> tuple[Any, tuple[Any, ...]] | None:
    """Run the statistical-contract audit on a binding's data.

    Returns ``(report, findings_tuple)`` if the audit produced a report;
    returns ``None`` if the audit module is unavailable, the contract is
    permissive (default), or the data could not be re-read as a
    DataFrame for any reason (the audit is best-effort and never
    blocks rendering on its own bookkeeping failures).

    The audit reads the data via ``pandas.read_csv`` (or ``read_parquet``)
    independently of the column-mapping projection used by
    ``_load_data_for_binding`` — the audit needs the *full* data file to
    compute per-group counts, normality tests, etc.
    """
    contract = getattr(entry.metadata, "statistical_contract", None)
    if contract is None or _is_permissive(contract):
        return None
    try:
        from .statistical_audit import audit_recipe_against_data
    except ImportError:  # pragma: no cover — Build-A scaffold guard
        return None

    # Determine a primary data path. Prefer per-field map's first entry,
    # fall back to ``data_file`` (legacy single-source path).
    primary: Path | None = None
    if binding.data_file_per_field:
        primary = next(iter(binding.data_file_per_field.values()), None)
    elif data_file is not None:
        primary = data_file.path
    if primary is None:
        return None

    try:
        import pandas as pd
        suffix = primary.suffix.lower()
        if suffix in {".parquet", ".pq"}:
            df = pd.read_parquet(primary)
        elif suffix == ".csv":
            df = pd.read_csv(primary)
        else:  # .npz or anything else — skip audit, defer to render-time errors
            return None
    except Exception:  # noqa: BLE001 — audit is best-effort
        return None

    try:
        report = audit_recipe_against_data(
            contract=contract,
            data=df,
            group_column=None,
            recipe_full_name=binding.full_name,
        )
    except Exception:  # noqa: BLE001 — audit must not crash render
        return None

    return report, tuple(getattr(report, "findings", ()) or ())


def _recipe_module_path(entry: Any) -> Path | None:
    """Return the filesystem path to the recipe's source module, or None.

    Used by the provenance sidecar emitter; falls back gracefully if the
    module is built-in / frozen / stripped of source.
    """
    try:
        import inspect

        return Path(inspect.getfile(entry.render))
    except (TypeError, OSError, ValueError):
        return None


def _emit_provenance_sidecar(
    *,
    binding: RenderBinding,
    entry: Any,
    pdf_path: Path,
    data_files: list[RenderDataFile],
    audit_findings: tuple[Any, ...],
) -> None:
    """Best-effort: write a provenance.json sidecar next to ``pdf_path``.

    Failures are intentionally swallowed (logged-and-continue) — the spec
    notes (§8) that "failure to write provenance is non-fatal, logged
    as a warning."
    """
    try:
        recipe_module_path = _recipe_module_path(entry)
        if recipe_module_path is None:
            return
        # Build the data_files list in the shape build_provenance wants.
        # Resolve paths from binding.data_file_per_field (preferred,
        # multi-source) or binding.data_file_id (legacy single-source).
        seen_paths: set[Path] = set()
        data_files_meta: list[dict[str, Any]] = []
        if binding.data_file_per_field:
            for p in binding.data_file_per_field.values():
                if p in seen_paths:
                    continue
                seen_paths.add(p)
                data_files_meta.append({"path": str(p)})
        elif binding.data_file_id:
            for df in data_files:
                if df.file_id == binding.data_file_id:
                    data_files_meta.append({"path": str(df.path)})
                    break

        # Translate audit_findings into the rules_passed/warned/failed shape.
        audit_meta: dict[str, Any] | None = None
        if audit_findings:
            audit_meta = {
                "rules_passed": [],
                "rules_warned": [
                    str(getattr(f, "rule_id", ""))
                    for f in audit_findings
                    if str(getattr(f, "severity", "")).lower() == "warn"
                ],
                "rules_failed": [
                    str(getattr(f, "rule_id", ""))
                    for f in audit_findings
                    if str(getattr(f, "severity", "")).lower() == "refuse"
                ],
            }

        record = build_provenance(
            figure_path=pdf_path,
            recipe_full_name=binding.full_name,
            recipe_module_path=recipe_module_path,
            panelforge_version=__version__,
            panelforge_git_commit=_git_commit_short(),
            data_files=data_files_meta,
            column_mapping=dict(binding.column_mapping),
            scorer_state=None,
            audit_findings=audit_meta,
        )
        write_provenance_json(record)
    except Exception:  # noqa: BLE001 — provenance is best-effort
        return


def _render_one(
    binding: RenderBinding,
    data_file: RenderDataFile | None,
    out_dir: Path,
    dpi: int,
    figsize: tuple[float, float],
    *,
    skip_audit: bool = False,
    enable_provenance: bool = True,
    all_data_files: list[RenderDataFile] | None = None,
) -> RenderOutcome:
    """Execute a single recipe and return its outcome.

    Re-raises ``ImportError`` / ``ModuleNotFoundError`` / ``OSError`` /
    ``KeyboardInterrupt`` so the caller can convert them into halts.

    When ``skip_audit`` is False (the default), the per-recipe
    :class:`StatisticalContract` audit runs after the recipe is looked
    up but before the contract is constructed. A ``refuse`` verdict
    short-circuits the rest of the pipeline with status
    ``error_audit_refuse``; ``warn`` and ``pass`` verdicts proceed
    normally with the findings recorded on the outcome.
    """
    started = time.perf_counter()

    if not binding.fully_bound:
        return RenderOutcome(
            full_name=binding.full_name,
            status="skipped_unbound",
            pdf_path=None,
            png_path=None,
            error_class=None,
            error_message=binding.unbound_reason or "binding incomplete",
            traceback_excerpt=None,
            elapsed_seconds=time.perf_counter() - started,
        )

    # Lookup recipe — KeyError is a per-recipe error.
    try:
        entry = get_recipe(binding.full_name)
    except KeyError as exc:
        return RenderOutcome(
            full_name=binding.full_name,
            status="error_render",
            pdf_path=None,
            png_path=None,
            error_class=type(exc).__name__,
            error_message=str(exc),
            traceback_excerpt=_excerpt_traceback(exc),
            elapsed_seconds=time.perf_counter() - started,
        )

    # Statistical-contract audit (Sprint 1A — v1.7.0). Skip when the
    # contract is the default permissive (e.g. recipes without explicit
    # contracts) OR when --skip-audit was passed.
    audit_findings: tuple[Any, ...] = ()
    if not skip_audit:
        audit_result = _run_audit_for_binding(binding, entry, data_file)
        if audit_result is not None:
            report, audit_findings = audit_result
            overall = str(getattr(report, "overall", "")).lower()
            if overall == "refuse":
                return RenderOutcome(
                    full_name=binding.full_name,
                    status="error_audit_refuse",
                    pdf_path=None,
                    png_path=None,
                    error_class="StatisticalContractViolation",
                    error_message=_format_audit_findings(report),
                    traceback_excerpt=None,
                    elapsed_seconds=time.perf_counter() - started,
                    audit_findings=audit_findings,
                )

    # Load data — pandas/numpy may raise OSError on missing file (caller halts)
    # or generic Exception on parse problems (we capture).
    try:
        mapped = _load_data_for_binding(binding, data_file)
    except (ImportError, ModuleNotFoundError, OSError):
        raise
    except Exception as exc:
        return RenderOutcome(
            full_name=binding.full_name,
            status="error_render",
            pdf_path=None,
            png_path=None,
            error_class=type(exc).__name__,
            error_message=str(exc),
            traceback_excerpt=_excerpt_traceback(exc),
            elapsed_seconds=time.perf_counter() - started,
            audit_findings=audit_findings,
        )

    # Build contract.
    try:
        contract_obj = entry.contract(**mapped)
    except ValidationError as exc:
        return RenderOutcome(
            full_name=binding.full_name,
            status="error_contract",
            pdf_path=None,
            png_path=None,
            error_class="ContractValidationError",
            error_message=str(exc),
            traceback_excerpt=_excerpt_traceback(exc),
            elapsed_seconds=time.perf_counter() - started,
            audit_findings=audit_findings,
        )
    except (ImportError, ModuleNotFoundError, OSError):
        raise
    except Exception as exc:
        return RenderOutcome(
            full_name=binding.full_name,
            status="error_render",
            pdf_path=None,
            png_path=None,
            error_class=type(exc).__name__,
            error_message=str(exc),
            traceback_excerpt=_excerpt_traceback(exc),
            elapsed_seconds=time.perf_counter() - started,
            audit_findings=audit_findings,
        )

    # Render + save.  Matplotlib import is lazy so an environment without
    # mpl raises ImportError → caller halts.
    import matplotlib.pyplot as plt

    stem = _safe_filename(binding.full_name)
    pdf_path = out_dir / f"{stem}.pdf"
    png_path = out_dir / f"{stem}.png"

    fig, ax = plt.subplots(figsize=figsize)
    try:
        try:
            entry.render(contract_obj, ax=ax)
            fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
            fig.savefig(png_path, format="png", dpi=dpi, bbox_inches="tight")
        except (ImportError, ModuleNotFoundError, OSError):
            raise
        except Exception as exc:
            return RenderOutcome(
                full_name=binding.full_name,
                status="error_render",
                pdf_path=None,
                png_path=None,
                error_class=type(exc).__name__,
                error_message=str(exc),
                traceback_excerpt=_excerpt_traceback(exc),
                elapsed_seconds=time.perf_counter() - started,
                audit_findings=audit_findings,
            )
    finally:
        plt.close(fig)

    # Provenance sidecar — Sprint 1B (PR #62).  Best-effort; failures
    # do NOT change the render outcome.  See spec §8.
    if enable_provenance:
        _emit_provenance_sidecar(
            binding=binding,
            entry=entry,
            pdf_path=pdf_path,
            data_files=list(all_data_files or []),
            audit_findings=audit_findings,
        )

    return RenderOutcome(
        full_name=binding.full_name,
        status="success",
        pdf_path=pdf_path,
        png_path=png_path,
        error_class=None,
        error_message=None,
        traceback_excerpt=None,
        elapsed_seconds=time.perf_counter() - started,
        audit_findings=audit_findings,
    )


def render_shortlist(
    *,
    bindings: list[RenderBinding],
    data_files: list[RenderDataFile],
    out_dir: Path = Path("figures"),
    dpi: int = 300,
    figsize: tuple[float, float] = (4.2, 3.2),
    skip_audit: bool = False,
    enable_provenance: bool = True,
) -> RenderLog:
    """Run the render loop over a confirmed shortlist of bindings.

    Per-recipe exceptions are captured as :class:`RenderOutcome` rows.
    ``ImportError`` / ``ModuleNotFoundError`` / ``OSError`` raise
    :class:`EnvironmentalFailure` and halt the loop immediately;
    ``KeyboardInterrupt`` propagates unchanged.

    Parameters
    ----------
    skip_audit
        Sprint 1A (v1.7.0) escape hatch.  When ``True``, the per-recipe
        :class:`StatisticalContract` audit is bypassed and the loop
        reverts to its pre-1.7 behaviour (intake → score → bind →
        render → report). When ``False`` (default), every recipe with
        a non-permissive contract is audited before render; refused
        bindings produce ``RenderOutcome(status="error_audit_refuse")``
        and are NOT rendered.  See ``docs/spec_statistical_contract.md``
        §4 for the pipeline placement rationale.
    enable_provenance
        Sprint 1B (PR #62) toggle.  When ``True`` (default), every
        successful render emits a ``<figure>.pdf.provenance.json``
        sidecar next to the PDF/PNG.  When ``False``, no sidecars are
        written — useful for tight dev loops via ``--no-provenance``.
        Sidecar emission is best-effort; failures are non-fatal and do
        not change the render outcome.  See ``docs/spec_provenance_chain.md``
        §8.
    """
    started_at = _utc_iso()

    out_dir = Path(out_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise EnvironmentalFailure(
            f"cannot create output directory {out_dir!s}: {exc}"
        ) from exc

    file_index = {f.file_id: f for f in data_files}

    outcomes: list[RenderOutcome] = []
    n_success = 0
    n_skipped = 0
    n_failed = 0

    for binding in bindings:
        df = file_index.get(binding.data_file_id) if binding.data_file_id else None
        try:
            outcome = _render_one(
                binding, df, out_dir, dpi, figsize,
                skip_audit=skip_audit,
                enable_provenance=enable_provenance,
                all_data_files=data_files,
            )
        except (ImportError, ModuleNotFoundError) as exc:
            raise EnvironmentalFailure(
                f"missing dependency while rendering {binding.full_name!r}: {exc}"
            ) from exc
        except OSError as exc:
            raise EnvironmentalFailure(
                f"OS error while rendering {binding.full_name!r}: {exc}"
            ) from exc

        outcomes.append(outcome)
        if outcome.status == "success":
            n_success += 1
        elif outcome.status == "skipped_unbound":
            n_skipped += 1
        else:
            n_failed += 1

    finished_at = _utc_iso()

    return RenderLog(
        project_root=out_dir.resolve().parent,
        n_attempted=len(bindings),
        n_success=n_success,
        n_skipped=n_skipped,
        n_failed=n_failed,
        outcomes=tuple(outcomes),
        started_at=started_at,
        finished_at=finished_at,
    )


# ─────────────────────────── report writer ──────────────────────────────


def _md_escape(s: str) -> str:
    """Escape pipes and newlines for safe inclusion in a Markdown table cell."""
    return s.replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def write_render_report(
    log: RenderLog,
    report_path: Path | None = None,
) -> Path:
    """Write a Markdown render report from ``log`` and return its path.

    Default location is ``figures/RENDER_REPORT.md`` (resolved relative
    to the first successful outcome's output dir, falling back to
    ``log.project_root / "figures"``).
    """
    if report_path is None:
        # Pick the directory the outcomes wrote into.
        first_path: Path | None = next(
            (o.pdf_path for o in log.outcomes if o.pdf_path is not None), None
        )
        out_dir = first_path.parent if first_path is not None else (
            log.project_root / "figures"
        )
        report_path = out_dir / "RENDER_REPORT.md"

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Render Report")
    lines.append("")
    lines.append(f"**Generated:** {log.finished_at}")
    lines.append(f"**panelforge version:** {__version__}")
    lines.append(f"**panelforge git commit:** {_git_commit_short()}")
    lines.append(f"**Project:** {log.project_root}")
    lines.append(f"**Total recipes attempted:** {log.n_attempted}")
    lines.append(f"**Rendered:** {log.n_success}")
    lines.append(f"**Skipped (unbound):** {log.n_skipped}")
    lines.append(f"**Failed (render error):** {log.n_failed}")
    lines.append("")

    # Successful section
    successes = [o for o in log.outcomes if o.status == "success"]
    lines.append(f"## Successful ({len(successes)})")
    lines.append("")
    if successes:
        lines.append("| # | Recipe | Output | Render time |")
        lines.append("|---|---|---|---|")
        for i, o in enumerate(successes, 1):
            pdf = str(o.pdf_path) if o.pdf_path else ""
            lines.append(
                f"| {i} | {_md_escape(o.full_name)} | {_md_escape(pdf)} "
                f"| {o.elapsed_seconds:.2f} s |"
            )
    else:
        lines.append("_No recipes rendered successfully._")
    lines.append("")

    # Skipped section
    skipped = [o for o in log.outcomes if o.status == "skipped_unbound"]
    lines.append(f"## Skipped ({len(skipped)})")
    lines.append("")
    if skipped:
        lines.append("| Recipe | Reason | Remediation |")
        lines.append("|---|---|---|")
        for o in skipped:
            reason = o.error_message or "binding incomplete"
            lines.append(
                f"| {_md_escape(o.full_name)} | {_md_escape(reason)} "
                f"| Add the missing column or remove from shortlist |"
            )
    else:
        lines.append("_No recipes skipped._")
    lines.append("")

    # Failed section — render-time errors (NOT audit refusals; those are
    # broken out into their own section below).
    failed = [
        o for o in log.outcomes
        if o.status in {"error_contract", "error_render"}
    ]
    lines.append(f"## Failed ({len(failed)})")
    lines.append("")
    if failed:
        lines.append("| Recipe | Error class | Message | Traceback |")
        lines.append("|---|---|---|---|")
        for o in failed:
            cls = o.error_class or ""
            msg = o.error_message or ""
            tb = o.traceback_excerpt or ""
            lines.append(
                f"| {_md_escape(o.full_name)} | {_md_escape(cls)} "
                f"| {_md_escape(msg)} | {_md_escape(tb)} |"
            )
    else:
        lines.append("_No render errors._")
    lines.append("")

    # Audit-refused section (Sprint 1A — v1.7.0). Recipes whose
    # statistical-contract audit returned ``overall == "refuse"`` were
    # NOT rendered; we surface them here so the user can act on the
    # offending rule_id rather than scanning the generic Failed table.
    audit_refused = [o for o in log.outcomes if o.status == "error_audit_refuse"]
    lines.append(f"## Audit refused ({len(audit_refused)})")
    lines.append("")
    if audit_refused:
        lines.append("| Recipe | Findings |")
        lines.append("|---|---|")
        for o in audit_refused:
            msg = o.error_message or "audit refused (no message)"
            lines.append(
                f"| {_md_escape(o.full_name)} | {_md_escape(msg)} |"
            )
    else:
        lines.append("_No recipes refused by statistical audit._")
    lines.append("")

    # Statistical warnings — surfaced from any outcome that carries
    # non-empty audit findings whose severity is "warn". These rendered
    # successfully but the report flags them so the figure consumer can
    # decide whether to trust them.
    warned: list[tuple[RenderOutcome, list[Any]]] = []
    for o in log.outcomes:
        warns = [
            f for f in o.audit_findings
            if str(getattr(f, "severity", "")).lower() == "warn"
        ]
        if warns:
            warned.append((o, warns))
    lines.append(f"## Statistical warnings ({len(warned)})")
    lines.append("")
    if warned:
        for o, warns in warned:
            lines.append(f"### {o.full_name}")
            for w in warns:
                rule = getattr(w, "rule_id", "<unknown>")
                msg = getattr(w, "message", "")
                lines.append(f"- **rule:** {rule}")
                lines.append(f"  **observed:** {msg}")
            lines.append("")
    else:
        lines.append("_No statistical warnings emitted._")
    lines.append("")

    # Next steps
    lines.append("## Next steps")
    lines.append("")
    lines.append(
        f"- Fix the {log.n_failed} failed recipes by addressing data "
        "shape issues."
    )
    lines.append(
        f"- For the {log.n_skipped} skipped recipes, add data or remove "
        "from shortlist."
    )
    if audit_refused:
        lines.append(
            f"- For the {len(audit_refused)} audit-refused recipes, either "
            "collect more data, pick a recipe with a more permissive "
            "statistical contract, or rerun with `figures generate "
            "--skip-audit` (NOT recommended for production)."
        )
    lines.append(
        "- Re-run with `figures generate` to render only the previously-failed "
        "recipes."
    )
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


__all__ = [
    "RenderDataFile",
    "EnvironmentalFailure",
    "RenderBinding",
    "RenderLog",
    "RenderOutcome",
    "render_shortlist",
    "write_render_report",
]
