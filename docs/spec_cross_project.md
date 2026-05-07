# Cross-project orchestration — a portfolio view of panelforge work

**Status:** proposal
**Version target:** v2.0.0
**Author:** _(W7 swarm scribe; placeholder for v2.0.0 owner)_
**Plan file:** _(to be assigned)_
**Spec siblings:** `docs/spec_*.md` (parallel v2.0.0 elevations)

**TL;DR.** v1.6.1 Claude Code sessions are single-repo by construction — every new project starts cold from `figures profile scan`, with no memory that `~/manuscripts/example_modality_a` and `~/manuscripts/example_modality_b` already share three meta-and-diagnostic recipes. A working scientist juggles three manuscript repos plus a methods paper plus a grant simultaneously, but no panelforge command admits this multi-project reality. This spec proposes a per-user **project registry** at `~/.config/panelforge/projects.yaml` that records every panelforge project the user has touched, plus a `figures projects {list,register,switch,current,diff,portfolio,unregister,validate}` CLI surface that surfaces recipe-overlap, suggests shared-methods extraction, and warm-loads previously scanned workspaces. The registry stores **paths, not data** — switching projects only `cd`s and re-reads the local `panelforge_workspace/`; nothing is implicitly copied.

---

## 1. Problem statement — the multi-repo gap

Panelforge in v1.6.1 was designed under a single-project mental model: open one repo, run `figures profile scan`, work the 8-question intake, render the 12 recipes the scorer recommends, ship Figure 3. The model fits a graduate student writing one thesis chapter. It does not fit the working PI who has four windows open.

Three concrete frictions surfaced from the disc1 and cdc42 companion packs and the early intravital / biophysics betas:

1. **Cold-start tax per project.** Every new repo runs `figures profile scan` from scratch, even when the user has already answered "yes" to "uses Bayesian priors?" in three other projects this month. There is no warm cache of "what kind of scientist is this?" across projects.
2. **Recipe-overlap is invisible.** The disc1 manuscript picks `bayes_factor_arrow_plot` for Figure 4. Three weeks later the cdc42 manuscript picks the same recipe, and the user re-derives that decision (and writes the same caption boilerplate) from scratch, never knowing a sibling project converged on the identical choice. There is no portfolio view that would surface "you've used this recipe in 3 of 5 projects — extract it".
3. **No "where am I" prompt.** When a Claude Code session resumes after a coffee break, there is no `figures projects current` to confirm the workspace, the active profile, and the last render status. The user must `cat panelforge_workspace/state.json` and pattern-match. This is fine once; it scales badly across 5 repos.

The solution is small in surface area and zero-data-leakage in design: a YAML registry of `{project_id → metadata}` in the user's config dir, queryable through a new CLI subcommand group. Each per-project workspace continues to own its truth (`panelforge.project.yaml`, `panelforge_workspace/`); the registry is a **pointer index**, never a data store.

---

## 2. `~/.config/panelforge/projects.yaml` — schema

Canonical location follows the XDG Base Directory spec (with `$XDG_CONFIG_HOME` honoured if set, else `~/.config/`). Loaded by `panelforge_figures.projects.load_registry()`; safe-loaded with a fallback to an empty registry on any parse error (see §11).

```yaml
# ~/.config/panelforge/projects.yaml
schema_version: 1
default_project: example_modality_a_2026

projects:
  example_modality_a_2026:
    path: ~/manuscripts/example_modality_a
    last_used: 2026-05-04T15:32:00Z
    active_profile: disc1
    n_recipes_picked: 12
    last_render_status: 11/12 success
    tags:
      - manuscript
      - microglia
      - bayesian

  example_modality_b_2026:
    path: ~/manuscripts/example_modality_b
    last_used: 2026-05-06T09:18:00Z
    active_profile: example_modality_b
    n_recipes_picked: 19
    last_render_status: 19/19 success
    tags:
      - manuscript
      - actin
      - factorial

  methods_paper_2026:
    path: ~/manuscripts/methods_paper
    last_used: 2026-04-22T11:04:00Z
    active_profile: methods
    n_recipes_picked: 6
    last_render_status: 6/6 success
    tags:
      - methods-paper

  example_grant_2026:
    path: ~/grants/example_grant
    last_used: 2026-05-02T16:40:00Z
    active_profile: grant
    n_recipes_picked: 4
    last_render_status: 4/4 success
    tags:
      - grant
      - r01
```

### 2.1 Field semantics

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int | Currently `1`. Used for forward-compat migration. |
| `default_project` | string | The project assumed when no `--project` flag is passed; updated by `figures projects switch`. |
| `projects.<id>.path` | absolute path | Authoritative pointer; if the path no longer exists, `figures projects validate` flags the entry. |
| `projects.<id>.last_used` | ISO 8601 UTC | Auto-updated on every `figures` invocation that touches that project. |
| `projects.<id>.active_profile` | string | Name of the active panelforge profile in that project's `panelforge_workspace/`. |
| `projects.<id>.n_recipes_picked` | int | Count from the most recent `manifest.yaml`; cached for fast `list` rendering without I/O on every project. |
| `projects.<id>.last_render_status` | string | `"<n_success>/<n_total> success"` — one-line summary; full status remains in the per-project workspace. |
| `projects.<id>.tags` | list[string] | Free-form labels — the user's own taxonomy (`manuscript`, `grant`, `microglia`, `r01`). |

The `id` (top-level key under `projects`) is canonical and stable; defaults to the `project_id` declared in the project's own `panelforge.project.yaml`, with a `<basename>_<YYYY>` fallback for unnamed projects.

---

## 3. CLI surface — `figures projects`

A new subcommand group on the existing `figures` Click app. All subcommands respect `--config-path` for non-default registry locations (CI, sandboxed users).

| Command | Purpose |
|---|---|
| `figures projects list` | Table of registered projects with last-used + status. |
| `figures projects register [path]` | Add the directory to the registry (path defaults to cwd). |
| `figures projects switch <id>` | Set `default_project` and warm-load that project's workspace. |
| `figures projects current` | Print the active project + key metadata; exit 0 if registered, 1 otherwise. |
| `figures projects diff <a> <b>` | Recipe-overlap analysis between two projects. |
| `figures projects portfolio` | Visual summary across all projects (recipe heatmap + top-10). |
| `figures projects unregister <id>` | Remove from the registry; **never** deletes project files. |
| `figures projects validate` | Walk the registry, drop entries whose `path` no longer exists, with a confirm prompt unless `--yes`. |

`switch` and `current` are intentionally cheap: they re-read `panelforge_workspace/state.json` from the target project but do **not** re-run a scan or re-render. The implicit contract is that the local workspace is the source of truth — the registry is only an index.

---

## 4. `projects diff` output — recipe-overlap analysis

The diff command is the headline feature: it converts "I think these two papers reuse some methods" into a printed list. It loads the two target projects' `panelforge_workspace/manifest.yaml` files, extracts the set of recipe IDs each has rendered (or queued), and reports overlap.

```
$ figures projects diff disc1 cdc42

Project A (example_modality_a_2026): 12 recipes
Project B (example_modality_b_2026): 19 recipes

Shared (3):
  - meta_and_diagnostic.bayes_factor_arrow_plot              [DISC1 + CDC42]
  - actin_microtubule_morphometry.compartment_paired_delta_scatter
  - biophysics_scaling.equivalence_forest_with_tost_bounds

A only (9):
  - omics_differential.module_concordance_signed_heatmap
  - …

B only (16):
  - factorial.sex_x_genotype_interaction_forest
  - …

Suggestion: extract a `shared_methods.figure.yaml` using the 3 shared
recipes — single source of truth for common methods across both papers.
Run:  figures compose-from-shared disc1 cdc42 --out shared_methods.figure.yaml
```

The "Suggestion" line is heuristic: ≥ 3 shared recipes triggers the prompt; < 3 stays silent. The `compose-from-shared` follow-on is a dependency on the §spec_composition_layer composition CLI; if that spec is not yet implemented, the suggestion text is replaced with a passive `"3 recipes are candidates for shared-methods extraction"` line.

---

## 5. Three worked examples

### 5.1 Example A — register four projects, list them, switch

```
$ figures projects register ~/manuscripts/example_modality_a
✓ Registered as `example_modality_a_2026`. (default project)

$ figures projects register ~/manuscripts/example_modality_b
✓ Registered as `example_modality_b_2026`.

$ figures projects register ~/manuscripts/panelforge_methods
✓ Registered as `methods_paper_2026`.

$ figures projects register ~/grants/example_grant
✓ Registered as `example_grant_2026`.

$ figures projects list
ID                       LAST USED          PROFILE            RECIPES   STATUS         TAGS
* example_modality_a_2026     2026-05-04 15:32   disc1              12        11/12 success  manuscript, microglia
  example_modality_b_2026     2026-05-06 09:18   example_modality_b    19        19/19 success  manuscript, actin
  methods_paper_2026       2026-04-22 11:04   methods             6         6/6 success   methods-paper
  example_grant_2026         2026-05-02 16:40   grant               4         4/4 success   grant, r01

(* = default project; switch with `figures projects switch <id>`)

$ figures projects switch example_modality_b_2026
✓ Switched. Active profile: example_modality_b. 19 recipes in manifest.
  (warm-loaded panelforge_workspace/state.json — no scan re-run)
```

### 5.2 Example B — `diff` surfaces shared-methods candidate

```
$ figures projects diff example_modality_a_2026 example_modality_b_2026
```

Output is the §4 listing verbatim. The user runs:

```
$ figures compose-from-shared example_modality_a_2026 example_modality_b_2026 \
    --out shared_methods.figure.yaml
✓ Wrote shared_methods.figure.yaml (3 panels, ~150 lines)
  Place under each project's panelforge_workspace/figures/ to reuse.
```

This converts a wandering observation into a versionable artefact in 30 seconds.

### 5.3 Example C — `portfolio` heatmap across all five projects

```
$ figures projects portfolio
Portfolio summary — 5 projects, 47 distinct recipes used

Top 10 recipes (by project-count):
  5/5  meta_and_diagnostic.run_provenance_card
  4/5  meta_and_diagnostic.bayes_factor_arrow_plot
  3/5  actin_microtubule_morphometry.compartment_paired_delta_scatter
  3/5  biophysics_scaling.equivalence_forest_with_tost_bounds
  2/5  omics_differential.module_concordance_signed_heatmap
  …

Recipe usage heatmap  (• = used, · = unused)
                                              disc1 cdc42 meth grant intra
  meta_and_diagnostic.run_provenance_card       •     •     •    •     •
  meta_and_diagnostic.bayes_factor_arrow_plot   •     •     ·    •     •
  actin_mt.compartment_paired_delta_scatter     •     •     •    ·     ·
  biophysics_scaling.equiv_forest_tost          •     •     ·    •     ·
  omics_diff.module_concordance_signed_heatmap  •     ·     •    ·     ·
  …

Suggestion: 4 recipes appear in ≥ 3 projects — strong candidates for
            a shared 'lab-default' figure spec.
```

The heatmap is rendered in the terminal with Unicode block characters; a `--png <path>` flag emits a matplotlib PNG for slide decks.

---

## 6. Integration with `panelforge.project.yaml`

The project-local `panelforge.project.yaml` (already defined by `manifest/project_scan.py`) gains an opt-in **auto-registration** behaviour:

1. On the first invocation of `figures profile scan` (or any `figures` command that loads `panelforge.project.yaml`), `project_scan.py` calls `panelforge_figures.projects.register_if_absent(path, project_id, profile)`.
2. If the registry doesn't exist yet, `register_if_absent` creates `~/.config/panelforge/projects.yaml` with `schema_version: 1`, `default_project: <this_project_id>`, and the single entry.
3. If the project is already in the registry, only `last_used`, `active_profile`, `n_recipes_picked`, and `last_render_status` are updated — never the `path` or `tags` (those are user-managed).

Auto-registration is silent on success and logs a single info line on first registration. Users who do not want this behaviour can pass `--no-auto-register` (per-invocation) or set `auto_register: false` in `panelforge.project.yaml` (sticky).

`figures projects unregister <id>` is the deliberate deregistration counterpart: it removes the entry from the registry but **never** deletes the project directory or its `panelforge_workspace/`. Re-scanning a deregistered project re-registers it (unless `auto_register: false` is set).

---

## 7. Privacy + portability invariants

The registry is intentionally lightweight to keep three invariants:

1. **Paths, not data.** No recipe outputs, no figure PDFs, no contract data ever lives in `~/.config/panelforge/projects.yaml`. The file is small (kilobytes) and contains pointers, summary counts, and timestamps — nothing a `cat` would reveal that is not already on the user's filesystem.
2. **User-readable + user-editable.** A user can `cat ~/.config/panelforge/projects.yaml` and see exactly what's registered. Manual edits (rename a tag, change `default_project`) are first-class supported; `figures projects validate` does not rewrite tags or `default_project`.
3. **No implicit data movement.** `figures projects switch` only updates `default_project` and re-reads the target's local workspace state. It does **not** copy, sync, or export anything between projects. Project-to-project data flow remains a manual user decision (e.g., the `figures compose-from-shared` follow-on in Example B).

These invariants make the feature safe to enable by default: the worst case of a corrupted registry is "panelforge forgets which project you opened last" — it never loses data, and the per-project workspace always remains the truth.

---

## 8. Files to create / modify

- **NEW** `src/panelforge_figures/projects/__init__.py` (~250 LOC)
  - `load_registry(config_path: Path | None) -> Registry`
  - `save_registry(registry: Registry, config_path: Path | None) -> None`
  - `register_if_absent(path, project_id, profile, *, n_recipes, status) -> None`
  - `switch(project_id) -> ProjectEntry`
  - `unregister(project_id, *, missing_ok=False) -> None`
  - `diff(a_id, b_id) -> DiffReport`
  - `validate(*, prompt=True) -> list[str]` (returns dropped IDs)
- **NEW** `src/panelforge_figures/projects/portfolio.py` (~200 LOC)
  - `aggregate(registry) -> PortfolioSummary` (recipe-count vector per project)
  - `top_n_recipes(summary, n=10) -> list[RecipeUsage]`
  - `render_heatmap_terminal(summary) -> str`
  - `render_heatmap_png(summary, path) -> Path`
- **EDIT** `src/panelforge_figures/cli.py`
  - Add `projects` subcommand group with eight commands listed in §3.
- **EDIT** `src/panelforge_figures/manifest/project_scan.py`
  - Append `register_if_absent(...)` call at the end of `scan(path)`, gated by `auto_register` flag.
- **NEW** `tests/test_projects.py` (~250 LOC) — see §10.

Total: ~700 new LOC + ~30 LOC of edits — sized for a single PR.

---

## 9. API sketch — `Registry` dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

@dataclass(frozen=True)
class ProjectEntry:
    id: str
    path: Path
    last_used: datetime
    active_profile: str
    n_recipes_picked: int
    last_render_status: str
    tags: tuple[str, ...] = ()

@dataclass
class Registry:
    schema_version: int = 1
    default_project: str | None = None
    projects: dict[str, ProjectEntry] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> "Registry": ...
    def add(self, entry: ProjectEntry, *, set_default: bool = False) -> None: ...
    def get(self, project_id: str) -> ProjectEntry: ...
    def remove(self, project_id: str, *, missing_ok: bool = False) -> None: ...
```

Persistence is `yaml.safe_dump` for write and `yaml.safe_load` for read; corrupted YAML falls back to `Registry.empty()` with a `RuntimeWarning`.

---

## 10. Test surface

`tests/test_projects.py` — pytest, ~250 LOC, six clusters:

1. **Round-trip** — register → save → load → entries equal; `default_project` preserved.
2. **List / switch / unregister** — switch updates `default_project`; unregister removes the entry but does not touch the filesystem.
3. **Diff** — two synthetic projects with deterministically-mocked manifests (3 shared, 9 / 16 unique); assert exact `DiffReport`.
4. **Portfolio aggregation** — five mock projects, assert top-10 ordering and heatmap dimensions.
5. **Missing path** — `validate()` drops entries whose `path` no longer exists; non-existent path on `switch` raises `ProjectPathMissing`.
6. **Corrupted YAML** — write a malformed `projects.yaml`, assert `load_registry` returns `Registry.empty()` and emits a `RuntimeWarning` (no exception).

Coverage target: ≥ 95 % of `panelforge_figures.projects` (small module, easy to hit).

---

## 11. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Stale entries (project deleted from disk). | `figures projects validate` walks every entry, calls `path.exists()`, prompts for removal. Never auto-deletes without confirmation. |
| YAML corruption (truncated write, manual edit error). | `yaml.safe_load` + try/except → fall back to empty registry + emit `RuntimeWarning`. The corrupted file is renamed to `projects.yaml.broken-<timestamp>` before the empty registry is written, so the user can recover. |
| Concurrent access from two terminals. | Last-writer-wins is acceptable for solo users (the registry is bounded; collisions are rare). A simple advisory `fcntl.flock` on `projects.yaml` during write keeps two near-simultaneous writes from interleaving on POSIX; on platforms without `fcntl` the flock is a no-op and we accept LWW. |
| Registry path injection (someone plants a malicious `~/.config/panelforge/projects.yaml`). | All `path` values are validated as absolute, `realpath`-resolved, and confined to existing directories before any I/O is performed against them. The registry never executes anything from a project; it only reads its `panelforge.project.yaml` and `panelforge_workspace/state.json`. |
| Project-id collisions (two repos with the same `project_id`). | `register_if_absent` detects an existing ID at a different path, raises `ProjectIdCollision`, and instructs the user to set a unique `project_id` in `panelforge.project.yaml` or pass `--id <new>`. |

---

## 12. Acceptance criteria

The feature is shippable when:

1. A 4-project registry round-trips through save / load / switch / unregister with no data loss.
2. `figures projects diff` correctly identifies the shared and unique recipes for two synthetic test projects with known overlap.
3. `figures projects portfolio` produces a coherent summary (top-10 list + terminal heatmap + optional PNG) over a 5-project test registry.
4. Auto-registration on first `figures profile scan` works and is silent on subsequent invocations of the same project.
5. `figures projects validate` cleans stale entries (project path no longer exists) under a confirm prompt.
6. Corrupted `projects.yaml` falls back to an empty registry with a `RuntimeWarning` and a `.broken-<ts>` backup, with no exception leaking to the user.

---

## 13. Out of scope (deferred)

- **Multi-user shared registries.** A group account or shared `/etc/panelforge/projects.yaml` is interesting for labs but adds permissions / locking complexity that single-user v2.0.0 does not need. Defer.
- **Cloud-sync of registries across machines.** A laptop ↔ workstation sync (Dropbox, iCloud, syncthing) is a downstream user choice — they can already symlink `~/.config/panelforge/projects.yaml` into a synced folder. We do not ship a built-in sync.
- **Project templates / cloning.** `figures projects clone <a> --as <b>` (copy the structure of one project into a new directory) is a tempting feature but bleeds into project-scaffolding territory and depends on §spec_composition_layer composition primitives. Defer.
- **Cross-project recipe-history search.** A `figures projects grep <recipe>` that lists every project that ever rendered a given recipe is a natural follow-on but easily user-implementable on top of the registry; not included in v2.0.0.
- **Web-UI portfolio dashboard.** The terminal `portfolio` view + optional PNG covers the working scientist; a browser dashboard belongs in a separate spec.

---

## 14. Spec ambiguities flagged for the v2.0.0 owner

1. **Auto-register default.** This spec defaults `auto_register: true`. A reasonable case can be made for opt-in (more conservative, surprises no one) — owner to decide.
2. **`compose-from-shared` dependency.** The Example B / §4 "Suggestion" line cross-references the composition spec's `figures compose-from-shared` command. If composition ships first, full integration; if cross-project ships first, the suggestion is text-only. Owner to confirm sequencing with W1 (composition).
3. **Heatmap renderer.** The terminal heatmap uses Unicode block characters; degraded ASCII for `LANG=C` terminals is mentioned in passing but not specified in detail. Owner may want to lock down a `--ascii` flag.
