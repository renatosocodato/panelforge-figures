"""Cross-project orchestration registry — Sprint 3A (v2.0.0).

See ``docs/spec_cross_project.md`` for the full design. The registry is a
per-user YAML file at ``~/.config/panelforge/projects.yaml`` (honouring
``$XDG_CONFIG_HOME``) that records every panelforge project the user has
touched. It stores **paths, not data**: switching projects only re-reads
the local ``panelforge_workspace/``; nothing is implicitly copied.

Privacy invariants (spec §7, §11):

1. All ``path`` values are stored absolute, ``realpath``-resolved.
2. :func:`validate_registry` does NOT delete filesystem; only registry rows.
3. :func:`register_if_absent` confines I/O to existing directories.
4. Corrupted YAML falls back to an empty registry, emits a
   ``RuntimeWarning`` and renames the broken file to
   ``projects.yaml.broken-<ts>``; it never raises to the caller.
"""

from __future__ import annotations

import os
import sys
import warnings
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

DEFAULT_REGISTRY_FILENAME = "projects.yaml"


class ProjectIdCollision(ValueError):
    """Same ID reused for a different path (spec §11)."""


class ProjectPathMissing(FileNotFoundError):
    """Registered path no longer exists when a live path was required."""


@dataclass(frozen=True)
class ProjectEntry:
    """One registered project: pointer + cached summary metadata.

    ``path`` is absolute and ``realpath``-resolved; ``last_used`` is a
    tz-aware UTC ``datetime`` and round-trips as ISO 8601 with a ``Z``.
    """

    id: str
    path: Path
    last_used: datetime
    active_profile: str
    n_recipes_picked: int
    last_render_status: str
    tags: tuple[str, ...] = ()


@dataclass
class Registry:
    """In-memory view of ``projects.yaml``."""

    schema_version: int = 1
    default_project: str | None = None
    projects: dict[str, ProjectEntry] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> Registry:
        """Fresh empty registry with ``schema_version = 1``."""
        return cls(schema_version=1, default_project=None, projects={})

    def add(self, entry: ProjectEntry, *, set_default: bool = False) -> None:
        """Insert (or replace) ``entry``; promote to default if asked or empty."""
        self.projects[entry.id] = entry
        if set_default or self.default_project is None:
            self.default_project = entry.id

    def get(self, project_id: str) -> ProjectEntry:
        """Lookup ``project_id`` or raise :class:`KeyError`."""
        if project_id not in self.projects:
            raise KeyError(f"project_id not registered: {project_id!r}")
        return self.projects[project_id]

    def remove(self, project_id: str, *, missing_ok: bool = False) -> None:
        """Drop ``project_id``; rotate default to next-most-recent if needed."""
        if project_id not in self.projects:
            if missing_ok:
                return
            raise KeyError(f"project_id not registered: {project_id!r}")
        del self.projects[project_id]
        if self.default_project == project_id:
            self.default_project = _next_default(self.projects)


def _next_default(projects: dict[str, ProjectEntry]) -> str | None:
    """Most-recently-used id, or None if empty."""
    if not projects:
        return None
    return max(projects.values(), key=lambda e: e.last_used).id


def default_registry_path() -> Path:
    """``$XDG_CONFIG_HOME/panelforge/projects.yaml`` else ``~/.config/...``."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path(os.path.expanduser("~")) / ".config"
    return base / "panelforge" / DEFAULT_REGISTRY_FILENAME


#: Evaluated-at-import default; use :func:`default_registry_path` for
#: env-sensitive lookups (e.g. tests that monkeypatch ``$XDG_CONFIG_HOME``).
DEFAULT_REGISTRY_PATH: Path = default_registry_path()


def _serialize_entry(entry: ProjectEntry) -> dict[str, Any]:
    """``ProjectEntry`` -> YAML-friendly dict; ``last_used`` becomes ISO-Z UTC."""
    last_used = entry.last_used
    if last_used.tzinfo is None:
        last_used = last_used.replace(tzinfo=UTC)
    else:
        last_used = last_used.astimezone(UTC)
    return {
        "path": str(entry.path),
        "last_used": last_used.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "active_profile": entry.active_profile,
        "n_recipes_picked": int(entry.n_recipes_picked),
        "last_render_status": entry.last_render_status,
        "tags": list(entry.tags),
    }


def _deserialize_entry(project_id: str, raw: dict[str, Any]) -> ProjectEntry:
    """YAML dict -> ``ProjectEntry``; tolerates missing optional fields."""
    last_raw = raw.get("last_used")
    if isinstance(last_raw, datetime):
        last_used = last_raw if last_raw.tzinfo else last_raw.replace(tzinfo=UTC)
    elif isinstance(last_raw, str):
        last_used = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=UTC)
    else:
        last_used = datetime.now(UTC)
    return ProjectEntry(
        id=project_id,
        path=Path(str(raw.get("path", ""))),
        last_used=last_used,
        active_profile=str(raw.get("active_profile", "")),
        n_recipes_picked=int(raw.get("n_recipes_picked", 0) or 0),
        last_render_status=str(raw.get("last_render_status", "n/a")),
        tags=tuple(str(t) for t in (raw.get("tags") or ())),
    )


def _resolve_config_path(config_path: Path | None) -> Path:
    """User-supplied or current XDG default (re-evaluated each call)."""
    return Path(config_path) if config_path is not None else default_registry_path()


def _backup_corrupted(config_path: Path) -> Path:
    """Rename to ``projects.yaml.broken-<ts>`` (best-effort)."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    broken = config_path.with_name(config_path.name + f".broken-{ts}")
    try:
        config_path.rename(broken)
    except OSError:
        pass
    return broken


def _warn_corrupted(path: Path, broken: Path, reason: str) -> None:
    """Single-source warning for the three corruption branches."""
    warnings.warn(
        f"corrupted registry at {path}: {reason}; backed up to {broken}; "
        "starting from empty registry",
        RuntimeWarning,
        stacklevel=3,
    )


def load_registry(config_path: Path | None = None) -> Registry:
    """Load the registry; corruption falls back to empty + warning + backup.

    Never raises (spec §7): on parse error or schema mismatch the file is
    renamed to ``projects.yaml.broken-<ts>``, a :class:`RuntimeWarning` is
    emitted, and an empty registry is returned.
    """
    path = _resolve_config_path(config_path)
    if not path.exists():
        return Registry.empty()
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except (yaml.YAMLError, OSError) as exc:
        _warn_corrupted(path, _backup_corrupted(path), str(exc))
        return Registry.empty()
    if not isinstance(raw, dict):
        _warn_corrupted(path, _backup_corrupted(path), "top-level is not a mapping")
        return Registry.empty()
    projects_raw = raw.get("projects") or {}
    if not isinstance(projects_raw, dict):
        _warn_corrupted(path, _backup_corrupted(path), "'projects' is not a mapping")
        return Registry.empty()
    projects: dict[str, ProjectEntry] = {}
    for pid, body in projects_raw.items():
        if not isinstance(body, dict):
            continue
        try:
            projects[str(pid)] = _deserialize_entry(str(pid), body)
        except (TypeError, ValueError):
            continue
    default_project = raw.get("default_project")
    return Registry(
        schema_version=int(raw.get("schema_version", 1) or 1),
        default_project=str(default_project) if default_project else None,
        projects=projects,
    )


def save_registry(registry: Registry, config_path: Path | None = None) -> None:
    """Persist ``registry``; takes ``fcntl.flock`` on POSIX (no-op elsewhere)."""
    path = _resolve_config_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": int(registry.schema_version),
        "default_project": registry.default_project,
        "projects": {
            pid: _serialize_entry(e) for pid, e in registry.projects.items()
        },
    }
    serialised = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)
    with path.open("w", encoding="utf-8") as fh:
        if sys.platform != "win32":
            try:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass
        fh.write(serialised)


def _resolve_project_path(path: Path) -> Path:
    """Resolve to an absolute existing directory, else raise."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ProjectPathMissing(
            f"project path is not an existing directory: {resolved}"
        )
    return resolved


def register_if_absent(
    path: Path,
    project_id: str,
    profile: str,
    *,
    n_recipes: int = 0,
    status: str = "n/a",
    tags: Iterable[str] = (),
    config_path: Path | None = None,
    set_default: bool = False,
) -> ProjectEntry:
    """Add or refresh a project entry.

    On re-registration only ``last_used``, ``active_profile``,
    ``n_recipes_picked`` and ``last_render_status`` are refreshed (spec
    §6); ``path`` and ``tags`` are user-managed and preserved. Raises
    :class:`ProjectIdCollision` if the same id maps to a different path
    and :class:`ProjectPathMissing` if ``path`` is not a live directory.
    """
    resolved = _resolve_project_path(path)
    registry = load_registry(config_path)
    now = datetime.now(UTC)
    existing = registry.projects.get(project_id)
    if existing is not None and existing.path != resolved:
        raise ProjectIdCollision(
            f"project_id {project_id!r} already registered at "
            f"{existing.path}; refusing to re-bind to {resolved}. "
            "Set a unique project_id in panelforge.project.yaml or "
            "pass --id <new>."
        )
    entry = ProjectEntry(
        id=project_id,
        path=resolved,
        last_used=now,
        active_profile=profile,
        n_recipes_picked=int(n_recipes),
        last_render_status=status,
        tags=existing.tags if existing is not None else tuple(str(t) for t in tags),
    )
    registry.add(entry, set_default=set_default)
    save_registry(registry, config_path)
    return entry


def switch_default(
    project_id: str, *, config_path: Path | None = None
) -> ProjectEntry:
    """Set ``default_project`` to ``project_id`` and persist.

    Raises :class:`KeyError` if not registered, or
    :class:`ProjectPathMissing` if its path no longer exists on disk.
    """
    registry = load_registry(config_path)
    entry = registry.get(project_id)
    if not entry.path.is_dir():
        raise ProjectPathMissing(
            f"project {project_id!r} path no longer exists: {entry.path}; "
            "run `figures projects validate` to clean stale entries."
        )
    refreshed = ProjectEntry(
        id=entry.id,
        path=entry.path,
        last_used=datetime.now(UTC),
        active_profile=entry.active_profile,
        n_recipes_picked=entry.n_recipes_picked,
        last_render_status=entry.last_render_status,
        tags=entry.tags,
    )
    registry.projects[project_id] = refreshed
    registry.default_project = project_id
    save_registry(registry, config_path)
    return refreshed


def unregister(
    project_id: str,
    *,
    missing_ok: bool = False,
    config_path: Path | None = None,
) -> None:
    """Remove ``project_id`` from the registry; never touches filesystem."""
    registry = load_registry(config_path)
    registry.remove(project_id, missing_ok=missing_ok)
    save_registry(registry, config_path)


def validate_registry(
    *,
    prompt: bool = True,
    config_path: Path | None = None,
) -> list[str]:
    """Drop entries whose ``path`` no longer exists; return their IDs.

    Filesystem is never touched (spec §11). When ``prompt`` is true but
    stdin is not a TTY, emit a :class:`RuntimeWarning` per drop instead
    of blocking on interactive input (so CI does not stall).
    """
    registry = load_registry(config_path)
    stale: list[str] = [
        pid for pid, e in registry.projects.items() if not e.path.is_dir()
    ]
    if not stale:
        return []
    if not (prompt and sys.stdin.isatty()):
        for pid in stale:
            warnings.warn(
                f"dropping stale registry entry {pid!r} "
                f"(path missing: {registry.projects[pid].path})",
                RuntimeWarning,
                stacklevel=2,
            )
    for pid in stale:
        registry.remove(pid, missing_ok=True)
    save_registry(registry, config_path)
    return stale


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "ProjectEntry",
    "ProjectIdCollision",
    "ProjectPathMissing",
    "Registry",
    "default_registry_path",
    "load_registry",
    "register_if_absent",
    "save_registry",
    "switch_default",
    "unregister",
    "validate_registry",
]
