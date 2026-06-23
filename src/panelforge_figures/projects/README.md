# `panelforge_figures.projects` — register a project

The `projects/` package is a small **cross-project orchestration registry**: a
per-user YAML file (default `~/.config/panelforge/projects.yaml`, honouring
`$XDG_CONFIG_HOME`) that records every panelforge project you have touched, so
the CLI can list them and switch a default between repos.

Full design: [`docs/spec_cross_project.md`](../../../docs/spec_cross_project.md).

> **It stores paths, not data.** Every `path` is absolute and
> `realpath`-resolved. Switching projects only re-reads the local workspace;
> nothing is implicitly copied. A corrupted YAML file falls back to an empty
> registry, emits a `RuntimeWarning`, renames the broken file to
> `projects.yaml.broken-<ts>`, and never raises to the caller.

---

## Register a project

```python
from pathlib import Path
from panelforge_figures.projects import register_if_absent

entry = register_if_absent(
    Path("/work/microglia-paper"),   # must be a live directory
    project_id="microglia-paper",
    profile="intravital_imaging",
    n_recipes=12,
    status="rendered",
    tags=("intravital", "calcium"),
    set_default=True,
)
print(entry.id, entry.path, entry.active_profile)
```

`register_if_absent` adds the project or **refreshes** an existing one. On
re-registration only `last_used`, `active_profile`, `n_recipes_picked`, and
`last_render_status` change; `path` and `tags` are user-managed and preserved. It
raises `ProjectIdCollision` if the same id maps to a different path, and
`ProjectPathMissing` if the path is not a live directory.

## Read, switch, and list

```python
from panelforge_figures.projects import load_registry, switch_default

reg = load_registry()                 # Registry view of projects.yaml
print(reg.default_project)
for pid, e in reg.projects.items():
    print(pid, e.last_render_status, e.last_used)

switch_default("microglia-paper")     # persists the new default
```

Other helpers: `save_registry`, `unregister`, `validate_registry` (drops registry
rows whose paths no longer exist — never touches the filesystem),
`default_registry_path`, and the value types `Registry` / `ProjectEntry`.

## Public API

`register_if_absent`, `load_registry`, `save_registry`, `switch_default`,
`unregister`, `validate_registry`, `default_registry_path`, `Registry`,
`ProjectEntry`, `ProjectIdCollision`, `ProjectPathMissing`,
`DEFAULT_REGISTRY_PATH` — see `__all__` in [`__init__.py`](./__init__.py).
