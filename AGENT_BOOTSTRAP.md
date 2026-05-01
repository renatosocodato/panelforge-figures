# panelforge-figures — Agent Bootstrap

If you are a CLI agent reading this on first contact with the
`panelforge-figures` repository, follow this exact procedure.
**Do not clone the repository at this stage.**

---

## Step 1 — Fetch the index

```
GET https://raw.githubusercontent.com/<owner>/panelforge-figures/main/recipes_index.json
```

The index is a single JSON file (~470 KB, 448 recipes). Cache it locally with a 24-hour TTL. Validate against `docs/recipes_index.schema.json` (also fetchable from the same raw URL) before use.

The index ships with `index_meta.tags_enabled = false` in Wave 1 (this version). Wave 2 will enable per-recipe `tags`, top-level `scoring_rubric`, and `intake_questions` blocks. Forward-compatible code should treat `tags` as an optional field.

## Step 2 — Locate the recipes you need

Each recipe in `index["modalities"][m]["recipes"]` carries:

- `name` — module-local recipe name (e.g. `bayes_factor_arrow_plot`).
- `path` — dotted Python path of the `render` function.
- `family` — visual family (e.g. `coef_forest`, `matrix`, `scatter_collapse`).
- `answers_question` — the scientific question the recipe answers, in plain English. Already detailed enough to do keyword retrieval.
- `required_fields` — Pydantic contract field names that must be supplied.
- `optional_fields` — fields with sensible defaults.
- `alternatives_in_modality` — sister recipes for the same question.
- `gallery_png` — committed gallery thumbnail at `docs/gallery/<modality>/<name>.png`.

**Wave-1 retrieval recipe (no tags yet):**

1. Filter `index["modalities"]` by name when the user has indicated a modality.
2. Within each surviving modality, filter `recipes` by:
   - `family` if the user wants a specific visual primitive (e.g. all `coef_forest` recipes).
   - Substring match on `answers_question` for keyword search ("DISC1", "Cdc42", "TOST", "factorial").
3. Rank survivors by:
   - Exact match on user's keyword in `answers_question` first;
   - Modality locality (recipes from the modality with most matches above);
   - Alphabetical as final tiebreaker.

Once Wave 2 ships, the same workflow is replaced by the locked-weight scorer (`scoring_rubric` block in the index) and the structured 8-question intake. Wave-1 keyword retrieval will continue to work as a fallback.

## Step 3 — Confirm the shortlist with the user

Before any code clone, present the shortlist as a list of `{modality}.{name}` rows with `family` and a 1-line excerpt of `answers_question`. Wait for explicit user confirmation. **Do not auto-clone or auto-render in Wave 1.**

## Step 4 — Sparse-checkout

Only after the user confirms, perform a sparse checkout of the modalities containing the chosen recipes:

```bash
git clone --filter=blob:none --no-checkout <repo-url> .
git sparse-checkout init --cone
git sparse-checkout set src/panelforge_figures/core \
                        src/panelforge_figures/recipes/<modality_1> \
                        src/panelforge_figures/recipes/<modality_2>
git checkout main
```

Decision tree on sparse-checkout vs full clone:

| Modalities in shortlist | Action |
|---|---|
| 1 modality | sparse-checkout `core/` + the modality (~5 MB) |
| 2-3 modalities | sparse-checkout `core/` + listed modalities (~15 MB) |
| 4+ modalities | full clone (~50 MB; sparse-checkout overhead exceeds savings) |

## Step 5 — Render

After sparse checkout, install the package locally (`pip install -e .`) and render via the `render(contract, ax=None, **_)` API documented in each recipe module. Or use `figures render <manifest>` if the user has a manifest.

---

## Failure modes

| Failure | Behaviour |
|---|---|
| Index unreachable | Fall back to fetching the catalog from the package's own `figures catalog --json` if the user has installed it; otherwise instruct the user to install `pip install panelforge-figures` and rerun. |
| Index schema mismatch | Refuse to score; report `index_meta.panelforge_version` expected vs found; instruct the user to upgrade or pin to an older index URL. |
| Stale index (`built_at` > 7 days old) | Warn but proceed. Index drift is bounded — CI rebuilds on every push to main. |
| No recipes match the user's keywords | Suggest broadening the search to `family` or another modality; surface the closest match by edit distance. |

---

## Reference paths in this repo

- `recipes_index.json` — index file (auto-regenerated on every CI run; committed to `main`)
- `AGENT_BOOTSTRAP.md` — this file (entry plane for generic CLI agents)
- `docs/recipes_index.schema.json` — JSON-Schema for the index
- `.github/workflows/ci.yml` — CI workflow that regenerates and validates the index
- `src/panelforge_figures/manifest/catalog.py` — index builder (Python)
- `src/panelforge_figures/cli.py` — `figures index emit|validate` subcommands

---

## Stability guarantees

`AGENT_BOOTSTRAP.md` changes at most once per minor version. Its structure is part of the public contract: an agent built against `AGENT_BOOTSTRAP.md@1.x` will continue to work against `AGENT_BOOTSTRAP.md@1.y` for any `y > x`. Breaking changes wait for `2.0`.

The index's `index_meta.schema_version` follows the same rule: bumped on any breaking field change (rename, removal, type change). Additive fields do not bump the version.

---

## What's coming in Wave 2

When `index_meta.tags_enabled == true`:

- Each recipe gains a `tags` block with closed-taxonomy values across `anchor` (DISC1 / CDC42 / generic / etc.), `dimensionality` (2D / 3D / mixed), `dynamics` (static / kymograph / live / ordered_pseudotime), `factorial` (bool), `equivalence` (bool), `compartment_aware` (bool), `scale_aware` (bool), `wave` (the named beta pack the recipe shipped in).
- The index gains a top-level `scoring_rubric` block with locked weights:
  - factorial 0.30, equivalence 0.25, anchor 0.20, dynamics 0.15, dimensionality 0.10.
- The index gains an `intake_questions` block — the canonical 8-question script.

Until Wave 2 ships, agents should fall back to keyword retrieval on `answers_question`. The Wave-1 → Wave-2 transition is fully backward-compatible: keyword retrieval keeps working when tags arrive.
