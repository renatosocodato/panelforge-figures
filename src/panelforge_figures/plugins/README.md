# `panelforge_figures.plugins` — write your first plugin

Plugins let a local repo or an installable package add its own recipes to the
panelforge catalog **without forking**. A plugin is just a Python module that
calls the same `@register_recipe(...)` decorator the built-in catalog uses,
against the same process-global registry.

Full design: [`docs/spec_project_plugins.md`](../../../docs/spec_project_plugins.md).

> **Trust boundary.** Loading a plugin executes arbitrary Python at import time.
> Directory plugins are `exec`-ed with no sandbox. Only point panelforge at
> plugin packages and directories you trust. Discovery is always **opt-in** —
> nothing is imported until a caller invokes a `discover_*` function.

---

## Minimal single-file plugin

Drop a `*.py` file into a `panelforge_plugins/` directory at your project root:

```
my-project/
├── panelforge.project.yaml
└── panelforge_plugins/
    └── my_kymograph.py
```

```python
# panelforge_plugins/my_kymograph.py
from panelforge_figures.core import (
    RecipeContract, RecipeFamily, RecipeMetadata, register_recipe,
)


class MyKymographInput(RecipeContract):
    line_scan: list[list[float]]
    title: str = "Example line-scan"


_META = RecipeMetadata(
    name="example_line_scan_kymograph",
    modality="example_extras",              # plugin-namespaced modality
    family=RecipeFamily.heatmap,
    answers_question="What is the spatiotemporal evolution of the line-scan?",
    required_fields=("line_scan",),
)


def _demo() -> MyKymographInput:
    return MyKymographInput(line_scan=[[0.0, 1.0], [1.0, 0.0]])


@register_recipe(metadata=_META, contract=MyKymographInput, demo_contract=_demo)
def render(contract: MyKymographInput, ax=None, **_):
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots()
    ax.imshow(contract.line_scan, aspect="auto")
    ax.set_title(contract.title)
    return ax
```

A plugin recipe is "the same shape as a catalog recipe, but it lives in your
tree": the four artifacts (`RecipeContract` subclass, `_demo`, `_META`,
`@register_recipe`-decorated `render`) are identical to the built-ins.

## Loading plugins

Discovery is never automatic. Invoke it explicitly:

```python
from panelforge_figures.plugins import discover_all_plugins
from pathlib import Path

infos = discover_all_plugins(plugins_dir=Path("panelforge_plugins"))
for info in infos:
    print(info.name, info.discovered_recipes)
```

`discover_all_plugins` combines two paths:

- **`discover_entry_point_plugins()`** — installable packages declaring the
  `panelforge.plugins` entry-point group (`PLUGINS_ENTRY_POINT_GROUP`). Preferred
  for sharing across a group; survives `pip install -e`.
- **`discover_directory_plugins(plugins_dir)`** — single-file plugins in a
  `panelforge_plugins/` directory (`DEFAULT_PLUGINS_DIR`). Preferred for solo
  researchers.

Both are **idempotent** and end at the same `register_recipe(...)` call. A
duplicate `{modality}.{name}` raises `PluginConflictError`; an import failure
raises `PluginLoadError`. Attribution (`PluginInfo.discovered_recipes`) is
computed by diffing the registry full-name set before/after import.

## Public API

`discover_all_plugins`, `discover_entry_point_plugins`,
`discover_directory_plugins`, `list_loaded_plugins`, `get_plugin`,
`plugin_for_recipe`, `reset_plugin_state`, `PluginInfo`, `PluginConflictError`,
`PluginLoadError`, `PLUGINS_ENTRY_POINT_GROUP`, `DEFAULT_PLUGINS_DIR` — see
`__all__` in [`__init__.py`](./__init__.py).
