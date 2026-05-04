# panelforge-figures — Claude Code Autonomous Bootstrap

You are a Claude Code agent. The user has filesystem access and expects you
to take action — **not stop at a shortlist**. Drive the seven steps below
end-to-end, halting only at the two confirmation checkpoints called out in
**bold** and on environmental failures.

If you are a generic CLI agent without filesystem access, read
[`AGENT_BOOTSTRAP.md`](AGENT_BOOTSTRAP.md) instead — that file ends at the
shortlist; this one continues to a rendered `figures/` directory.

---

## Step 1 — Fetch the three resources

```
GET https://raw.githubusercontent.com/<owner>/panelforge-figures/main/recipes_index.json
GET https://raw.githubusercontent.com/<owner>/panelforge-figures/main/RECIPE_SELECTION.md
GET https://raw.githubusercontent.com/<owner>/panelforge-figures/main/CLAUDE_CODE_AUTONOMOUS.md
```

Cache all three locally with a 24-hour TTL. Validate `recipes_index.json`
against `docs/recipes_index.schema.json` (also fetchable from the same raw
URL) before use. Confirm `index_meta.tags_enabled == true` and
`index_meta.scoring_rubric` is populated — both are required for Wave 3.

## Step 2 — Scan the user's project

Read the project files in priority order **without prompting the user**.
The scanner is implemented at `src/panelforge_figures/manifest/project_scan.py`
and is exposed via the `figures profile scan` CLI subcommand.

| Priority | Files (relative to user's CWD) | Confidence weight |
|---|---|---|
| 1 | `panelforge.project.yaml`, `manuscript.{md,tex}`, `methods.{md,tex}`, `README.md` | 1.0 if explicit YAML; +0.4 per keyword hit otherwise |
| 2 | `results.md`, `discussion.md`, `data/README.md`, `figures/RENDER_REPORT.md`, `*.bib` | +0.3 per corroborating signal |
| 3 | `data/*.csv` headers, `*.ipynb` markdown cells, `data/<modality>/` folder names | +0.2 to +0.5 |

`project_scan` emits one `InferredAnswer` per intake field with a
confidence in [0, 1] and a `[inferred]` / `[inferred — review]` /
`[asking]` band label. Six of the eight intake fields typically reach
confidence ≥ 0.7 on a moderately documented project; the remaining two
are forwarded to step 3 for explicit prompting.

## Step 3 — Pre-filled intake — **CHECKPOINT 1**

Run `figures intake` (Click prompts at `src/panelforge_figures/manifest/intake.py`)
and pass the scan result as the `pre_filled` argument. Every field with
confidence ≥ 0.7 skips its prompt and prints an `[auto] field = value`
line; lower-confidence fields drop into normal interactive mode.

After all eight answers settle, the intake renders the assembled YAML
profile back to the terminal and waits for `Confirm? [Y/n]`. **This is
checkpoint 1 — wait for the user's explicit confirmation before
proceeding.** A `Confirm? n` answer raises `click.Abort` and halts the
flow without writing `panelforge_workspace/profile.json`.

## Step 4 — Score and sparse-checkout

Once `profile.json` is on disk, score the 448-recipe catalog using the
locked-weight rubric at `src/panelforge_figures/manifest/scoring.py`
(weights: factorial 0.30, equivalence 0.25, anchor 0.20, dynamics 0.15,
dimensionality 0.10). Take the top `profile.shortlist_size` recipes,
collect the set of modalities they live in, and sparse-checkout only
those:

```bash
git clone --filter=blob:none --no-checkout <repo-url> .
git sparse-checkout init --cone
git sparse-checkout set src/panelforge_figures/core \
                        src/panelforge_figures/recipes/<modality_1> \
                        src/panelforge_figures/recipes/<modality_2>
git checkout main
```

If the shortlist spans 4+ modalities, do a full clone instead (the
sparse-checkout overhead exceeds the savings).

## Step 5 — Data-to-contract bridge — **CHECKPOINT 2**

The bridge module at `src/panelforge_figures/manifest/data_bridge.py`
maps the user's `data/*.csv` columns onto each shortlisted recipe's
Pydantic contract via three passes:

1. **Pass 1 — exact**: identical column-name match (case-insensitive).
2. **Pass 2 — fuzzy**: `difflib.get_close_matches` with cutoff 0.8
   (catches plural/singular drift, underscore vs space, Unicode
   substitutions like `µ ↔ u`). An alias dictionary is planned for a
   future polish wave.
3. **Pass 3 — LLM**: only fires if `ANTHROPIC_API_KEY` is set and the
   `panelforge-figures[claude-autonomous]` extras are installed.
   Otherwise the bridge gracefully degrades and reports unmapped fields
   to the user.

Mappings are cached at `panelforge_workspace/data_bridge_cache.json` so
subsequent runs are deterministic.

After the three passes, render the mapping table:

```
recipe.field          ←  data column         confidence  pass
────────────────────────────────────────────────────────────
contract.area_um2     ←  area_um2            1.00        exact
contract.compartment  ←  region              0.83        fuzzy
contract.d_effect     ←  effect_d            0.71        llm
```

Wait for `Confirm mapping? [Y/n]`. **This is checkpoint 2 — do not start
the render loop until the user confirms.** Edits ("rename foo→bar") loop
back to pass 1 with the user's overrides applied first.

## Step 6 — Render loop

Drive `figures generate` (or call `render_manifest` directly) over the
confirmed shortlist + mapping. The loop continues past per-recipe
errors — a single recipe that raises `ContractError` is logged as
`fail` in the report but does **not** abort the run. The loop halts
only on environmental failures (missing modality module, corrupt index,
matplotlib backend errors).

## Step 7 — Write `figures/RENDER_REPORT.md`

Emit a markdown report under the user's `figures/` directory listing
every attempted recipe with:

- `ok` / `fail` status,
- the contract fields that were filled,
- the source data columns consumed,
- the path to the rendered PNG / PDF (or the exception traceback on
  `fail`).

End your conversational reply with `Rendered N of M panels — see
figures/RENDER_REPORT.md.`

---

## Fall-back to AGENT_BOOTSTRAP.md

Switch to the [`AGENT_BOOTSTRAP.md`](AGENT_BOOTSTRAP.md) flow whenever
**any** of the following is true:

- The project directory is empty (no `README.md`, no `data/`, no
  `manuscript.{md,tex}`).
- More than 2 of the 8 intake fields land below confidence 0.7.
- `recipes_index.json` reports `index_meta.tags_enabled: false` (Wave 1).

In each case, surface the reason to the user once, then hand off to the
generic bootstrap.

> **Future opt-out flags.**  `--manual`, `--shortlist-only`, and the
> `panelforge.project.yaml: autonomy: false` knob are reserved but
> not yet wired.  When implemented, they'll join the fall-back
> triggers above.

---

## CLI surface

| Step | Command | Module |
|---|---|---|
| 2 | `figures profile scan` | `manifest/project_scan.py` |
| 3 | `figures intake` | `manifest/intake.py` |
| 4-5 | `figures bridge` (scores + binds in one pass) | `manifest/scoring.py` + `manifest/data_bridge.py` |
| 6 | `figures generate` | `manifest/render_loop.py` |

> **Note.**  Scoring runs as part of `figures bridge` rather than a
> standalone `figures score` subcommand — bridge needs the shortlist
> to know which contracts to bind.  A separate `figures score` is on
> the roadmap for advanced use cases.

All commands accept their own `--out` / `--profile` / `--bindings`
path overrides.  Default cache location: `panelforge_workspace/`.
A unified `--workspace <path>` flag is on the roadmap.

---

## Environment

Pass-3 LLM mapping is optional. To enable it:

```bash
pip install 'panelforge-figures[claude-autonomous]'
export ANTHROPIC_API_KEY=sk-ant-…
```

When either is missing, the bridge skips Pass 3 and reports any
unmapped fields back to the user as part of the checkpoint-2 table.
Passes 1 and 2 always run.

---

## `panelforge.project.yaml` schema

A user can short-circuit the scan + intake by committing this file at
the project root:

```yaml
anchor: DISC1                # CDC42 | DISC1 | both | none
factorial: false
equivalence: true
modalities: [biophysics_scaling, actin_microtubule_morphometry]
shortlist_size: 12
autonomy: true               # optional; false → AGENT_BOOTSTRAP.md flow
```

Every key is optional. Keys present override the corresponding
inferred answer with confidence 1.0; keys absent leave the scanner's
inference untouched.

---

## Reference paths

- `recipes_index.json` — index file (auto-regenerated on every CI run)
- `CLAUDE_CODE_AUTONOMOUS.md` — this file
- `AGENT_BOOTSTRAP.md` — generic-agent fall-back
- `docs/recipes_index.schema.json` — JSON-Schema for the index
- `src/panelforge_figures/manifest/project_scan.py` — Step 2
- `src/panelforge_figures/manifest/intake.py` — Step 3
- `src/panelforge_figures/manifest/scoring.py` — Step 4
- `src/panelforge_figures/manifest/data_bridge.py` — Step 5
- `src/panelforge_figures/manifest/render_loop.py` — Step 6
- `src/panelforge_figures/cli.py` — `figures` Click entry point
- `tests/fixtures/sample_project/` — end-to-end test fixture

---

## Stability guarantees

`CLAUDE_CODE_AUTONOMOUS.md` follows the same contract as
`AGENT_BOOTSTRAP.md`: changes within a major version are additive only;
the seven-step procedure and the two-checkpoint contract are part of
the public surface. An agent built against
`CLAUDE_CODE_AUTONOMOUS.md@1.x` will continue to work against
`CLAUDE_CODE_AUTONOMOUS.md@1.y` for any `y > x`. Breaking changes wait
for `2.0`.

The index's `index_meta.schema_version` follows the same rule. Additive
fields do not bump the version. Pre-filled intake's confidence cutoff
(0.7) and the rubric's weight table are part of the spec — changing
either requires a major-version bump.
