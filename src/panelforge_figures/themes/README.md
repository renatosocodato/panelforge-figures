# `panelforge_figures.themes` — package map

`themes/` is a **self-autoloading registry of per-venue rcParams overlays**. A
theme is a small set of matplotlib `rcParams` overrides (label/title/tick sizes,
weights, etc.) layered *on top of* the base publication style in
`core.style.apply_base_style`. Themes never replace the base style — they nudge it
to match a target journal's typographic conventions.

For where this fits, read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §3.10.

---

## The registry (`__init__.py`)

The package keeps a module-level `_REGISTRY: dict[str, Callable[[], dict]]`. On
import, `_autoload_themes()` `pkgutil`-walks this package and imports every
non-underscore module, each of which registers itself at import time. Public API:

- `register_theme(name, overrides)` — register a zero-arg callable returning an
  rcParams dict. Called by each theme module at import.
- `get_theme(name)` — return the resolved overrides dict (raises `KeyError`
  listing known names if absent).
- `list_themes()` — sorted list of registered names.
- `apply_theme(name)` — fetch the overrides and call
  `core.style.apply_base_style(theme=name, overrides=...)`.

A new theme is a **one-file drop-in**: add `themes/<name>.py` that defines a
zero-arg `_overrides()` returning an rcParams dict and calls
`register_theme("<name>", _overrides)`. Autoload picks it up — no central edit
needed.

---

## Shipped themes

| Module | Theme name | Target / intent |
|---|---|---|
| `default.py` | `default` | Base style, no overrides. |
| `nature.py` | `nature` | Nature family (Nature, Nat Methods, Nat Cell Biol) — tight sans. |
| `cell.py` | `cell` | Cell Press family. |
| `devcell.py` | `devcell` | Developmental Cell. |
| `ncb.py` | `ncb` | Nature Cell Biology. |
| `neuron.py` | `neuron` | Neuron. |
| `pnas.py` | `pnas` | PNAS. |
| `trends.py` | `trends` | Trends journals. |
| `sttt.py` | `sttt` | Signal Transduction and Targeted Therapy. |
| `bpj.py` | `bpj` | Biophysical Journal. |
| `horizon.py` | `horizon` | Horizon / generic wide-format overlay. |
| `fct_grant.py` | `fct_grant` | FCT grant figures. |

Run `figures catalog` (the `themes:` line) for the authoritative, live list.

---

## How it fits the architecture

`themes/` is a **surface** layered on `core.style`; it has no knowledge of
recipes, manifests, or modalities. A manifest selects a theme by name, the render
pipeline calls `apply_theme(...)` before drawing, and the base style plus the
overlay together fix the rcParams for that figure.

**Caveat (inherited from `core.style`):** `apply_base_style` mutates the global
`matplotlib.rcParams`, so applying a theme is process-global and not thread-safe.

Themes are the *extensible* member of the surface layer: contrast with
`transforms/`, which is a closed fixed set rather than an autoloading registry.
