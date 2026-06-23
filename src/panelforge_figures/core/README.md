# `panelforge_figures.core` — package map

`core/` is the **leaf foundation** of panelforge-figures. It imports no sibling
subsystem at module scope (its only inward dependency is a *lazy* import of
`recipes` inside `ensure_all_imported`). Everything else — `recipes/`,
`manifest/`, `cli/`, `mcp/` — depends inward on `core`.

For the full design rationale and the honest trade-offs, read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §2.

---

## The registry lifecycle (`contract.py`)

The single most important design decision in the project: the recipe registry is
a **process-global, mutable, module-level dict** (`_REGISTRY`) populated by an
`@register_recipe` decorator at import time. That registry — not any external
manifest file — is the ground truth for the entire catalog.

```
@register_recipe(metadata=_META, contract=MyInput, demo_contract=_demo)
def render(contract, ax=None, **_): ...
        │
        │  (import side-effect: inserts a _RegistryEntry keyed by
        │   full_name = "{modality}.{name}"; duplicate names raise ValueError)
        ▼
ensure_all_imported()        # pkgutil-walks the recipes/ package so every
        │                    # modality's decorators have run. Idempotent.
        ▼
list_recipes() / get_recipe(full_name) / list_modalities()
```

Because nothing is registered until imported, **callers (and tests) must call
`ensure_all_imported()` before querying** the registry. A forgotten import line
in a modality `__init__.py` silently omits a recipe with no error. The registry
is not thread-safe — acceptable for single-process CLI/MCP runs.

Key symbols: `register_recipe`, `ensure_all_imported`, `list_recipes`,
`get_recipe`, `list_modalities`, `register_modality`, `modality_aesthetic`,
`_RegistryEntry` (private; exposes `.full_name`, `.demo_contract()`).

---

## Contract / metadata / aesthetic relationship

Three artifacts travel with every recipe:

- **`RecipeContract`** (`contract.py`) — a near-empty pydantic `BaseModel` marker
  base. Each recipe subclasses it to declare its input fields. It sets
  `model_config = {"arbitrary_types_allowed": True}`, so raw `np.ndarray` fields
  get **no schema validation** — the validation guarantee is real only for
  declared scalar/typed fields. The CLI, MCP, data-binder, and composition engine
  all validate user data via `entry.contract.model_validate(...)` before
  `render`.
- **`RecipeMetadata`** (`contract.py`) — a frozen dataclass carrying catalog
  metadata (`name`, `modality`, `family`, `answers_question`, required/optional
  fields) plus a `kw_only` `StatisticalContract`. Its `RecipeFamily` is a closed
  `StrEnum` driving the `tests/quality_rules/` geometry gates.
- **`ModalityAesthetic`** (`aesthetic_base.py`) — one per modality, exposed as a
  module-level `AESTHETIC` object. Every recipe calls `AESTHETIC.apply_to_ax(ax)`
  so a whole modality renders as a visual family. `register_modality` accepts the
  aesthetic typed as `Any` (a known registration-boundary leak).

The embedded **`StatisticalContract`** (`statistical_contract.py`) defaults to an
all-permissive instance, so "no contract" and "explicitly permissive contract"
are indistinguishable. The audit layer (`manifest.statistical_audit`) consumes it
pre-render. Note: its `Literal` taxonomies are enforced only by static
type-checkers, **not** at runtime (unlike `RecipeFamily`, which raises on invalid
values).

---

## The palette facade (`palette.py`)

`Palette` is a frozen dataclass with cyclic `__getitem__` (`palette[3]` never
`IndexError`s — it repeats colors, which silently hides "too many groups" bugs),
an ordered color tuple, and an optional semantic name map. It has its **own
parallel registry** (`register_palette` / `get_palette` / `list_palettes` /
`palettes`) mirroring the recipe-registry pattern, pre-populated with
colorblind-safe built-ins (Okabe–Ito, sex-dimorphic, etc.). `semantic_color(name,
key, default=None)` is the recipe-facing convenience lookup.

---

## `apply_base_style` — the global-rcParams caveat (`style.py`)

`apply_base_style(theme="default", overrides=None)` configures matplotlib for
publication output (PDF/PS fonttype 42, `svg.fonttype "none"` for editor-friendly
vector output, the panelforge font stack, sizes, spine colors).

**Caveat:** it mutates the **global `matplotlib.rcParams`**, so it is
process-global and **not thread-safe**. Two concurrent renders with different
themes will race. For scoped changes prefer `temporary_style(overrides)` (a
context manager). `current_theme()` reports the last-applied theme name.

Supporting primitives also live here and in `primitives.py` — including
`add_halo_label`, which keeps its `halo_color`/`halo_width` kwargs for API
compatibility across ~390 callers but `del`-etes them and emits a plain
`ax.text` (the "halo" is an intentional no-op).

---

## Module index

| Module | Role |
|---|---|
| `contract.py` | Registry, `RecipeContract`, `RecipeMetadata`, `RecipeFamily`, `register_recipe`. |
| `statistical_contract.py` | `StatisticalContract` + its closed (static-only) taxonomies. |
| `aesthetic_base.py` | `ModalityAesthetic`, annotation/inset conventions. |
| `palette.py` | `Palette` + the palette registry facade. |
| `style.py` | `apply_base_style`, `temporary_style`, font/size constants. |
| `layout.py` | `make_figure`, `make_panel_grid`, `FIGSIZE_PRESETS`. |
| `primitives.py` | Shared drawing primitives. |
| `export.py` | `export_figure`, `multi_format_export`. |
| `qa.py` | Render quality-assurance helpers. |
| `*_utility.py` | Optional statistical helpers (KM survival, TOST, Bayes factor, transfer entropy, …), lazily importing scipy/statsmodels. |
