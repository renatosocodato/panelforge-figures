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

## Privacy & data handling (Pass-3 LLM)

When Pass-3 LLM column mapping is enabled (i.e. both
`ANTHROPIC_API_KEY` is set **and** the `claude-autonomous` extra is
installed), the bridge sends the following to Anthropic's API:

**What IS sent to Anthropic:**

| Field | Example | Sourced from |
|---|---|---|
| Contract field name | `"estimates"` | recipe `_META.required_fields` |
| Field type | `"list[float]"` | Pydantic type annotation |
| Field description | `"Per-cell standardized effect sizes."` | Pydantic field's `description=` |
| Candidate column names | `"cell_id"`, `"area_um2"`, `"velocity_um_per_min"` | user's data file headers |

**What is NEVER sent to Anthropic:**

- Cell-level data values from the user's CSV/Parquet files (sample
  values are explicitly stripped — `_llm_pass` is invoked with
  `samples={}` at the only call site in `data_bridge.py`).
- The user's manuscript, methods, README, or any free-text project
  content.
- Project filesystem paths beyond the bare column names that the
  bridge needs to score.

**To opt out**: simply omit `ANTHROPIC_API_KEY` from your environment,
**or** install without the `claude-autonomous` extra (`pip install
panelforge-figures` instead of `pip install
panelforge-figures[claude-autonomous]`). Pass-1 (exact match) and
Pass-2 (fuzzy match) always run locally and never make network calls.
Recipes whose required fields are not bound by Pass-1 + Pass-2 will
surface in the checkpoint-2 mapping table for manual review.

**Data retention**: Anthropic's API retention policy applies; see
<https://www.anthropic.com/legal/privacy>. Column names are typically
short, low-entropy strings (e.g. `area_um2`, `compartment`) and are
unlikely to constitute PHI/PII unless your column-naming convention
encodes it directly (e.g. `patient_DOB_yyyymmdd`). The bridge does
not inspect column names for sensitive content — that responsibility
sits with the user.

### Vision API additions (Sprint 2C — v1.12.0)

When vision input is enabled (e.g. `figures profile scan
--reference-figure`, `figures refine`, `figures vision-explain`), the
**image bytes** are sent to Anthropic's API in addition to the field
metadata listed above. This is a *separate consent surface* from the
Pass-3 column mapping — users may opt into low-entropy column names
but opt out of high-entropy figure content.

**What IS sent to Anthropic in vision modes:**

| Field | Example | Sourced from |
|---|---|---|
| Image bytes (base64-encoded) | the reference figure or rendered PNG/JPG | `--reference-figure` argument or `figures refine <pdf>` argument |
| Image SHA-256 (cache key only, computed locally) | `9f86d081...` | local hash; not transmitted as a separate field |
| Recipe Python source code | the contents of `recipes/<modality>/<recipe>.py` | the recipe package; only sent for `figures refine` |
| User edit instruction (for `refine` only) | `"make y-axis log-scale"` | CLI argument |

**What is NEVER sent in vision modes:**

- Cell-level data values from the user's CSV/Parquet files (vision
  modes only read images and recipe Python — never data files).
- The user's manuscript, methods, README, or any other free-text
  project content.
- Project filesystem paths beyond the recipe module path.

**Cost estimates** (Claude Sonnet 4.5 with vision, late-2025 pricing):

| Mode | Approximate cost per call |
|---|---|
| `figures profile scan --reference-figure` | ~$0.012 |
| `figures refine` | ~$0.025 |
| `figures vision-explain` | ~$0.009 |

**Cache**: results are cached by image SHA-256 in
`panelforge_workspace/vision_cache/<sha[:16]>.json` so repeat calls on
the same image are free.  Override the model with the
`PANELFORGE_VISION_MODEL` env var (default: `claude-sonnet-4-5`).

**To opt out of vision modes**:

- omit the `--reference-figure` flag and the `figures refine` /
  `figures vision-explain` subcommands (text-based scan and intake
  never invoke vision), OR
- set `data_class: clinical` (forces vision OFF unconditionally — see
  `docs/spec_data_class_safety.md`), OR
- omit `ANTHROPIC_API_KEY` from your environment, OR
- install without the `claude-autonomous` extra.

### Telemetry channel (v1.13.0+)

Panelforge ships an optional usage-telemetry channel for collecting
calibration data (which recipes users actually pick out of the auto-
shortlist). Telemetry is **OFF by default** and is **never auto-
uploaded** — the package contains no upload code.

Activation: add `telemetry: opt-in` to `panelforge.project.yaml`. Once
enabled, every `figures generate` call appends a row to
`panelforge_workspace/usage.jsonl`. The user later runs
`figures pick <recipe_name>` to record which recipe they actually
chose. To export an aggregated artifact for analysis (which the user
manually transmits if they wish), run:

```
figures telemetry export ./calibration_2026q4.jsonl --anonymize
```

Even with opt-in enabled, the telemetry log contains:

- categorical profile fields (modality, factorial_design, anchor_strength, …)
- recipe `full_name` strings (e.g. `live_imaging_2d.factorial_anchor_v3`)
- numeric scores and per-tag scores

It NEVER contains:

- manuscript text (never recorded)
- CSV row contents (never recorded)
- file paths (never recorded)
- DOIs (never recorded)
- auto-uploads (never — the user always ships the file manually)

To disable on an opt-in project, change the YAML to `telemetry: off` or
delete the line. The on-disk JSONL is plain text the user can `cat`,
`grep`, or delete at any time. See `docs/spec_active_learning.md` §9 for
the full privacy considerations.

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
