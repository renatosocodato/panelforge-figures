# panelforge-figures — Agent Recipes Walkthrough

A worked-example tutorial for agents that need to discover and render figures
from the panelforge-figures catalog. Two flows are documented side-by-side:
the **generic-CLI** flow (no filesystem, ends at a shortlist) and the
**Claude Code autonomous** flow (filesystem-aware, ends at rendered PNGs).

---

## 1. Two entry planes

panelforge-figures ships two bootstrap documents. Pick the one that matches
your runtime, not the one that sounds most interesting.

| You are… | Read | Stops at |
|---|---|---|
| A generic CLI agent (no filesystem write access, talks to the user via chat) | [`AGENT_BOOTSTRAP.md`](../AGENT_BOOTSTRAP.md) | A confirmed `{modality}.{recipe}` shortlist. The user runs the renderer. |
| Claude Code or any agent with filesystem + `figures` CLI installed | [`CLAUDE_CODE_AUTONOMOUS.md`](../CLAUDE_CODE_AUTONOMOUS.md) | A populated `figures/` directory plus `figures/RENDER_REPORT.md`. |

The two flows share the same scoring rubric ([`RECIPE_SELECTION.md`](RECIPE_SELECTION.md))
and the same index file (`recipes_index.json`). They differ in **agency**:
generic CLI agents stop short of side effects, Claude Code agents drive the
seven-step procedure all the way to rendered figures, halting only at the
two checkpoints (intake confirmation and bridge mapping confirmation).

If the autonomous flow can't satisfy its preconditions — empty project
directory, more than 2 of 8 intake fields below confidence 0.7, user passes
`--manual`, or `index_meta.tags_enabled == false` — Claude Code agents
**downgrade** to the generic flow and surface the reason. See §5 below.

---

## 2. Flow A — Generic CLI agent (`AGENT_BOOTSTRAP.md`)

The user has asked: *"Can you find me a recipe for a DISC1 biophysics figure
that shows persistence-length equivalence bounds?"*

**Step 1 — fetch the index.**

```bash
$ curl -fsSL https://raw.githubusercontent.com/<owner>/panelforge-figures/main/recipes_index.json \
       -o /tmp/recipes_index.json
$ jq '.index_meta' /tmp/recipes_index.json
{
  "built_at": "1970-01-01T00:00:00Z",
  "git_commit": "committed",
  "n_modalities": 20,
  "n_recipes": 448,
  "panelforge_version": "1.0.0",
  "schema_version": "1.0.0",
  "tags_enabled": true
}
```

`tags_enabled: true` confirms the index carries Wave-2/3 tag and rubric
blocks. Validate against the schema:

```bash
$ curl -fsSL https://raw.githubusercontent.com/<owner>/panelforge-figures/main/docs/recipes_index.schema.json \
       -o /tmp/index_schema.json
$ python -c "import json, jsonschema; jsonschema.validate(
    json.load(open('/tmp/recipes_index.json')),
    json.load(open('/tmp/index_schema.json')))"
```

**Step 2 — locate candidate recipes.** The user mentioned *DISC1*,
*biophysics*, and *equivalence bounds*, so filter by modality and the
`tags.equivalence` boolean:

```bash
$ jq '.modalities[] | select(.name == "biophysics_scaling")
        | .recipes[] | select(.tags.equivalence == true)
        | {name, family, answers_question}' /tmp/recipes_index.json
{
  "name": "censoring_mode_waterfall_cascade",
  "family": "waterfall",
  "answers_question": "..."
}
{
  "name": "compartment_paired_delta_scatter",
  "family": "coef_forest",
  "answers_question": "..."
}
{
  "name": "equivalence_forest_with_tost_bounds",
  "family": "coef_forest",
  "answers_question": "..."
}
{
  "name": "persistence_length_lp_with_equivalence_bounds",
  "family": "split_violin",
  "answers_question": "Across compartments, does the polymer persistence length Lp lie inside the pre-registered equivalence zone (null-accepting invariance) or outside it?"
}
```

The fourth match is the obvious hit — its `answers_question` mentions
persistence length and equivalence zones in one sentence.

**Step 3 — present the shortlist.** Surface the candidates and **wait for
explicit confirmation**:

```
Shortlist for "DISC1 biophysics persistence-length equivalence":

  [1] biophysics_scaling.persistence_length_lp_with_equivalence_bounds
      family: split_violin
      answers: persistence length Lp inside the equivalence zone?

  [2] biophysics_scaling.equivalence_forest_with_tost_bounds
      family: coef_forest
      answers: TOST-bounded equivalence claims, all-conditions forest

Pick one or more (1, 2, 1+2, or "none of these")?
```

The user replies `1`. **Generic-CLI agents stop here.** The user is
expected to either install panelforge-figures locally and render the
recipe themselves, or hand the shortlist to a Claude Code session that
will continue from step 4 onward.

**Step 4 — sparse-checkout (if and only if the user has filesystem
access).**

```bash
$ git clone --filter=blob:none --no-checkout https://github.com/<owner>/panelforge-figures .
$ git sparse-checkout init --cone
$ git sparse-checkout set src/panelforge_figures/core \
                          src/panelforge_figures/recipes/biophysics_scaling
$ git checkout main
$ pip install -e .
$ figures show-recipe persistence_length_lp_with_equivalence_bounds
```

That's the complete generic-CLI flow: **fetch → filter → confirm → hand
off**. No side effects on the user's project until they confirm.

---

## 3. Flow B — Claude Code autonomous (`CLAUDE_CODE_AUTONOMOUS.md`)

The user says: *"Render the figures for my DISC1 manuscript."*

Their project layout:

```
my_disc1_paper/
├── manuscript.tex
├── methods.md
├── README.md
├── data/
│   ├── persistence_length.csv
│   ├── compartment_metadata.csv
│   └── README.md
└── figures/                 # empty — to be populated
```

**Step 1 — fetch resources** (same as Flow A; cache to local TTL).

**Step 2 — scan the project.**

```bash
$ figures profile scan --project-root .
[inferred]      manuscript_anchor    = "DISC1"     conf=1.00   (manuscript.tex \\title{}, README.md, methods.md ×3)
[inferred]      factorial_design     = False       conf=1.00   (no 2x2 keywords across corpus)
[inferred]      equivalence_claims   = True        conf=0.92   (TOST in methods.md, equivalence-zone in manuscript.tex)
[inferred]      dynamics_needed      = "static"    conf=0.85   (no kymograph / live-imaging vocabulary)
[inferred]      dimensionality       = "mixed"     conf=0.71   (z_um in CSV header, 2D figures in methods)
[inferred]      modalities_in_scope  = ["biophysics_scaling", "actin_microtubule_morphometry"]   conf=0.78
[asking]        hard_filters                                    conf=0.30   (insufficient signal — prompt user)
[inferred]      shortlist_size       = 12          conf=1.00   (default)

✓ scan written to panelforge_workspace/profile.json (partial)
  6 of 8 fields auto-filled at conf ≥ 0.70; 2 fields will prompt during intake
```

**Step 3 — intake (CHECKPOINT 1).**

```bash
$ figures intake
[auto] manuscript_anchor   = DISC1
[auto] factorial_design    = False
[auto] equivalence_claims  = True
[auto] dynamics_needed     = static
[auto] dimensionality      = mixed
[auto] modalities_in_scope = biophysics_scaling, actin_microtubule_morphometry
Hard filters — any required? (compartment_aware, scale_aware, factorial_only) [empty]:
> compartment_aware
[auto] shortlist_size      = 12

Profile:
  anchor=DISC1  factorial=False  equivalence=True  dynamics=static
  dim=mixed  modalities=[biophysics_scaling, actin_microtubule_morphometry]
  hard_filters={compartment_aware: True}  shortlist_size=12

Confirm? [Y/n]: y
✓ profile written to panelforge_workspace/profile.json
```

**Step 4 — score and sparse-checkout.** The shortlist drops out of the
scorer; recipes from two modalities mean a sparse checkout is worthwhile:

```bash
$ figures score --profile panelforge_workspace/profile.json
Shortlist (12 recipes, scores 0.565 → 0.435):
  0.565  biophysics_scaling.compartment_paired_delta_scatter
  0.565  biophysics_scaling.hierarchical_effect_size_ladder
  0.565  biophysics_scaling.persistence_length_lp_with_equivalence_bounds
  0.515  actin_microtubule_morphometry.colocalization_raincloud_per_metric
  0.500  biophysics_scaling.equivalence_forest_with_tost_bounds
  ...

# 2 modalities → sparse-checkout, not full clone (~15 MB).
$ git clone --filter=blob:none --no-checkout <repo> _checkout/
$ cd _checkout && git sparse-checkout init --cone \
  && git sparse-checkout set src/panelforge_figures/core \
                             src/panelforge_figures/recipes/biophysics_scaling \
                             src/panelforge_figures/recipes/actin_microtubule_morphometry \
  && git checkout main && pip install -e .
```

**Step 5 — data-bridge (CHECKPOINT 2).**

```bash
$ figures bridge
recipe.field                                   ←  data column            confidence  pass
─────────────────────────────────────────────────────────────────────────────────────────
contract.lp_by_group_and_compartment           ←  persistence_length.csv 1.00        exact
contract.compartment                           ←  compartment            1.00        exact
contract.tost.lower                            ←  tost_lower             0.83        fuzzy
contract.tost.upper                            ←  tost_upper             0.83        fuzzy
contract.group                                 ←  genotype               0.71        llm  (anthropic)
... (54 more rows)

Confirm mapping? [Y/n]: y
✓ bindings cached to panelforge_workspace/data_bridge_cache.json
```

**Step 6 — render loop.**

```bash
$ figures generate
rendering 12/12 recipes...
  ✓ biophysics_scaling.compartment_paired_delta_scatter        → figures/01_paired_delta.png
  ✓ biophysics_scaling.hierarchical_effect_size_ladder         → figures/02_ladder.png
  ✓ biophysics_scaling.persistence_length_lp_with_equivalence_bounds  → figures/03_lp.png
  ✓ actin_microtubule_morphometry.colocalization_raincloud_per_metric → figures/04_raincloud.png
  ✗ biophysics_scaling.scaling_exponent_ci_forest              ContractError: missing tost.delta_ref
  ... (7 more ✓)

✓ rendered 11/12 recipes; see figures/RENDER_REPORT.md
```

**Step 7 — render report.** A markdown summary of every recipe attempt
(status, contract fields filled, source columns consumed, traceback on
failure) lands at `figures/RENDER_REPORT.md`.

End-to-end: scan, intake, score, bridge, render, report. Two checkpoints,
zero blind side effects on the user's project.

---

## 4. Common patterns

### 4.1 Filter by anchor only

When you want every DISC1-anchored recipe regardless of other dimensions:

```bash
$ jq -r '.modalities[] | .name as $m | .recipes[]
         | select(.tags.anchor == "DISC1") | "\($m).\(.name)"' \
     /tmp/recipes_index.json
actin_microtubule_morphometry.actin_mt_angle_rose_with_distance_inset
actin_microtubule_morphometry.airyscan_to_zone_territory_triptych
actin_microtubule_morphometry.colocalization_raincloud_per_metric
... (rest of DISC1-tagged recipes)
```

### 4.2 Find equivalence-aware recipes for TOST claims

```bash
$ jq -r '.modalities[] | .name as $m | .recipes[]
         | select(.tags.equivalence == true) | "\($m).\(.name)"' \
     /tmp/recipes_index.json
actin_microtubule_morphometry.colocalization_raincloud_per_metric
biophysics_scaling.censoring_mode_waterfall_cascade
biophysics_scaling.compartment_paired_delta_scatter
biophysics_scaling.equivalence_forest_with_tost_bounds
biophysics_scaling.persistence_length_lp_with_equivalence_bounds
intravital_imaging.equivalence_tost_radar_per_condition
```

These are the recipes that natively render TOST bounds — they earn the
full 0.25 equivalence weight when your profile has `equivalence_claims:
true`.

### 4.3 Force include or exclude via CLI flags

```bash
# Pin a specific recipe at the bottom of the shortlist regardless of score.
$ figures intake \
    --include biophysics_scaling.equivalence_forest_with_tost_bounds

# Drop a recipe even if it scores above threshold.
$ figures intake \
    --exclude biophysics_scaling.compartment_paired_delta_scatter
```

Forced includes are tagged `[forced-include]` in the audit log so the
override is visible downstream.

### 4.4 Override locked weights (power users only)

```bash
# Treat dimensionality as load-bearing for a 3D-only paper; demote anchor.
$ figures intake \
    --weights factorial=0.25,equivalence=0.20,anchor=0.10,dynamics=0.15,dimensionality=0.30
```

Custom weights must sum to ≤ 1.0; the CLI rejects sets that exceed 1.0.
The override is stamped into `discovery_log` so reviewers can replay the
shortlist.

---

## 5. Failure modes and recovery

| # | Symptom | Cause | Recovery |
|---|---|---|---|
| 1 | `figures intake` returns an empty shortlist. | Profile has no anchor, no factorial flag, no equivalence flag — top score below the 0.40 threshold (see [`RECIPE_SELECTION.md`](RECIPE_SELECTION.md) §4.3, generic example: total **0.245**). | Commit to at least one heavy-weight signal — set `manuscript_anchor`, `factorial_design`, or `equivalence_claims`. Or browse manually: `figures catalog --by modality`. |
| 2 | Hard filter drops 89 of 100 candidates. | `compartment_aware: True` (or similar) is too narrow for the chosen modalities. | Surface the per-filter drop count, ask the user to relax: `figures intake` → answer hard-filters as empty. |
| 3 | Pass-3 LLM bridge skipped, fields unmapped. | `ANTHROPIC_API_KEY` not set, or `panelforge-figures[claude-autonomous]` extras not installed. | Either install extras and export the key, or accept the unmapped-fields list and rename CSV columns to match the contract field names exactly. Before enabling Pass-3, review what is sent to Anthropic — see the [Privacy & data handling](../CLAUDE_CODE_AUTONOMOUS.md#privacy--data-handling-pass-3-llm) section in `CLAUDE_CODE_AUTONOMOUS.md`. |
| 4 | Index URL unreachable. | GitHub raw outage, or the URL was malformed. | Fall back to the package's own catalog: `pip install panelforge-figures && figures catalog --json`. |
| 5 | Autonomy aborted: "More than 2 of 8 intake fields below confidence 0.7." | Project directory is sparse (no manuscript, no methods, no README). | Expected behaviour — Claude Code downgrades to the generic-CLI flow. Either populate the project (write a 1-paragraph `README.md` mentioning the anchor, modalities, and design properties) or run `figures intake` without `figures profile scan` to answer all eight questions interactively. |

---

## 6. See also

- [`AGENT_BOOTSTRAP.md`](../AGENT_BOOTSTRAP.md) — the generic-CLI bootstrap (Flow A above).
- [`CLAUDE_CODE_AUTONOMOUS.md`](../CLAUDE_CODE_AUTONOMOUS.md) — the autonomous bootstrap (Flow B above).
- [`RECIPE_SELECTION.md`](RECIPE_SELECTION.md) — the prose contract for the scoring rubric, with full worked examples and arithmetic.
- [`recipes_index.schema.json`](recipes_index.schema.json) — JSON-Schema for the index.
- [`recipes_by_modality.md`](recipes_by_modality.md) — human-browsable catalog grouped by modality.
- [`recipes_by_question.md`](recipes_by_question.md) — human-browsable catalog grouped by `answers_question`.
