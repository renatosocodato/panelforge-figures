"""Project plugin discovery + loading (Sprint 2A — v1.10.0).

Plugins extend the recipe catalog with project-local recipes,
without forking. Two paths:

1. **Installable plugins** (preferred for groups): packages declaring
   an ``entry_points`` group ``"panelforge.plugins"`` in their pyproject.
   Discovered via :func:`importlib.metadata.entry_points`.

2. **Single-file plugins** (preferred for solo researchers): a
   ``panelforge_plugins/`` directory at the project root, walked at
   import time.

Plugin recipes use the same :func:`register_recipe` decorator as catalog
recipes; conflicts (duplicate ``{modality}.{name}``) raise
:class:`PluginConflictError` at discovery time (the underlying
``register_recipe`` raises ``ValueError``; this module re-raises with the
plugin attribution attached).

Discovery is **not** automatic at package import; callers must invoke
:func:`discover_all_plugins` (the catalog index builder + the
``figures plugins`` CLI both do this lazily).  Keeping it explicit means
``pytest`` runs that don't touch this module see deterministic behaviour
and the global registry stays catalog-only.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

PLUGINS_ENTRY_POINT_GROUP = "panelforge.plugins"
DEFAULT_PLUGINS_DIR = "panelforge_plugins"


class PluginConflictError(RuntimeError):
    """Raised when two plugins (or plugin + catalog) register the same recipe."""


class PluginLoadError(RuntimeError):
    """Raised when a plugin fails to load (import error, malformed metadata)."""


@dataclass(frozen=True)
class PluginInfo:
    """Metadata about a successfully loaded plugin."""

    name: str
    version: str = "unknown"
    source: str = "unknown"  # "entry_points" | "directory"
    module_path: Path | None = None
    discovered_recipes: tuple[str, ...] = field(default_factory=tuple)


# Process-wide cache of loaded plugins, keyed by plugin name.  Cleared by
# `reset_plugin_state` (test helper).  Never read directly by callers
# outside this module — use `list_loaded_plugins` instead.
_LOADED_PLUGINS: dict[str, PluginInfo] = {}


def _registry_full_names() -> set[str]:
    """Snapshot the current ``{modality}.{name}`` set in the registry.

    Imported lazily to avoid a circular import at module-load time.
    """
    from ..core.contract import list_recipes

    return {f"{e.metadata.modality}.{e.metadata.name}" for e in list_recipes()}


def _attribute_recipes(
    name: str,
    version: str,
    source: str,
    module_path: Path | None,
    before: set[str],
) -> PluginInfo:
    """Compute discovered_recipes by diffing the registry pre/post-import.

    Recipes registered between ``before`` and now are credited to the
    plugin.  A recipe registered by the plugin under a name that already
    existed would have raised ``ValueError`` from ``register_recipe`` —
    this function is only reached on a clean import.
    """
    after = _registry_full_names()
    new_recipes = tuple(sorted(after - before))
    info = PluginInfo(
        name=name,
        version=version,
        source=source,
        module_path=module_path,
        discovered_recipes=new_recipes,
    )
    _LOADED_PLUGINS[name] = info
    return info


def discover_entry_point_plugins(
    *,
    disabled: tuple[str, ...] = (),
) -> list[PluginInfo]:
    """Walk ``entry_points`` for the ``panelforge.plugins`` group.

    Returns the list of :class:`PluginInfo` for every entry-point that
    successfully loaded.  Side effect: populates ``_LOADED_PLUGINS``.

    Already-loaded plugin names are skipped (idempotent).  Names in
    ``disabled`` are silently skipped.  Duplicate-recipe conflicts raise
    :class:`PluginConflictError` rather than being swallowed.
    """
    loaded: list[PluginInfo] = []
    try:
        eps = importlib.metadata.entry_points(group=PLUGINS_ENTRY_POINT_GROUP)
    except Exception as e:  # noqa: BLE001 — defensive against pkg metadata bugs
        log.warning("entry_points discovery failed: %s", e)
        return []

    for ep in eps:
        if ep.name in disabled:
            log.debug("plugin %r disabled; skipping", ep.name)
            continue
        if ep.name in _LOADED_PLUGINS:
            loaded.append(_LOADED_PLUGINS[ep.name])
            continue

        before = _registry_full_names()
        try:
            module = ep.load()
        except ValueError as e:
            # `register_recipe` raises ValueError on duplicate full_name;
            # the plugin attribution is still useful so re-raise as conflict.
            raise PluginConflictError(
                f"plugin {ep.name!r} duplicates an existing recipe registration: {e}"
            ) from e
        except Exception as e:  # noqa: BLE001 — wrap any import error
            raise PluginLoadError(
                f"plugin {ep.name!r} failed to load: {e}"
            ) from e

        info = _attribute_recipes(
            name=ep.name,
            version=getattr(module, "__version__", "unknown"),
            source="entry_points",
            module_path=Path(getattr(module, "__file__", "") or "") or None,
            before=before,
        )
        loaded.append(info)
    return loaded


def discover_directory_plugins(
    plugins_dir: Path | None = None,
    *,
    disabled: tuple[str, ...] = (),
) -> list[PluginInfo]:
    """Walk a ``panelforge_plugins/`` directory for single-file plugins.

    Each ``.py`` file in the directory (excluding files starting with
    ``_`` or ``.``) is imported as a module under the
    ``panelforge_user_plugins`` namespace.  Subdirectories with
    ``__init__.py`` are also imported.

    The plugin name is the file stem (or directory name).  Names in
    ``disabled`` are silently skipped.  Duplicate-recipe conflicts raise
    :class:`PluginConflictError`.
    """
    if plugins_dir is None:
        plugins_dir = Path(DEFAULT_PLUGINS_DIR)
    if not plugins_dir.is_dir():
        return []

    loaded: list[PluginInfo] = []
    for path in sorted(plugins_dir.iterdir()):
        if path.name.startswith("_") or path.name.startswith("."):
            continue

        if path.is_file() and path.suffix == ".py":
            plugin_name = path.stem
            init_path: Path = path
        elif path.is_dir() and (path / "__init__.py").is_file():
            plugin_name = path.name
            init_path = path / "__init__.py"
        else:
            continue

        if plugin_name in disabled:
            log.debug("plugin %r disabled; skipping", plugin_name)
            continue
        if plugin_name in _LOADED_PLUGINS:
            loaded.append(_LOADED_PLUGINS[plugin_name])
            continue

        module_qual = f"panelforge_user_plugins.{plugin_name}"
        before = _registry_full_names()
        try:
            spec = importlib.util.spec_from_file_location(
                module_qual, init_path,
            )
            if spec is None or spec.loader is None:
                raise PluginLoadError(
                    f"plugin {plugin_name!r}: spec could not be created"
                )
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_qual] = module
            spec.loader.exec_module(module)
        except ValueError as e:
            sys.modules.pop(module_qual, None)
            raise PluginConflictError(
                f"plugin {plugin_name!r} duplicates an existing recipe registration: {e}"
            ) from e
        except PluginLoadError:
            raise
        except Exception as e:  # noqa: BLE001 — wrap any import error
            sys.modules.pop(module_qual, None)
            raise PluginLoadError(
                f"plugin {plugin_name!r} failed to load: {e}"
            ) from e

        info = _attribute_recipes(
            name=plugin_name,
            version=getattr(module, "__version__", "unknown"),
            source="directory",
            module_path=init_path,
            before=before,
        )
        loaded.append(info)
    return loaded


def discover_all_plugins(
    *,
    plugins_dir: Path | None = None,
    disabled: tuple[str, ...] = (),
) -> list[PluginInfo]:
    """Combined discovery: entry-points + directory.

    Skips plugin names in ``disabled``.  Idempotent — already-loaded
    plugins aren't re-imported.  Returns the merged loaded list (after
    filtering ``disabled``).
    """
    if plugins_dir is None:
        plugins_dir = Path(DEFAULT_PLUGINS_DIR)

    discover_entry_point_plugins(disabled=disabled)
    discover_directory_plugins(plugins_dir, disabled=disabled)

    return [
        info
        for name, info in _LOADED_PLUGINS.items()
        if name not in disabled
    ]


def list_loaded_plugins() -> list[PluginInfo]:
    """Return all successfully loaded plugins (in insertion order)."""
    return list(_LOADED_PLUGINS.values())


def get_plugin(name: str) -> PluginInfo | None:
    """Look up a loaded plugin by name."""
    return _LOADED_PLUGINS.get(name)


def reset_plugin_state() -> None:
    """Clear the loaded-plugin cache (test helper).

    Note: this does **not** unregister recipes from the global registry.
    Callers needing a clean recipe registry must reset it themselves
    (typically via fixture-level isolation in tests).
    """
    _LOADED_PLUGINS.clear()


def plugin_for_recipe(full_name: str) -> str | None:
    """Return the plugin name owning ``full_name``, or ``None`` for catalog.

    Used by `manifest/catalog.py` to set ``tags_source: plugin:<name>``.
    """
    for info in _LOADED_PLUGINS.values():
        if full_name in info.discovered_recipes:
            return info.name
    return None
