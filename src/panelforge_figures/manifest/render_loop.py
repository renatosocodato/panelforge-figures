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
``fully_bound``, ``column_mapping``, ``data_file_id`` and (when unbound)
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
    """

    full_name: str
    fully_bound: bool
    column_mapping: dict[str, str] = field(default_factory=dict)
    data_file_id: str | None = None
    unbound_reason: str | None = None


@dataclass(frozen=True)
class RenderDataFile:
    """Structural shape for a data file referenced by a binding."""

    file_id: str
    path: Path


@dataclass(frozen=True)
class RenderOutcome:
    """Per-recipe render result captured by the loop."""

    full_name: str
    status: str  # "success" | "skipped_unbound" | "error_contract" | "error_render"
    pdf_path: Path | None
    png_path: Path | None
    error_class: str | None
    error_message: str | None
    traceback_excerpt: str | None  # last 5 lines if applicable
    elapsed_seconds: float


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


def _load_data_for_binding(
    binding: RenderBinding,
    data_file: RenderDataFile | None,
) -> dict[str, Any]:
    """Read the data file referenced by ``binding`` and return mapped kwargs.

    Supports CSV, Parquet, and NPZ.  The returned dict is keyed by
    contract field name (the *target* of ``column_mapping``); values are
    Python lists (CSV/parquet) or numpy arrays (npz).
    """
    if data_file is None:
        return {}
    suffix = data_file.path.suffix.lower()

    if suffix == ".csv":
        import pandas as pd

        df = pd.read_csv(data_file.path)
        return {
            field_name: df[col].tolist()
            for field_name, col in binding.column_mapping.items()
            if col in df.columns
        }

    if suffix in (".parquet", ".pq"):
        import pandas as pd

        df = pd.read_parquet(data_file.path)
        return {
            field_name: df[col].tolist()
            for field_name, col in binding.column_mapping.items()
            if col in df.columns
        }

    if suffix == ".npz":
        import numpy as np

        with np.load(data_file.path) as bundle:
            return {
                field_name: bundle[col]
                for field_name, col in binding.column_mapping.items()
                if col in bundle.files
            }

    raise ValueError(f"unsupported data file format: {data_file.path.suffix!r}")


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


def _render_one(
    binding: RenderBinding,
    data_file: RenderDataFile | None,
    out_dir: Path,
    dpi: int,
    figsize: tuple[float, float],
) -> RenderOutcome:
    """Execute a single recipe and return its outcome.

    Re-raises ``ImportError`` / ``ModuleNotFoundError`` / ``OSError`` /
    ``KeyboardInterrupt`` so the caller can convert them into halts.
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
            )
    finally:
        plt.close(fig)

    return RenderOutcome(
        full_name=binding.full_name,
        status="success",
        pdf_path=pdf_path,
        png_path=png_path,
        error_class=None,
        error_message=None,
        traceback_excerpt=None,
        elapsed_seconds=time.perf_counter() - started,
    )


def render_shortlist(
    *,
    bindings: list[RenderBinding],
    data_files: list[RenderDataFile],
    out_dir: Path = Path("figures"),
    dpi: int = 300,
    figsize: tuple[float, float] = (4.2, 3.2),
) -> RenderLog:
    """Run the render loop over a confirmed shortlist of bindings.

    Per-recipe exceptions are captured as :class:`RenderOutcome` rows.
    ``ImportError`` / ``ModuleNotFoundError`` / ``OSError`` raise
    :class:`EnvironmentalFailure` and halt the loop immediately;
    ``KeyboardInterrupt`` propagates unchanged.
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
            outcome = _render_one(binding, df, out_dir, dpi, figsize)
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

    # Failed section
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

    # Next steps
    lines.append("## Next steps")
    lines.append("")
    lines.append(
        "- Fix the F failed recipes by addressing data shape issues."
    )
    lines.append(
        "- For the K skipped recipes, add data or remove from shortlist."
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
