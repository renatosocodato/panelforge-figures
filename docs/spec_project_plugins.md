# Spec — Project-Extensible Recipes (Plugins)

**Status:** Draft v0 (executable scoping doc, not yet implemented)
**Target release:** v2.0.0
**Owner:** roadmap-v2-specs / W4
**Depends on:** core registry (`core/contract.py`), `manifest/catalog.py`, `manifest/intake.py`, `manifest/scoring.py`

## TL;DR

Local repos can register their own recipes alongside the 448-recipe catalog without forking panelforge-figures. A plugin is just a Python module (or installable package) that calls `register_recipe(...)` against the same registry the core catalog uses. `figures index emit` walks discovered plugins, validates them against the same JSON Schema, and merges them into a project-local `recipes_index.json` with provenance (`tags_source: "plugin:<name>"`). The 8-question intake and scorer treat catalog and plugin recipes identically. Discovery uses Python `entry_points` (preferred) with a directory-scan fallback for solo researchers who do not want to publish a package.

## 1. Problem statement

Every wet-lab group that uses panelforge ends up with 5–10 figures specific to their data: a kymograph variant tuned for the lab's particular line-scan acquisition, a per-genotype cohort layout for the consortium's reporting template, a custom diagnostic that combines two existing recipes for an internal QC pass. Today these one-offs require either (a) forking panelforge-figures and maintaining a divergent branch, (b) maintaining a parallel script collection that loses the contract/score machinery, or (c) submitting the recipe upstream even though it is too lab-specific to belong in the shared catalog.

The result is a missing extension slot in an otherwise mature tool. Mature plotting tools (matplotlib styles, seaborn palettes, snakemake wrappers) all expose a plugin shape. Panelforge does not.

This spec defines that extension shape. The non-negotiable: **plugin recipes are first-class.** They register through the same decorator, validate through the same schema, score against the same intake, and appear in `recipes_index.json` indistinguishable from the catalog except via a `tags_source` provenance label. Agents in the project see N+M recipes (catalog plus plugin), and the 8-question intake routes between them transparently.

## 2. Plugin discovery mechanism

Two discovery paths, both supported, both ending at the same `register_recipe(...)` call against the in-process registry.

**Preferred path: Python `entry_points`.** This is the native Python plugin idiom (`importlib.metadata.entry_points`), it survives `pip install -e`, it is what scientific tooling expects (pytest, jupyter, mkdocs all use it), and it does not require panelforge to know where the consumer's source tree lives. Plugin authors declare:

```toml
# pyproject.toml of the plugin package
[project.entry-points."panelforge.plugins"]
my_disc1_extra = "panelforge_disc1_extra"
```

At index-build time, panelforge calls `importlib.metadata.entry_points(group="panelforge.plugins")` and imports each named module. The module's `__init__.py` (or any submodule it imports) is responsible for invoking `@register_recipe(...)` exactly as catalog recipes do.

**Fallback path: directory scan.** For solo researchers who want to drop a single file into their project without packaging, panelforge looks for `panelforge_plugins/` at the project root (the directory containing `panelforge.project.yaml`, or `cwd` when the YAML is absent). The directory is added to `sys.path` ephemerally, then every `*.py` file (excluding `__init__.py` private modules prefixed with `_`) is imported via `importlib.import_module`. Each imported module is expected to call `register_recipe(...)` at import time, identically to entry-points plugins.

The scan is **opt-in by presence**. No `panelforge_plugins/` directory means zero plugins; no flag flip required.

A `panelforge.project.yaml` may override the directory name:

```yaml
anchor: DISC1
plugins_dir: panelforge_plugins/   # default; set to e.g. "figures/plugins/" to relocate
plugins_disabled: []                # explicit opt-out by plugin name
```

## 3. Plugin layout — single-file (solo researcher)

Minimum viable plugin, suitable for a one-off lab figure that should never escape this project:

```
my_disc1_project/
├── panelforge.project.yaml
└── panelforge_plugins/
    ├── __init__.py             # may be empty; presence triggers package-style import
    ├── plugin.yaml             # name, version, description, author
    ├── my_custom_kymograph.py  # one or more @register_recipe calls
    └── _shared.py              # optional shared helpers (leading underscore = not scanned)
```

`plugin.yaml` is a free-form metadata sidecar, surfaced by `figures plugins describe`:

```yaml
name: disc1_lab_extras
version: 0.1.0
description: DISC1 lab one-off recipes (line-scan kymograph variants).
author: Renato Socodato <renato@example.org>
panelforge_min_version: 2.0.0
panelforge_max_version: 2.99.0
```

Each `*.py` file imports the same primitives the catalog uses:

```python
from panelforge_figures.core import (
    RecipeContract, RecipeFamily, RecipeMetadata, register_recipe
)

class MyKymographInput(RecipeContract):
    line_scan: list[list[float]]
    title: str = "DISC1 line-scan"

_META = RecipeMetadata(
    name="disc1_line_scan_kymograph",
    modality="disc1_extras",                  # plugin-namespaced modality
    family=RecipeFamily.heatmap,
    answers_question="What is the spatiotemporal evolution of the line-scan?",
    required_fields=("line_scan",),
)

@register_recipe(metadata=_META, contract=MyKymographInput, demo_contract=lambda: ...)
def render(contract, ax=None, **_):
    ...
```

There is no panelforge-side modification. The plugin is "the same shape as a catalog recipe, but it lives in the consumer's tree."

## 4. Plugin layout — installable package (group)

For a group sharing a plugin across labs (e.g. a clinical-cohort plugin used by three sites), packaging is preferable so `pip install` plus the entry-point is enough:

```
panelforge-disc1-extra/
├── pyproject.toml
├── README.md
├── LICENSE
└── src/panelforge_disc1_extra/
    ├── __init__.py             # imports each recipe submodule, triggering @register_recipe
    ├── recipes/
    │   ├── __init__.py
    │   ├── disc1_genotype_panel.py
    │   ├── disc1_cohort_violin.py
    │   └── disc1_qc_strip.py
    └── plugin.yaml             # same shape as single-file plugins
```

`pyproject.toml`:

```toml
[project]
name = "panelforge-disc1-extra"
version = "0.1.0"
dependencies = ["panelforge-figures>=2.0,<3.0"]

[project.entry-points."panelforge.plugins"]
disc1_extra = "panelforge_disc1_extra"
```

`pip install panelforge-disc1-extra` makes the plugin discoverable in any project that has panelforge-figures, with no project-level configuration required.

## 5. Plugin discovery in `figures index emit`

`build_index()` in `manifest/catalog.py` is extended with a plugin-walk pass that runs **after** `ensure_all_imported()` (the catalog scan) and **before** the per-recipe loop. The walk:

1. Reads `panelforge.project.yaml` if present; otherwise uses defaults (`plugins_dir=panelforge_plugins/`, no disabled list).
2. Iterates `entry_points(group="panelforge.plugins")`. For each entry point not in `plugins_disabled`, imports its target module. The plugin name is the entry-point key.
3. If `<project_root>/<plugins_dir>/` exists, prepends it to `sys.path` and imports every non-underscore `*.py` inside it. Each plugin name is taken from the first of: `plugin.yaml.name`, the module's `__plugin_name__`, the file stem.
4. Records each plugin in a per-process `_LOADED_PLUGINS` table: `{name: PluginRecord(source, version, recipes=[...])}`. Recipes registered between "before plugin import" and "after plugin import" are attributed to that plugin.

Each plugin recipe in the merged catalog gets:

- `tags_source: "plugin:<plugin_name>"` (alongside the existing `auto`/`override`/`merged` values from the YAML-merge layer).
- `plugin_metadata: {name, version, source}` block at the recipe level (so an agent reading `recipes_index.json` knows which plugin to credit).
- The same JSON-Schema validation as catalog recipes (no special-casing). A bad plugin recipe fails the index emit; partial success is not allowed.

A plugin recipe and a catalog recipe with the same `<modality>.<name>` is a fatal error (see §6).

## 6. Plugin priority + conflict resolution

**Policy: fail fast on duplicate `full_name`.** Two recipes with the same `<modality>.<name>` cannot coexist. `register_recipe` already raises on duplicates within a single registry; plugins re-use the same registry, so this falls out of the existing implementation. The error message names both the catalog recipe and the offending plugin so the user knows which to rename.

This is intentional. Allowing plugins to "shadow" catalog recipes by name would be a footgun: a plugin author shipping a same-name recipe could silently change the figure an agent draws. If an extension genuinely wants to provide an alternative to a catalog recipe, the plugin author should:

1. Register the recipe under a plugin-namespaced modality (e.g. `disc1_extras.cohort_violin`), and
2. Declare `alternatives_in_modality=("clinical_cohort.cohort_violin",)` in the plugin recipe's metadata.

The cross-modality `alternatives_in_modality` link surfaces the plugin as a sibling in the catalog's "see also" view. Agents and scorers use the link symmetrically: scoring a question that ranks the catalog recipe also ranks the plugin recipe one notch lower (or higher, depending on the rubric weight on plugin authorship — TBD, see §15).

## 7. Plugin distribution

**Single-file plugins** are checked into the project repo alongside the data. They travel with the project; they are reproducible by clone alone; they require no PyPI presence. This is the right shape for a thesis project, a paper supplement, or a one-off internal report. The cost is per-project duplication if two projects want the same recipe.

**Installable plugins** are published to PyPI (or a private index) and `pip install`-ed. They survive across projects, version cleanly, can declare panelforge version pins, and integrate with reproducible-environment tooling (`pip-compile`, `uv lock`, `conda-lock`). The cost is the packaging overhead, which is non-trivial for a wet-lab researcher.

The two shapes are first-class equally; no "preferred" path in the docs. The implementation does not branch on which kind of plugin a recipe came from — both end at `register_recipe(...)`.

## 8. `panelforge.project.yaml` integration

The project-config YAML (already used by `manifest/project_scan.py`) gains three fields:

```yaml
anchor: DISC1
plugins_dir: panelforge_plugins/    # optional; default panelforge_plugins/
plugins_disabled:                    # optional; explicit opt-out by plugin name
  - flaky_kymograph_v0
plugins_strict: true                 # optional; default true; fail-fast on plugin error
```

`plugins_strict: true` (the default) makes `figures index emit` exit non-zero on any plugin error: import failure, schema-validation failure, name collision. `plugins_strict: false` downgrades errors to warnings and skips the offending plugin — useful in research mode but **never** in CI.

`plugins_disabled` is the user's escape hatch for a plugin that is broken or whose author has gone dark; it suppresses discovery without uninstalling.

## 9. Three worked examples

### Example A — single-file plugin

A DISC1 lab has a one-off compound figure that overlays Ca²⁺ event amplitude on a per-genotype cohort plot. They drop one file into the project:

```
disc1_paper/
├── panelforge.project.yaml
├── data/
└── panelforge_plugins/
    ├── plugin.yaml
    └── disc1_specific_compound.py
```

`disc1_specific_compound.py` defines `DISC1CompoundInput`, instantiates `RecipeMetadata(name="disc1_compound_overlay", modality="disc1_extras", ...)`, decorates `render()` with `@register_recipe(...)`. The user runs:

```bash
$ figures index emit --include-tags
[...]
n_recipes=449  (448 catalog + 1 plugin)
```

`recipes_index.json` now has a 21st modality (`disc1_extras`) with one recipe whose `tags_source` is `"plugin:disc1_extras"`. The intake scorer treats it identically to catalog recipes; an agent answering the 8-question intake may receive `disc1_extras.disc1_compound_overlay` as the top-ranked recipe for a DISC1-specific question.

### Example B — installable plugin

A clinical consortium publishes `panelforge-clinical-extra` to PyPI. The package contains 12 cohort-specific recipes (genotype-stratified Kaplan–Meier, ARIA event raster, etc.). A site member at one of the participating labs runs:

```bash
$ pip install panelforge-clinical-extra
$ figures index emit --include-tags
n_recipes=460  (448 catalog + 12 plugin)
```

The package's `pyproject.toml` declares `[project.entry-points."panelforge.plugins"] clinical_extra = "panelforge_clinical_extra"`. No project-level configuration required; installation alone is sufficient. `figures plugins list` reports the plugin with version `0.1.0` and 12 recipes. The 8-question intake's "what is the cohort design?" question now scores against the 12 clinical-extra recipes alongside the catalog's `clinical_cohort/` modality.

### Example C — plugin with `alternatives_in_modality` cross-link

A second plugin (`panelforge-trajectories`) provides an enriched alternative to the catalog's `single_cell_embeddings.umap_trajectory` recipe. The plugin author registers under `trajectories_extra.umap_trajectory_pseudo_force` with metadata:

```python
RecipeMetadata(
    name="umap_trajectory_pseudo_force",
    modality="trajectories_extra",
    family=RecipeFamily.embedding_trajectory,
    answers_question="...",
    required_fields=("umap_xy", "pseudotime"),
    alternatives_in_modality=("single_cell_embeddings.umap_trajectory",),
)
```

In `recipes_index.json`, the catalog recipe and the plugin recipe cross-reference each other (the link is reciprocal at index-build time). Scoring a "trajectory inference" question surfaces both, ranked by data-fit; the plugin is no more or less privileged than the catalog recipe.

## 10. CLI surface

A new `figures plugins` subcommand group, in `cli.py`:

```
figures plugins list                 # print discovered plugins (name, version, source, n_recipes)
figures plugins describe <name>      # plugin.yaml content, registered recipes, file paths
figures plugins disable <name>       # append to panelforge.project.yaml: plugins_disabled
figures plugins enable <name>        # remove from panelforge.project.yaml: plugins_disabled
figures plugins doctor               # validate every discovered plugin's metadata + run schema check
```

`figures plugins disable` and `enable` mutate `panelforge.project.yaml` in place (with a `--dry-run` flag for safety). `figures plugins doctor` is a one-shot validator suitable for CI: it imports every plugin, runs each through the JSON-Schema validator, reports any failures, and exits non-zero if `plugins_strict` would fail.

## 11. Files to create / modify

**NEW** `src/panelforge_figures/plugins/__init__.py` — ~150 LOC. Public API: `discover_plugins() -> list[PluginRecord]`, `load_plugins(record_list) -> None`, `loaded_plugins() -> list[PluginRecord]`. Owns the `entry_points` walk, the directory scan, the `plugins_disabled` filter, the per-plugin import context (so attribution works), and the `PluginRecord` dataclass.

**EDIT** `src/panelforge_figures/manifest/catalog.py` — `build_index` calls `discover_plugins()` then `load_plugins(...)` between `ensure_all_imported()` and the modality loop. Plugin-attributable recipes get `tags_source: "plugin:<name>"` + `plugin_metadata: {...}` in the per-recipe block.

**EDIT** `src/panelforge_figures/cli.py` — add the `figures plugins` subcommand group with `list`, `describe`, `disable`, `enable`, `doctor`.

**EDIT** `src/panelforge_figures/manifest/project_scan.py` — read the new `plugins_dir`, `plugins_disabled`, `plugins_strict` fields; surface them on the `ProjectConfig` dataclass.

**EDIT** `docs/recipes_index.schema.json` — add optional `plugin_metadata` and extend the `tags_source` enum to allow `"plugin:*"` (open-ended, schema validates the prefix).

**NEW** `docs/PLUGIN_AUTHORING.md` — author-facing guide: how to scaffold a plugin, the `RecipeMetadata` checklist, the `plugin.yaml` schema, security advisory (§14), version-pinning recommendation.

**NEW** `tests/test_plugin_discovery.py` — ~200 LOC, ~12 tests (see §13).

**NEW** `tests/fixtures/sample_plugin/` — minimal single-file plugin fixture: one recipe, one `plugin.yaml`, one `__init__.py`. Used by 4 of the 12 tests.

**NEW** `tests/fixtures/sample_entry_point_plugin/` — minimal installable-shape plugin fixture, registered via a fake `entry_points` shim in test setup.

## 12. Test surface (≥10 tests)

1. `test_single_file_plugin_discovers_and_loads_recipe` — `tests/fixtures/sample_plugin/` is found, imported, and its one recipe appears in `list_recipes()`.
2. `test_entry_points_plugin_loads_via_metadata` — a fake `entry_points` shim exposes `tests/fixtures/sample_entry_point_plugin/`; `discover_plugins()` returns it; `load_plugins()` registers it.
3. `test_duplicate_full_name_raises_at_index_time` — plugin recipe with same `<modality>.<name>` as catalog → `ValueError` on `build_index()`.
4. `test_plugins_disabled_suppresses_discovery` — `panelforge.project.yaml: plugins_disabled: [sample_plugin]` removes the plugin from `loaded_plugins()`.
5. `test_plugin_recipe_appears_in_index_with_correct_tags_source` — emitted `recipes_index.json` has `tags_source: "plugin:sample_plugin"` for the plugin recipe.
6. `test_plugin_recipe_validated_by_json_schema` — plugin recipe missing required field fails the same JSON-Schema validation as a catalog recipe.
7. `test_intake_scorer_treats_plugin_and_catalog_identically` — give the intake a question; verify a plugin recipe and a catalog recipe with the same answer-fit score tie at the same rank.
8. `test_plugin_with_bad_metadata_fails_fast_with_clear_error` — plugin missing `RecipeMetadata.answers_question` → import-time error names the plugin and the file.
9. `test_alternatives_in_modality_cross_link_to_catalog` — plugin recipe declares `alternatives_in_modality=("clinical_cohort.foo",)`; the cross-link appears reciprocally in `recipes_index.json`.
10. `test_plugins_strict_false_downgrades_error_to_warning` — broken plugin + `plugins_strict: false` → emits index, logs warning, exits 0; `plugins_strict: true` → exits non-zero.
11. `test_plugin_metadata_block_includes_version_and_source` — emitted recipe has `plugin_metadata.version` from `plugin.yaml`.
12. `test_figures_plugins_list_reports_discovered_plugins` — CLI smoke test: `figures plugins list` lists `sample_plugin` with the right metadata.

Optional 13th: `test_plugins_dir_override_respected` — non-default `plugins_dir: figures/plugins/` is honoured.

## 13. Security considerations

Plugins are arbitrary Python code. Importing a plugin runs that code in the panelforge process with the user's full permissions. There is no sandbox in v2.

This is the same trust model as `pip install` of any Python package, but it is worth being explicit because plugins are designed to be informally shared (drop a file, copy a folder). `PLUGIN_AUTHORING.md` will state plainly:

> A panelforge plugin is regular Python that runs in your environment. Only install plugins from sources you trust. `figures plugins describe` shows the plugin's source path and author so you can review before enabling.

`figures plugins describe` surfaces `plugin.yaml` in full (author, source, version, description) so the user has a one-command way to see what they are about to enable. `figures plugins doctor` does not execute any plugin code beyond import — it does not run `render()`.

Sandboxing (subprocess isolation, restricted import set, capability filter) is deferred to v3; see §16.

## 14. Risks and mitigations

**Risk: a plugin breaks on panelforge upgrade.** Plugin imports `core.RecipeMetadata`; we change `RecipeMetadata` in v2.1; the plugin breaks. Mitigation: `plugin.yaml.panelforge_min_version` and `panelforge_max_version` are surfaced by `figures plugins doctor`; versions outside the range emit a warning. Plugin authors are encouraged to pin (`>=2.0,<3.0`) in `pyproject.toml` for installable plugins. We will treat the `core` namespace as semver-stable across minor releases of panelforge.

**Risk: plugin name collision across two installed packages.** Two PyPI plugins both register `disc1_extra` as their entry-point key. Mitigation: `entry_points` keys are namespaced by Python distribution name; collisions are rare. When they do happen, `discover_plugins` raises with both distribution names so the user can `pip uninstall` one.

**Risk: recipe full-name collision (catalog vs plugin, or plugin vs plugin).** Already covered in §6 — fail fast, name both sides. Plugin authors are encouraged to namespace their modality (`disc1_extras.recipe`, not `clinical_cohort.recipe`).

**Risk: silently slow indexing.** A plugin with 200 recipes adds 200 imports and 200 schema validations to every `figures index emit`. Mitigation: `figures plugins doctor --time` reports per-plugin import + validation cost; `index_meta.timing.plugin_load_ms` is added to the index.

**Risk: leftover `sys.path` mutations.** The directory-scan path mutates `sys.path` to import the plugin module. Mitigation: scope the mutation in a `try/finally` block; assert in tests that `sys.path` is restored.

## 15. Open questions / spec ambiguity flagged

- **Score weighting for plugin recipes.** The current rubric does not distinguish source. Should plugin recipes be ranked at parity, slightly preferred (because they are project-specific), or slightly penalised (because they are unvetted)? Current default in this spec: parity. Decision to be made before implementation.
- **Plugin metadata for the YAML override.** `docs/recipe_tags.yaml` carries override tags for catalog recipes. Should plugin recipes be allowed to ship their own `recipe_tags.yaml`? This spec assumes **yes**: a plugin may include `recipe_tags.yaml` at its package root and its entries are merged with the same precedence rules. Confirm before implementation.
- **Entry-point group naming.** This spec uses `"panelforge.plugins"`. We could split into `"panelforge.recipes"` and `"panelforge.adapters"` for forward-compatibility with adapter plugins. Recommend deferring; one group for v2 keeps the surface small.

## 16. Acceptance criteria

The release is gated on all of the following:

1. `tests/fixtures/sample_plugin/` discovers, registers, and scores correctly under `figures index emit --include-tags`.
2. An installable plugin via `entry_points` (`tests/fixtures/sample_entry_point_plugin/` plus a fake-`entry_points` shim) discovers, registers, and scores correctly.
3. `figures plugins list` reports the discovered plugins with name, version, source, and recipe count.
4. `figures plugins describe <name>` prints the full `plugin.yaml` and the list of registered recipes.
5. `figures plugins disable <name>` writes to `panelforge.project.yaml` and the plugin is suppressed on next index emit.
6. Plugin recipes co-exist with catalog recipes in `recipes_index.json` with no name collision (or fail-fast with a clear error pointing at both sides).
7. JSON-Schema validation runs identically on plugin and catalog recipes.
8. The 8-question intake / scorer ranks plugin recipes alongside catalog recipes without code-path branching.
9. ≥10 tests in `tests/test_plugin_discovery.py` pass deterministically; CI runs them on Linux + macOS.
10. `docs/PLUGIN_AUTHORING.md` documents the authoring path end-to-end (single-file + installable), including the security advisory.

## 17. Out of scope (defer to v3+)

- **Plugin sandboxing / permission model.** No subprocess isolation, no restricted imports, no capability filter in v2. Trust is binary: install or don't.
- **Plugin marketplace / discovery service.** No central registry, no `figures plugins search`. Distribution is PyPI for installable, git for single-file. v3 may revisit.
- **Cross-language plugins.** R, Julia, JavaScript recipes would require an FFI layer the v2 architecture does not have. Deferred indefinitely.
- **Hot-reload.** Plugin changes require re-running `figures index emit`. No watch mode.
- **Plugin signing / provenance attestation.** No SBOM, no signature check. v3 may add.
- **Plugin-scoped configuration.** Plugins read `panelforge.project.yaml` only via the standard panelforge API; no per-plugin config sections in v2.
