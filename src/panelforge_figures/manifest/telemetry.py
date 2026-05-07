"""Active-learning telemetry channel — Sprint 3B (W6 — v1.7.0).

See ``docs/spec_active_learning.md`` for the full design.

Telemetry is **fully opt-in** and **never auto-uploaded**.  A vanilla
install writes nothing to disk regardless of how many ``figures
generate`` calls happen.  The only activation path is the line
``telemetry: opt-in`` inside ``<project_root>/panelforge.project.yaml``
— a VCS-tracked, project-level record of consent.

Public API consumed by gate sites
---------------------------------

::

    from panelforge_figures.manifest.telemetry import (
        TelemetryRow,
        TelemetryError,
        is_telemetry_enabled,
        log_invocation,
        set_user_pick,
        export_telemetry,
        telemetry_log_path,
    )

Privacy invariants (spec §9):

* The on-disk schema (``TelemetryRow``) records only **categorical**
  ``ProjectProfile`` fields — never raw ``manuscript.md`` text, CSV row
  contents, file paths, or DOIs.  Unknown ``profile`` keys are silently
  dropped at log time.
* ``scored_top_5`` rows are validated to ``{full_name: str, score:
  float, tags: dict[str, float]}``; malformed rows are dropped with
  a ``RuntimeWarning`` rather than raising — telemetry must never leak
  exceptions into the figure-generation path.
* Writes are atomic via ``os.replace`` so a crash mid-flush cannot
  corrupt the JSONL.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
import warnings
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

__all__ = [
    "TelemetryError",
    "TelemetryRow",
    "export_telemetry",
    "is_telemetry_enabled",
    "log_invocation",
    "set_user_pick",
    "telemetry_log_path",
]


# ---------------------------------------------------------------------------
# Locked constants — spec §2 / §9.
# ---------------------------------------------------------------------------

# Whitelist of categorical ``profile`` keys allowed on disk.  Spec §9:
# any key outside this set is silently dropped at log time.  We never
# raise from the telemetry path — exceptions must not leak into
# ``figures generate``.
_PROFILE_WHITELIST: frozenset[str] = frozenset(
    {
        "modality",
        "factorial_design",
        "equivalence_present",
        "anchor_strength",
        "dynamics_kind",
        "dimensionality",
        "shortlist_size",
    }
)

# Workspace directory + log filename — fixed by spec §2.
_WORKSPACE_DIR: str = "panelforge_workspace"
_LOG_FILENAME: str = "usage.jsonl"
_PROJECT_YAML: str = "panelforge.project.yaml"

# ``set_user_pick`` requires an explicit ``--session-id`` when more
# than one row in the last hour has ``user_picked: null`` (spec §12,
# row 6 — race-safety for parallel sessions).
_PICK_AMBIGUITY_WINDOW: timedelta = timedelta(hours=1)


# ---------------------------------------------------------------------------
# Errors and dataclasses
# ---------------------------------------------------------------------------


class TelemetryError(RuntimeError):
    """Raised by :func:`set_user_pick` when no candidate row exists or
    when multiple candidate rows are ambiguous within the last hour and
    no ``session_id`` was supplied.

    Logging itself never raises — it returns an empty string on any
    error so figure generation is unaffected.
    """


@dataclass(frozen=True)
class TelemetryRow:
    """One JSONL row — schema locked by spec §2.

    ``session_id`` is a fresh ``uuid.uuid4().hex`` per generate call (no
    derivation from hostname/user). ``profile`` carries only categorical
    fields per ``_PROFILE_WHITELIST``. ``scored_top_5`` is up to five
    funnel rows. ``user_picked`` is ``None`` until ``set_user_pick`` runs;
    ``rejected_higher_scored`` is the calibration signal computed there.
    """

    session_id: str
    timestamp: str
    panelforge_version: str
    scoring_rubric_version: str
    profile: dict[str, Any]
    scored_top_5: list[dict[str, Any]]
    user_picked: str | None
    rejected_higher_scored: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public predicates and path resolvers
# ---------------------------------------------------------------------------


def telemetry_log_path(project_root: Path) -> Path:
    """Return ``<project_root>/panelforge_workspace/usage.jsonl``.

    Pure function; does not touch the filesystem.
    """
    return Path(project_root) / _WORKSPACE_DIR / _LOG_FILENAME


def is_telemetry_enabled(project_root: Path) -> bool:
    """Return True iff ``panelforge.project.yaml`` declares
    ``telemetry: opt-in``.

    Default: False.  Returns False on any read error (missing file,
    bad YAML, permission denied, etc.) — telemetry is opt-in,
    fail-closed by spec §3.
    """
    yaml_path = Path(project_root) / _PROJECT_YAML
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    # We do not import pyyaml here even though the rest of the package
    # does — the opt-in line is a flat scalar key and a regex-shaped
    # check keeps the telemetry path zero-dependency / fail-closed.
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        if key.strip() != "telemetry":
            continue
        return value.strip().strip("\"'").lower() == "opt-in"
    return False


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _utc_now_iso() -> str:
    """ISO-8601 UTC timestamp with the spec-mandated ``Z`` suffix."""
    return (
        datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _sanitize_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Drop any key outside ``_PROFILE_WHITELIST``.  Never raises."""
    return {k: v for k, v in profile.items() if k in _PROFILE_WHITELIST}


def _is_real_number(value: Any) -> bool:
    """Numeric-but-not-bool check — bool is a subclass of int in Python."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _sanitize_scored_top_5(
    rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Validate each row is ``{full_name: str, score: float, tags:
    dict[str, float]}``.  Reject the whole list with ``RuntimeWarning``
    on any malformed row — telemetry must never raise (spec §9), so the
    shortlist silently downgrades to ``[]``.
    """
    def _bail(msg: str) -> list[dict[str, Any]]:
        warnings.warn(f"telemetry: {msg}", RuntimeWarning, stacklevel=4)
        return []

    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            return _bail("dropping non-mapping row in scored_top_5")
        full_name = raw.get("full_name")
        score = raw.get("score")
        tags = raw.get("tags")
        if not isinstance(full_name, str):
            return _bail("scored_top_5 row missing string full_name")
        if not _is_real_number(score):
            return _bail("scored_top_5 row missing numeric score")
        if not isinstance(tags, Mapping):
            return _bail("scored_top_5 row missing tags mapping")
        coerced_tags: dict[str, float] = {}
        for tk, tv in tags.items():
            if not isinstance(tk, str):
                return _bail("tags must use string keys")
            if not _is_real_number(tv):
                return _bail("tag values must be numeric")
            coerced_tags[tk] = float(tv)
        out.append({"full_name": full_name, "score": float(score), "tags": coerced_tags})
    # Defensive cap — caller is expected to truncate but spec §2 mandates ≤5.
    return out[:5]


def _atomic_write_text(target: Path, text: str, *, prefix: str) -> None:
    """Write ``text`` to ``target`` atomically (tempfile + ``os.replace``).

    The replace is atomic on POSIX and Windows-NTFS, so concurrent
    readers never see a partial JSONL row.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp_path, target)
    except Exception:
        # Best-effort cleanup; telemetry must never leak exceptions.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _atomic_append(log_path: Path, line: str) -> None:
    """Append one JSONL line — read-existing-then-replace for atomicity."""
    existing = ""
    if log_path.exists():
        try:
            existing = log_path.read_text(encoding="utf-8")
        except OSError:
            existing = ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    if not line.endswith("\n"):
        line += "\n"
    _atomic_write_text(log_path, existing + line, prefix=".usage.jsonl.")


def log_invocation(
    project_root: Path,
    *,
    profile: Mapping[str, Any],
    scored_top_5: list[Mapping[str, Any]],
    panelforge_version: str,
    scoring_rubric_version: str,
) -> str:
    """Append one row with ``user_picked=null`` to ``usage.jsonl``.

    Returns the new ``uuid.uuid4().hex`` ``session_id``.  No-op (returns
    empty string) if :func:`is_telemetry_enabled` is False; never
    creates the file in that case.  Errors inside the telemetry path
    are swallowed (spec §9 — figure generation must keep going).
    """
    project_root = Path(project_root)
    if not is_telemetry_enabled(project_root):
        return ""

    try:
        session_id = uuid.uuid4().hex
        row = TelemetryRow(
            session_id=session_id,
            timestamp=_utc_now_iso(),
            panelforge_version=str(panelforge_version),
            scoring_rubric_version=str(scoring_rubric_version),
            profile=_sanitize_profile(profile),
            scored_top_5=_sanitize_scored_top_5(list(scored_top_5)),
            user_picked=None,
            rejected_higher_scored=[],
        )
        log_path = telemetry_log_path(project_root)
        line = json.dumps(asdict(row), separators=(",", ":"), sort_keys=True)
        _atomic_append(log_path, line)
        return session_id
    except Exception:
        # Telemetry must never break figure generation.  We swallow
        # all errors and return the empty string; the caller treats
        # an empty session_id as "no row was recorded".
        return ""


# ---------------------------------------------------------------------------
# Pick resolution
# ---------------------------------------------------------------------------


def _read_all_rows(log_path: Path) -> list[dict[str, Any]]:
    """Parse ``usage.jsonl`` into a list of dicts.

    Malformed lines are skipped with a ``RuntimeWarning`` rather than
    raising; the file is user-managed plain text per spec §2 and may
    contain hand-edits.
    """
    if not log_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            warnings.warn(
                f"telemetry: skipping malformed JSONL row {lineno}",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
        if not isinstance(obj, dict):
            continue
        rows.append(obj)
    return rows


def _parse_iso(timestamp: str) -> datetime | None:
    """Parse spec-mandated ``...Z`` ISO-8601 stamps; tolerate ``+00:00``."""
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _compute_rejected_higher(
    scored_top_5: list[Any], full_name: str
) -> list[str]:
    """Return ``[r.full_name for r in scored_top_5 if r.score > picked.score]``.

    Returns ``[]`` if ``full_name`` is not in the recorded top-5 (the
    user picked something outside the funnel — no calibration signal).
    """
    picked_score: float | None = None
    for entry in scored_top_5:
        if isinstance(entry, dict) and entry.get("full_name") == full_name:
            score = entry.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                picked_score = float(score)
            break
    if picked_score is None:
        return []
    out: list[str] = []
    for entry in scored_top_5:
        if not isinstance(entry, dict):
            continue
        score = entry.get("score")
        name = entry.get("full_name")
        if (
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and isinstance(name, str)
            and float(score) > picked_score
        ):
            out.append(name)
    return out


def _atomic_write_rows(log_path: Path, rows: list[dict[str, Any]]) -> None:
    """Replace ``log_path`` with the JSONL serialisation of ``rows``."""
    body = "".join(
        json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n" for row in rows
    )
    _atomic_write_text(log_path, body, prefix=".usage.jsonl.")


def set_user_pick(
    project_root: Path,
    full_name: str,
    *,
    session_id: str | None = None,
) -> TelemetryRow:
    """Record the user's recipe pick into ``usage.jsonl``.

    With ``session_id``, target that exact row (raise if missing).
    Without, target the unique row with ``user_picked is None`` —
    ambiguity within the last hour raises :class:`TelemetryError` per
    spec §12 row 6 (race-safety for parallel sessions); ambiguity older
    than that falls back to the most recent unpicked row.

    Updates the row in place: ``user_picked = full_name`` and
    ``rejected_higher_scored = [r.full_name for r in scored_top_5 if
    r.score > picked.score]``.  If ``full_name`` is not in the recorded
    top-5 the rejected list is empty (no calibration signal).  Writes
    atomically via ``os.replace``.
    """
    project_root = Path(project_root)
    log_path = telemetry_log_path(project_root)
    rows = _read_all_rows(log_path)
    if not rows:
        raise TelemetryError(
            f"no telemetry rows found at {log_path}; "
            "run `figures generate` before `figures pick`"
        )

    target_idx: int | None = None
    if session_id is not None:
        for idx, row in enumerate(rows):
            if row.get("session_id") == session_id:
                target_idx = idx
                break
        if target_idx is None:
            raise TelemetryError(
                f"no telemetry row found with session_id={session_id!r}"
            )
    else:
        unpicked: list[int] = [
            idx for idx, row in enumerate(rows) if row.get("user_picked") is None
        ]
        if not unpicked:
            raise TelemetryError(
                "no unpicked telemetry rows found; "
                "every recorded session already has a `user_picked` value"
            )
        if len(unpicked) == 1:
            target_idx = unpicked[0]
        else:
            now = datetime.now(UTC)
            recent: list[int] = []
            for idx in unpicked:
                ts = _parse_iso(rows[idx].get("timestamp", ""))
                if ts is None:
                    continue
                if now - ts <= _PICK_AMBIGUITY_WINDOW:
                    recent.append(idx)
            if len(recent) > 1:
                raise TelemetryError(
                    f"{len(recent)} unpicked telemetry rows in the last hour; "
                    "pass --session-id <hex> to disambiguate"
                )
            if len(recent) == 1:
                target_idx = recent[0]
            else:
                # All unpicked rows are stale (>1h); fall back to the
                # most recent one rather than failing — single-user case.
                target_idx = unpicked[-1]

    assert target_idx is not None  # invariant: every branch above sets it.
    row = rows[target_idx]
    rejected = _compute_rejected_higher(row.get("scored_top_5") or [], full_name)
    row["user_picked"] = full_name
    row["rejected_higher_scored"] = rejected

    _atomic_write_rows(log_path, rows)

    return TelemetryRow(
        session_id=str(row.get("session_id", "")),
        timestamp=str(row.get("timestamp", "")),
        panelforge_version=str(row.get("panelforge_version", "")),
        scoring_rubric_version=str(row.get("scoring_rubric_version", "")),
        profile=dict(row.get("profile") or {}),
        scored_top_5=list(row.get("scored_top_5") or []),
        user_picked=full_name,
        rejected_higher_scored=rejected,
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_telemetry(
    project_root: Path,
    output_path: Path,
    *,
    anonymize: bool = True,
    drop_unpicked: bool = True,
) -> int:
    """Sanitise and export ``usage.jsonl`` to ``output_path`` as JSONL.

    With ``drop_unpicked`` (default True) rows where ``user_picked is
    None`` are dropped.  With ``anonymize`` (default True) each
    ``session_id`` is replaced with ``sha256(session_id)[:16]`` per
    spec §9.  No upload is performed; the user manually transmits
    ``output_path``.  Returns the number of rows written.
    """
    project_root = Path(project_root)
    output_path = Path(output_path)
    rows = _read_all_rows(telemetry_log_path(project_root))

    selected: list[dict[str, Any]] = []
    for row in rows:
        if drop_unpicked and row.get("user_picked") is None:
            continue
        if anonymize:
            sid = row.get("session_id")
            if isinstance(sid, str) and sid:
                digest = hashlib.sha256(sid.encode("utf-8")).hexdigest()
                row = {**row, "session_id": digest[:16]}
        selected.append(row)

    body = "".join(
        json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n" for r in selected
    )
    _atomic_write_text(output_path, body, prefix=".telemetry-export.")
    return len(selected)
