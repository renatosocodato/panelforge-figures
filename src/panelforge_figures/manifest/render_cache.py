"""Incremental render cache (Elevation 11 — v3.5.0).

Tracks per-panel input SHAs (recipe source, contract, data files) and
output SHAs so ``figures execute-plan`` can short-circuit rendering when
nothing has changed.

Critical for manuscript revision cycles: editing one data file should
re-render only the panels that depend on it, not all 12 figures.

Cache lives at ``panelforge_workspace/render_cache.json``; the schema is
versioned (``CACHE_SCHEMA_VERSION``) and any mismatch causes the cache
to be silently invalidated with a ``RuntimeWarning``.

Public surface
--------------
- :class:`CacheEntry` — one row per rendered panel.
- :class:`RenderCache` — the on-disk store.
- :class:`CacheStatus` — staleness enum (``fresh`` / ``missing`` /
  ``stale_data`` / ``stale_recipe`` / ``stale_contract`` /
  ``stale_output`` / ``unknown``).
- :class:`RenderCacheError` — corrupted / schema-mismatched cache.
- :func:`compute_recipe_sha`, :func:`compute_contract_sha`,
  :func:`compute_data_sha` — SHA helpers.
- :func:`load_cache`, :func:`save_cache` — atomic disk I/O.
- :func:`check_staleness` — compare current SHAs vs cached entry.
- :func:`update_cache_entry` — record a fresh render in the cache.
- :func:`summarize_cache_state` — aggregate counters for reporting.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "CACHE_FILENAME",
    "CACHE_SCHEMA_VERSION",
    "CacheEntry",
    "CacheStatus",
    "RenderCache",
    "RenderCacheError",
    "cache_path_for_project",
    "check_staleness",
    "compute_contract_sha",
    "compute_data_sha",
    "compute_recipe_sha",
    "load_cache",
    "save_cache",
    "summarize_cache_state",
    "update_cache_entry",
]


CACHE_SCHEMA_VERSION = "1.0.0"
CACHE_FILENAME = "render_cache.json"


class CacheStatus(StrEnum):
    """Per-panel staleness verdict.

    The values are the literal strings emitted in JSON; ``StrEnum``
    keeps them comparable to bare strings without a cast.
    """

    fresh = "fresh"
    """All SHAs match the cached entry → render can be skipped."""

    missing = "missing"
    """Panel has no cache entry → must render."""

    stale_data = "stale_data"
    """Cached entry exists but the data SHA changed → must re-render."""

    stale_recipe = "stale_recipe"
    """Recipe source file changed → must re-render."""

    stale_contract = "stale_contract"
    """Contract dict changed → must re-render."""

    stale_output = "stale_output"
    """Cache says rendered but the output PDF/PNG was deleted."""

    unknown = "unknown"
    """Reserved for forward compatibility / corrupt entries."""


class RenderCacheError(RuntimeError):
    """Raised on unrecoverable cache failures (e.g. write failures).

    Soft failures (corrupt JSON, schema mismatch) emit a
    ``RuntimeWarning`` and return an empty cache instead — the caller
    keeps making progress; the next save overwrites the stale file.
    """


# ─────────────────────────── dataclasses ────────────────────────────────


@dataclass(frozen=True)
class CacheEntry:
    """One row per rendered panel.

    Attributes
    ----------
    figure_id
        Figure identifier as it appears in the plan (e.g. ``"1A"`` or
        ``"figure_1"``).  Free-form string — no parsing applied.
    panel_id
        Panel identifier within the figure (e.g. ``"panel_1A"``).  Used
        as the primary key in :class:`RenderCache`.
    recipe_full_name
        Fully-qualified recipe name, ``"{modality}.{recipe_name}"``.
    recipe_sha
        sha256 hex digest of the recipe ``.py`` file bytes, or empty
        string when the recipe couldn't be located on disk.
    contract_sha
        sha256 of the canonicalised JSON of the input-contract dict.
    data_sha
        sha256 over the sorted list of ``(relpath, file_sha)`` pairs of
        the panel's input data files.  Empty input → fixed sentinel.
    output_sha
        sha256 of the rendered output (PDF or PNG); empty when the
        output file is missing at update time (defensive).
    output_path
        Repo-relative path to the rendered file as a string.
    rendered_at
        ISO-8601 UTC timestamp with a ``"Z"`` suffix (no offset).
    panelforge_version
        ``panelforge_figures.__version__`` at the time of render.
    notes
        Free-form tuple of human-readable notes (e.g. ``"rendered"``
        or ``"re-rendered: stale_data"``).
    """

    figure_id: str
    panel_id: str
    recipe_full_name: str
    recipe_sha: str
    contract_sha: str
    data_sha: str
    output_sha: str
    output_path: str
    rendered_at: str
    panelforge_version: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-ready dict.

        ``notes`` becomes a list (tuples are not JSON-native); the
        round-trip via :meth:`from_dict` restores the tuple.
        """
        return {
            "figure_id": self.figure_id,
            "panel_id": self.panel_id,
            "recipe_full_name": self.recipe_full_name,
            "recipe_sha": self.recipe_sha,
            "contract_sha": self.contract_sha,
            "data_sha": self.data_sha,
            "output_sha": self.output_sha,
            "output_path": self.output_path,
            "rendered_at": self.rendered_at,
            "panelforge_version": self.panelforge_version,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CacheEntry:
        """Reconstruct from a JSON-decoded dict; defensive on missing keys.

        Unknown / missing fields default to empty strings or empty
        tuples so a forward-compatible cache write that drops a field
        doesn't crash an older reader.
        """
        return cls(
            figure_id=str(d.get("figure_id", "")),
            panel_id=str(d.get("panel_id", "")),
            recipe_full_name=str(d.get("recipe_full_name", "")),
            recipe_sha=str(d.get("recipe_sha", "")),
            contract_sha=str(d.get("contract_sha", "")),
            data_sha=str(d.get("data_sha", "")),
            output_sha=str(d.get("output_sha", "")),
            output_path=str(d.get("output_path", "")),
            rendered_at=str(d.get("rendered_at", "")),
            panelforge_version=str(d.get("panelforge_version", "")),
            notes=tuple(str(n) for n in d.get("notes", []) or []),
        )


@dataclass
class RenderCache:
    """In-memory render cache, keyed by ``panel_id``.

    Not frozen — :meth:`upsert` / :meth:`remove` mutate ``entries``.
    The dict-of-CacheEntry shape makes JSON serialisation trivial and
    avoids the linear scan that a list-of-entries layout would impose
    on the hot per-panel staleness check.
    """

    schema_version: str = CACHE_SCHEMA_VERSION
    entries: dict[str, CacheEntry] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> RenderCache:
        """Construct an empty cache pinned to the current schema."""
        return cls(schema_version=CACHE_SCHEMA_VERSION, entries={})

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-ready dict.

        The ``entries`` mapping is preserved as a dict (not a list),
        keeping panel_id → CacheEntry lookups O(1) on reload.
        """
        return {
            "schema_version": self.schema_version,
            "entries": {pid: e.to_dict() for pid, e in self.entries.items()},
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RenderCache:
        """Reconstruct from a JSON-decoded dict.

        Defensive: missing ``schema_version`` defaults to the current
        constant; entries that fail :meth:`CacheEntry.from_dict` are
        skipped silently (we'd rather drop one bad row than fail to
        load any of the others on a partial corruption).
        """
        raw_entries = d.get("entries", {}) or {}
        entries: dict[str, CacheEntry] = {}
        for pid, e in raw_entries.items():
            try:
                entries[str(pid)] = CacheEntry.from_dict(e)
            except Exception:  # noqa: BLE001 — tolerant on per-row corruption
                continue
        return cls(
            schema_version=str(d.get("schema_version", CACHE_SCHEMA_VERSION)),
            entries=entries,
        )

    def get(self, panel_id: str) -> CacheEntry | None:
        """Return the entry for ``panel_id`` or ``None`` if missing."""
        return self.entries.get(panel_id)

    def upsert(self, entry: CacheEntry) -> None:
        """Insert or replace ``entry`` keyed by its ``panel_id``."""
        self.entries[entry.panel_id] = entry

    def remove(self, panel_id: str) -> None:
        """Delete the entry for ``panel_id`` if present; no-op otherwise.

        The idempotent behaviour matches the CLI ``cache invalidate``
        command's UX, which prints a warning rather than erroring on a
        missing key.
        """
        self.entries.pop(panel_id, None)


def cache_path_for_project(project_root: Path) -> Path:
    """Default cache location: ``<project_root>/panelforge_workspace/render_cache.json``.

    Always returns a fully-resolved path — callers should not need to
    re-resolve relative inputs.
    """
    return Path(project_root) / "panelforge_workspace" / CACHE_FILENAME


# ─────────────────────────── SHA helpers ────────────────────────────────


def _sha256_file(path: Path) -> str:
    """sha256 hex digest of the bytes at ``path``.

    Streams in 64 KiB chunks so we don't peak-allocate memory for big
    parquet files.  Caller is responsible for existence — this raises
    ``FileNotFoundError`` if ``path`` is missing.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_recipe_sha(recipe_module_path: Path) -> str:
    """sha256 of the recipe ``.py`` file bytes.

    Returns an empty string when the file doesn't exist — the caller
    treats that as a "render needed" signal (the recipe might be a
    plugin loaded from somewhere other than the filesystem).
    """
    if not recipe_module_path.exists():
        return ""
    return _sha256_file(recipe_module_path)


def compute_contract_sha(contract_dict: dict[str, Any]) -> str:
    """sha256 of the canonical JSON of ``contract_dict``.

    Canonical form: keys sorted, no whitespace.  Two dicts with the
    same key/value content produce the same hash regardless of
    insertion order — important when the contract is rebuilt from a
    different Pydantic version or column order.
    """
    canonical = json.dumps(contract_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_data_sha(data_paths: list[Path]) -> str:
    """sha256 over a sorted list of ``(path, file_sha)`` pairs.

    Order-insensitive: ``[a, b]`` and ``[b, a]`` produce the same hash.
    Missing files contribute the literal sentinel ``"missing"`` rather
    than crashing — this keeps the staleness check robust when a data
    file is temporarily unavailable (the cache will simply mark the
    panel stale on the next compare).

    Empty input list produces a fixed sentinel (sha256 of the empty
    byte string) so a no-data panel still gets a stable, comparable
    hash rather than an empty string that could collide with the
    "missing" output_sha case.
    """
    if not data_paths:
        return hashlib.sha256(b"").hexdigest()
    parts: list[tuple[str, str]] = []
    for p in data_paths:
        if p.exists():
            parts.append((str(p), _sha256_file(p)))
        else:
            parts.append((str(p), "missing"))
    parts.sort()
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─────────────────────────── load / save ────────────────────────────────


def load_cache(project_root: Path) -> RenderCache:
    """Load the render cache from disk; return an empty cache on any failure.

    Failure modes — all soft (warn + empty cache):

    * File missing → silent empty cache (first run).
    * JSON decode error → ``RuntimeWarning`` + empty cache.
    * I/O error → ``RuntimeWarning`` + empty cache.
    * Schema mismatch → ``RuntimeWarning`` + empty cache.

    The "soft on corruption" behaviour matches the v1.8.0 provenance
    chain's stance: the cache is a performance optimisation, never a
    correctness gate.  A bad cache is equivalent to no cache.
    """
    path = cache_path_for_project(project_root)
    if not path.exists():
        return RenderCache.empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        warnings.warn(
            f"render_cache.json corrupt at {path}: {exc}; starting fresh",
            RuntimeWarning,
            stacklevel=2,
        )
        return RenderCache.empty()
    if data.get("schema_version") != CACHE_SCHEMA_VERSION:
        warnings.warn(
            f"render_cache schema mismatch (have {data.get('schema_version')!r}, "
            f"expect {CACHE_SCHEMA_VERSION!r}); starting fresh",
            RuntimeWarning,
            stacklevel=2,
        )
        return RenderCache.empty()
    return RenderCache.from_dict(data)


def save_cache(cache: RenderCache, project_root: Path) -> Path:
    """Atomically persist ``cache`` to ``<project_root>/panelforge_workspace/render_cache.json``.

    Writes to a temp file in the same directory, then ``os.replace`` —
    POSIX guarantees the rename is atomic, so partial writes never
    corrupt an existing cache.  The parent directory is created if
    absent.

    Returns the resolved path of the written file.  On exception, the
    temp file is removed (best-effort) before re-raising as a
    :class:`RenderCacheError`.
    """
    path = cache_path_for_project(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix="render_cache_", suffix=".json", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cache.to_dict(), f, indent=2, sort_keys=True)
        os.replace(tmp, path)
    except Exception as exc:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise RenderCacheError(f"failed to write render cache at {path}: {exc}") from exc
    return path


# ─────────────────────────── staleness ──────────────────────────────────


def check_staleness(
    cache: RenderCache,
    *,
    panel_id: str,
    current_recipe_sha: str,
    current_contract_sha: str,
    current_data_sha: str,
    output_path: Path | None = None,
) -> CacheStatus:
    """Compare current input SHAs against the cached entry.

    Order of checks (first mismatch wins):

    1. Entry not in cache → :attr:`CacheStatus.missing`.
    2. Recipe SHA differs → :attr:`CacheStatus.stale_recipe`.
    3. Contract SHA differs → :attr:`CacheStatus.stale_contract`.
    4. Data SHA differs → :attr:`CacheStatus.stale_data`.
    5. ``output_path`` was provided but the file is gone →
       :attr:`CacheStatus.stale_output`.
    6. ``output_path`` exists but its on-disk bytes no longer match the
       recorded ``output_sha`` (external edit / corruption) →
       :attr:`CacheStatus.stale_output`.
    7. All match → :attr:`CacheStatus.fresh`.

    The order is chosen so the most "user-explainable" cause wins: a
    recipe edit is more notable than a downstream data refresh, and
    both win over a vanished or tampered output file.

    Check 6 closes the "cache blind to mutation" gap: detecting only
    deletion (check 5) let an externally-edited or corrupted output
    file masquerade as fresh, silently surviving the re-render gate.
    The on-disk SHA is recomputed with :func:`_sha256_file` — the same
    helper :func:`update_cache_entry` uses to populate ``output_sha`` —
    so the two hashes are directly comparable.  The comparison is
    skipped when the recorded ``output_sha`` is empty (the documented
    "output missing at update time" defensive case), since there is no
    baseline to compare against.
    """
    entry = cache.get(panel_id)
    if entry is None:
        return CacheStatus.missing
    if entry.recipe_sha != current_recipe_sha:
        return CacheStatus.stale_recipe
    if entry.contract_sha != current_contract_sha:
        return CacheStatus.stale_contract
    if entry.data_sha != current_data_sha:
        return CacheStatus.stale_data
    if output_path is not None:
        if not output_path.exists():
            return CacheStatus.stale_output
        if entry.output_sha and _sha256_file(output_path) != entry.output_sha:
            return CacheStatus.stale_output
    return CacheStatus.fresh


def update_cache_entry(
    cache: RenderCache,
    *,
    panel_id: str,
    figure_id: str,
    recipe_full_name: str,
    recipe_sha: str,
    contract_sha: str,
    data_sha: str,
    output_path: Path,
    panelforge_version: str,
    notes: tuple[str, ...] = (),
) -> CacheEntry:
    """Build a :class:`CacheEntry` from current state and upsert it.

    ``output_sha`` is computed only when ``output_path`` exists; a
    missing output file yields an empty string (defensive — happens
    when the renderer claimed success but the file was moved or the
    test is constructing a synthetic cache).

    Returns the newly-stored entry so callers can inspect it.
    """
    output_sha = _sha256_file(output_path) if output_path.exists() else ""
    rendered_at = (
        datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )
    entry = CacheEntry(
        figure_id=figure_id,
        panel_id=panel_id,
        recipe_full_name=recipe_full_name,
        recipe_sha=recipe_sha,
        contract_sha=contract_sha,
        data_sha=data_sha,
        output_sha=output_sha,
        output_path=str(output_path),
        rendered_at=rendered_at,
        panelforge_version=panelforge_version,
        notes=tuple(notes),
    )
    cache.upsert(entry)
    return entry


def summarize_cache_state(
    cache: RenderCache,
    panel_states: dict[str, CacheStatus],
) -> dict[str, int]:
    """Aggregate per-panel staleness verdicts into counters.

    Returns a dict with one key per :class:`CacheStatus` value plus
    two sentinels — ``"total"`` (number of panels reported) and
    ``"cache_entries"`` (number of rows currently in the cache).  The
    CLI ``cache status`` and ``execute-plan`` summary pretty-print this.
    """
    summary = {
        "fresh": 0,
        "missing": 0,
        "stale_data": 0,
        "stale_recipe": 0,
        "stale_contract": 0,
        "stale_output": 0,
        "unknown": 0,
    }
    for status in panel_states.values():
        summary[status.value] = summary.get(status.value, 0) + 1
    summary["total"] = len(panel_states)
    summary["cache_entries"] = len(cache.entries)
    return summary
