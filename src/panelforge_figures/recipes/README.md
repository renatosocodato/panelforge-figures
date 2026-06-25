# `panelforge_figures.recipes` — package map

`recipes/` is the **catalog**: every figure panelforge can draw lives here as a
contract-bound recipe. The package is one Python module per recipe, grouped into
**modality subpackages** (one directory each). At the time of writing it holds
**471 recipes across 20 modalities**.

`recipes/` depends inward on `core/` only (it imports `register_recipe`,
`register_modality`, the contract/metadata bases, and the palette/style
primitives). Everything downstream — `manifest/`, `cli/`, `mcp/` — depends on
`recipes/` *indirectly*, by reading the registry `core` populates when these
modules import.

For the design rationale and trade-offs, read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §3.1.

---

## How a modality is wired

Importing `recipes/` does **not** import any modality (see `__init__.py`). The
registry is populated lazily: `core.contract.ensure_all_imported()`
`pkgutil`-walks this package, which runs each modality's `__init__.py`, which in
turn registers the modality and imports each recipe module so its
`@register_recipe` decorator fires.

```
recipes/<modality>/__init__.py
    │  register_modality(name, description, aesthetic=AESTHETIC)
    │  from . import (recipe_a, recipe_b, …)   # import side-effect = registration
    ▼
recipes/<modality>/_aesthetic.py   ── module-level AESTHETIC (a ModalityAesthetic)
recipes/<modality>/<recipe>.py     ── @register_recipe(metadata=…, contract=…, demo_contract=_demo)
                                        def render(contract, ax=None, **_): …
```

A recipe omitted from the `from . import (...)` block in its modality
`__init__.py` is **silently absent** from the catalog — no error is raised. Keep
that import list and the modality `__all__` exhaustive.

---

## Anatomy of a modality subpackage

Each modality directory contains:

| File | Role |
|---|---|
| `__init__.py` | Calls `register_modality(...)` then imports every recipe module. |
| `_aesthetic.py` | Defines the module-level `AESTHETIC` (`ModalityAesthetic`) so the whole modality renders as one visual family. |
| `<recipe>.py` | One recipe: a `RecipeContract` subclass, a `RecipeMetadata`, a `_demo()` zero-external-data contract, and a `render(contract, ax=None, **_)` function decorated with `@register_recipe`. |

The 20 modalities span imaging, signaling, statistics, and conceptual figures —
e.g. `actin_microtubule_morphometry`, `calcium_signaling`, `intravital_imaging`,
`fret_biosensors`, `redox_imaging`, `omics_differential`, `mixed_effects_models`,
`meta_and_diagnostic`, `clinical_cohort`, `grant_and_conceptual`. Run
`figures catalog` for the authoritative, live list.

---

## Vocabulary

- **Modality** — a thematic family of recipes sharing one `ModalityAesthetic`.
  The `{modality}.{name}` pair is a recipe's `full_name` (its registry key).
- **`_demo()` / demo contract** — every recipe ships a runnable, zero-external-data
  contract instance so it works in smoke tests and the MCP server with no user
  data.
- **Family** — a recipe's `RecipeFamily` (a closed enum in `core.contract`),
  orthogonal to modality and used by the geometry quality gates.

Do **not** run `figures index emit` to regenerate `recipes_index.json` by hand —
it is a checked-in build artifact derived from this catalog.
