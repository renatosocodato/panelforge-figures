# Themes

A theme is a function that returns a dict of matplotlib rcParams layered on
top of the base style (which comes from `core/style.py`). The base style
already enforces the Helvetica stack, pdf.fonttype 42, 600-dpi savefig, etc.
Themes only tune per-venue preferences (label sizes, line widths, title
weight).

| Theme | Use for |
|---|---|
| `default` | Neutral, no overrides |
| `nature` | Nature family (slightly tighter labels) |
| `cell` | Cell, Cell Reports, Dev Cell (larger labels) |
| `pnas` | PNAS (bold titles, compact) |
| `devcell` | Dev Cell (warm Cell variant) |
| `bpj` | Biophysical Journal (thinner lines, compact) |
| `neuron` | Neuron (heavier axes) |
| `ncb` | Nature Cell Biology |
| `sttt` | Signal Transduction and Targeted Therapy (punchy) |
| `trends` | Trends journals (review-friendly, thicker lines) |
| `fct_grant` | FCT grant (dense, compact) |
| `horizon` | Horizon Europe (dense + thicker axes) |

## Applying a theme

### From a manifest

```yaml
theme: pnas
```

Every figure in the manifest inherits the theme; an individual figure can
override it (not yet exposed, landing in a later commit).

### From Python

```python
from panelforge_figures.themes import apply_theme
apply_theme("pnas")
```

`apply_theme(name)` first calls `apply_base_style()` then layers the theme's
rcParams on top. The theme name is recorded via `current_theme()`.

## Writing a new theme

Add a module under `src/panelforge_figures/themes/<name>.py`:

```python
from . import register_theme

def _overrides() -> dict:
    return {
        "axes.labelsize": 9.2,
        "lines.linewidth": 1.4,
    }

register_theme("<name>", _overrides)
```

The theme package auto-loads every non-underscored submodule at import time,
so simply committing the file registers it. It will appear in
`figures list-themes` and in the catalog.
