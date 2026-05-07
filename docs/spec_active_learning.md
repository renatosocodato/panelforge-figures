# Spec — Active-Learning Loop (opt-in telemetry + weight calibration)

| Field        | Value                                                                  |
|--------------|------------------------------------------------------------------------|
| Status       | Draft (v2.0.0 elevation, swarm slot W6)                                |
| Owner        | TBD — assign before merge                                              |
| Branch       | `roadmap-v2-specs`                                                     |
| Target       | panelforge-figures **v1.7.0** (telemetry + tools); v1.7.1+ for re-locks |
| Depends on   | `src/panelforge_figures/manifest/scoring.py` (locked rubric v1.0.0)    |
| Supersedes   | n/a (additive)                                                         |
| Affects      | scoring API, CLI, on-disk workspace, `recipes_index.json`              |

## TL;DR

v1.6.1 ships a recipe-discovery scorer with five weights frozen by intuition
(`factorial 0.30 / equivalence 0.25 / anchor 0.20 / dynamics 0.15 /
dimensionality 0.10`). Nobody can tell whether those weights are correct
because the system never observes which recipe the user actually picks. This
spec adds a **fully opt-in, never-uploaded** telemetry channel
(`panelforge_workspace/usage.jsonl`), an offline cross-validation tool
(`figures suggest-weights`), and an explicit weights-versioning table so old
profiles can be re-scored against any historical rubric. Telemetry is OFF by
default. Nothing leaves the user's machine unless they manually run
`figures telemetry export`. Weight changes are never automatic — they require
a human to bump `SCORING_RUBRIC_VERSION` and ship a release.

---

## 1. Problem statement

The scoring rubric in `src/panelforge_figures/manifest/scoring.py` is anchored
on a `MappingProxyType` constant:

```python
WEIGHTS = MappingProxyType({
    "factorial": 0.30,
    "equivalence": 0.25,
    "anchor": 0.20,
    "dynamics": 0.15,
    "dimensionality": 0.10,
})
```

These five numbers were chosen by the spec author based on a reading of
`RECIPE_DISCOVERY_SYSTEM.md`. There is no empirical signal feeding into them.
If users systematically reject the auto-shortlist — say they always pick
the recipe ranked #4, never the recipe ranked #1 — the system has no way to
notice and no way to learn. The rubric is, in other words, a research problem
that nobody currently owns.

This spec does not attempt to solve calibration end-to-end. It does the
boring half: it (a) records the data needed to ever solve calibration, in a
schema that respects user privacy, and (b) provides a one-shot offline
analysis tool that turns aggregated logs into a weight proposal a maintainer
can manually review. Online learning, multi-armed bandits, and any kind of
cross-user telemetry server are explicitly out of scope (see §14).

## 2. Telemetry schema — `panelforge_workspace/usage.jsonl`

Format: append-only JSONL. One row per `figures generate` invocation that
produced a shortlist. Path:
`<project_root>/panelforge_workspace/usage.jsonl`. No rotation, no compression,
no checksum — this is plain text the user can `cat`, `grep`, and delete.

Row schema (every field required):

```json
{
  "session_id": "8c2a-…-uuid4",
  "timestamp": "2026-05-04T15:32:00Z",
  "panelforge_version": "1.6.1",
  "scoring_rubric_version": "1.0.0",
  "profile": {
    "modality": "live_imaging_2d",
    "factorial_design": "2x2_factorial",
    "equivalence_present": true,
    "anchor_strength": "established",
    "dynamics_kind": "time_lapse",
    "dimensionality": "2d",
    "shortlist_size": 12
  },
  "scored_top_5": [
    {"full_name": "live_imaging_2d.factorial_anchor_v3",
     "score": 0.685,
     "tags": {"factorial": 1.0, "equivalence": 1.0, "anchor": 0.5,
              "dynamics": 0.5, "dimensionality": 1.0}},
    {"full_name": "live_imaging_2d.equivalence_companion_v1",
     "score": 0.640, "tags": {…}}
  ],
  "user_picked": "live_imaging_2d.equivalence_companion_v1",
  "rejected_higher_scored": ["live_imaging_2d.factorial_anchor_v3"]
}
```

Rules:

- `profile` mirrors `ProjectProfile` field-for-field but only the categorical
  inferences — never raw `manuscript.md` text, never CSV headers, never DOIs.
- `scored_top_5` is exactly the top five rows of the funnel output (truncated
  if the shortlist is smaller). The full 12-row shortlist is too noisy and
  blows up the file size.
- `user_picked` is set by an explicit follow-up command:
  `figures pick <full_name>` (added to the existing `figures` CLI). Without
  a pick, the row stays in `usage.jsonl` with `user_picked: null` and is
  ignored by `suggest-weights`.
- `rejected_higher_scored` is computed at pick time as `[r.full_name for r in
  scored_top_5 if r.score > picked.score]`. It is the calibration signal.

## 3. Opt-in mechanism

Default: **OFF**. A vanilla install of panelforge-figures writes nothing to
`usage.jsonl` regardless of how many `figures generate` calls happen.

Activation: the user adds the following line to
`<project_root>/panelforge.project.yaml`:

```yaml
telemetry: opt-in
```

This is the only mechanism. No environment variable, no `--telemetry` CLI
flag (we want the choice to be persistent and visible in version control),
no global config file. A project that opts in but is then cloned by a
collaborator who does not touch the YAML will continue to log; this is
the correct behaviour because the YAML is the project-level record of
consent.

Three new CLI commands (added to `src/panelforge_figures/cli.py`):

```bash
figures telemetry status         # prints "off" or "opt-in" + path to log
figures telemetry export <path>  # writes a sanitized aggregated JSONL artifact
figures pick <full_name>         # records user_picked into the most recent row
```

`figures telemetry status` reads `panelforge.project.yaml`, prints one of:

```
telemetry: off (default — no rows written)
telemetry: opt-in (writing to /…/panelforge_workspace/usage.jsonl, 47 rows)
```

`figures telemetry export <path>` reads `usage.jsonl`, drops rows where
`user_picked` is null, optionally hashes `session_id` (CLI flag
`--anonymize`, default true), and writes the result as a single JSONL file
the user can ship to the panelforge maintainers if they wish. **No upload
is automatic.** The user does the shipping (email, PR, dropbox, whatever).

## 4. Cross-validation procedure

Input: an aggregated JSONL — concatenation of N opted-in users' exported
files. The aggregator (`figures suggest-weights`) treats each row independently;
it does not need to know who produced it.

Procedure:

1. Filter rows: keep only those with non-null `user_picked` and at least one
   entry in `rejected_higher_scored` (rows where the user picked the top
   recipe carry no calibration signal — `rejected_higher_scored` is empty).
2. Holdout split: shuffle with `random.Random(42)` (deterministic), 80% train,
   20% test.
3. Grid-search over weights: perturb each of the five locked weights by
   `{-0.05, 0.0, +0.05}`, re-normalize so the five sum to 1.0, and discard
   any vector whose minimum entry is < 0.05 (we never want a weight to vanish
   by accident). For five dims and three perturbations, that is 3⁵ = 243
   raw candidates, dropping to ~120 after the floor and renorm — small
   enough to brute-force.
4. For each candidate, re-score every test row using
   `score_recipes(profile, recipes, weights_version=<candidate>)` and count
   the fraction of rows whose `user_picked` lands in the predicted top 3.
5. Output: the candidate with the highest top-3 hit rate, plus its hit rate
   minus the locked-weights hit rate ("uplift").

The grid is intentionally narrow (`±0.05`). The system is not searching for
a global optimum — it is checking whether locked weights are obviously
miscalibrated. Larger jumps require a fresh design decision from the
maintainer, not a grid search.

## 5. `figures suggest-weights` CLI

```bash
figures suggest-weights --aggregate-from teams/usage.jsonl \
                        --output suggested_weights.json \
                        [--seed 42]
```

Output (`suggested_weights.json`):

```json
{
  "n_rows": 1024,
  "n_train": 819,
  "n_test": 205,
  "current_weights_version": "1.0.0",
  "current_weights": {"factorial": 0.30, "equivalence": 0.25,
                      "anchor": 0.20, "dynamics": 0.15,
                      "dimensionality": 0.10},
  "current_top3_hit_rate": 0.731,
  "suggested_weights": {"factorial": 0.32, "equivalence": 0.23,
                        "anchor": 0.20, "dynamics": 0.15,
                        "dimensionality": 0.10},
  "suggested_top3_hit_rate": 0.769,
  "uplift": 0.038,
  "seed": 42
}
```

A maintainer reads this file, decides whether the uplift justifies a release,
and — if yes — manually adds an entry to `WEIGHTS_HISTORY` with a new
`SCORING_RUBRIC_VERSION` and bumps the panelforge-figures package version.
**The CLI never edits source files.** This is a one-way handoff from
analysis to a human-authored release.

## 6. Weights versioning

Add to `src/panelforge_figures/manifest/scoring.py`:

```python
WEIGHTS_HISTORY: dict[str, Mapping[str, float]] = {
    "1.0.0": MappingProxyType({"factorial": 0.30, "equivalence": 0.25,
                               "anchor": 0.20, "dynamics": 0.15,
                               "dimensionality": 0.10}),
}
SCORING_RUBRIC_VERSION = "1.0.0"   # current default

def score_recipes(profile, recipes, *, weights_version: str = SCORING_RUBRIC_VERSION):
    weights = WEIGHTS_HISTORY[weights_version]
    …
```

`score_recipes` becomes a kwarg-only override. All v1.6.x callers pass no
kwarg and behave identically.

`recipes_index.json` already includes a `scoring_rubric` block; extend it:

```json
"scoring_rubric": {
  "version": "1.0.0",
  "weights_history_versions": ["1.0.0"],
  …
}
```

When v1.7.0 ships with `WEIGHTS_HISTORY = {"1.0.0": …, "1.1.0": …}` and
`SCORING_RUBRIC_VERSION = "1.1.0"`, old profiles can replay against `1.0.0`
via:

```bash
figures suggest --weights-version 1.0.0
```

## 7. CLI surface (additions)

Inserted into `src/panelforge_figures/cli.py` as new subcommand groups:

| Command                                  | Effect                                                           |
|------------------------------------------|------------------------------------------------------------------|
| `figures telemetry status`               | Print on/off + log location + row count                          |
| `figures telemetry export <out>`         | Write sanitized aggregated JSONL artifact                        |
| `figures pick <full_name>`               | Set `user_picked` on the most recent row in `usage.jsonl`        |
| `figures suggest --weights-version <v>`  | Replay shortlist against historical weights                      |
| `figures suggest-weights --aggregate-from <in> --output <out>` | Cross-validate, propose new weights      |

## 8. Worked examples

### Example A — fleet calibration → small adjustment → v1.7.0 release

A working group of fifty live-imaging labs all opt in
(`telemetry: opt-in`). After three months they each run
`figures telemetry export team_<lab>.jsonl` and email the file to the
maintainers. The maintainer concatenates the files (≈1000 rows total) and
runs:

```
figures suggest-weights --aggregate-from teams_combined.jsonl \
                        --output suggested_weights_2026q3.json
```

The output reports a 3.8-point uplift moving factorial from 0.30 to 0.32 and
equivalence from 0.25 to 0.23 (other three unchanged). The maintainer
opens a PR that adds `"1.1.0"` to `WEIGHTS_HISTORY`, sets
`SCORING_RUBRIC_VERSION = "1.1.0"`, regenerates `recipes_index.json`, and
ships **panelforge-figures v1.7.0**. Old profiles continue to score
identically against v1.0.0; new shortlists prefer factorials slightly more
strongly.

### Example B — replay an old profile against current weights

A user wrote a `panelforge.project.yaml` six months ago, before v1.7.0
shipped. They want to know whether the new rubric would have reordered
their shortlist. They run:

```
figures suggest --weights-version 1.0.0   # baseline (matches old shortlist)
figures suggest --weights-version 1.1.0   # current (default — same as no flag)
```

The two outputs are diffable: the user can see exactly which recipes moved
up and down between rubric versions. No telemetry was needed for this; it
relies only on `WEIGHTS_HISTORY` and the existing scoring path.

### Example C — telemetry off (the default path)

A new project sets nothing — or explicitly writes `telemetry: off` in
`panelforge.project.yaml`. Every `figures generate` call works as it does
today. No file is created in `panelforge_workspace/`, no row appears
anywhere, no network call happens, no warning is emitted. `figures
telemetry status` prints `telemetry: off (default — no rows written)`. The
behaviour of the figure-generation pipeline is byte-identical to a
v1.6.1-era install.

## 9. Privacy considerations

- Telemetry **never leaves the user's machine** unless they explicitly run
  `figures telemetry export <path>` and then manually transmit the resulting
  file. The package contains no upload code.
- Even with opt-in enabled, **no source data values are recorded**. The log
  captures only (a) the categorical fields of `ProjectProfile` (modality,
  factorial-design type, anchor strength, etc. — all enums or booleans),
  (b) recipe `full_name` strings, (c) numeric scores, and (d) tag scores
  per recipe. Manuscript text, CSV row contents, file paths, and DOIs are
  never written.
- `session_id` is a fresh UUIDv4 generated per `figures generate` call. It
  is not derived from username, hostname, or any persistent identifier.
- `figures telemetry export --anonymize` (default true) replaces
  `session_id` with `sha256(session_id)[:16]` to make cross-row joining by
  third parties harder.
- The privacy disclosure in `CLAUDE_CODE_AUTONOMOUS.md` (added in
  `ebc3c7f`) is extended with a paragraph stating the telemetry channel is
  opt-in, never auto-uploaded, and contains no source data values. The
  `README.md` features a one-line summary linking to this section.

## 10. Files to create / modify

| Path | Status | LOC est. | Purpose |
|------|--------|----------|---------|
| `src/panelforge_figures/manifest/telemetry.py`        | NEW  | ~200 | JSONL writer, opt-in resolver, `pick` resolver, exporter |
| `src/panelforge_figures/manifest/weight_calibration.py` | NEW  | ~250 | row loader, train/test split, grid search, output writer |
| `src/panelforge_figures/manifest/scoring.py`          | EDIT | +30  | add `WEIGHTS_HISTORY`, `weights_version` kwarg          |
| `src/panelforge_figures/cli.py`                       | EDIT | +120 | `telemetry`, `pick`, `suggest-weights` subcommands       |
| `tests/test_telemetry.py`                              | NEW  | ~150 | opt-in/out, schema, pick semantics, export sanitization  |
| `tests/test_weight_calibration.py`                     | NEW  | ~200 | synthetic 1000-row dataset, deterministic suggest output |
| `CLAUDE_CODE_AUTONOMOUS.md`                            | EDIT | +30  | privacy disclosure paragraph                              |
| `README.md`                                            | EDIT | +5   | one-line link to privacy section                          |
| `recipes_index.schema.json`                            | EDIT | +5   | optional `weights_history_versions` array                 |

## 11. Test surface

- **opt-out by default** — invoke `figures generate` against a fixture project
  with no `telemetry:` key in `panelforge.project.yaml`; assert
  `panelforge_workspace/usage.jsonl` does not exist after the call.
- **opt-in writes correct schema** — flip the YAML to `telemetry: opt-in`,
  run `figures generate`, assert exactly one row exists, validate it
  field-for-field against the §2 schema (every required key present, types
  correct, `user_picked` is `null` initially).
- **`pick` semantics** — call `figures pick <full_name>` against the most
  recent row, assert `user_picked` is now set and `rejected_higher_scored`
  is computed correctly from the previously stored top-5.
- **`suggest-weights` deterministic output** — generate a synthetic 1000-row
  `usage.jsonl` from a known scoring fixture (using a known "true" weight
  vector), invoke `suggest-weights --seed 42`, assert the output matches a
  golden JSON snapshot byte-for-byte.
- **`suggest-weights` recovers the planted vector** — when synthetic rows
  are generated using factorial=0.40, the grid search returns a vector
  with factorial ≥ 0.35.
- **weights versioning** — score the same profile with `weights_version=1.0.0`
  twice; the two shortlists are identical. With a synthetic v1.1.0 added to
  `WEIGHTS_HISTORY`, the v1.0.0 shortlist remains stable.
- **export sanitization** — call `figures telemetry export out.jsonl
  --anonymize`, assert no raw UUIDs appear in `out.jsonl` and every row's
  `session_id` matches `^[0-9a-f]{16}$`.
- **`pick` with no row** — calling `figures pick X` against a fresh
  workspace raises a friendly `UsageError`, not a stack trace.

## 12. Risks and mitigations

| Risk | Mitigation |
|------|-----------|
| Users distrust telemetry as a category | Default off; opt-in via VCS-tracked YAML; never-uploaded by package; §9 disclosure; no env-var override that could be set by a hidden parent process |
| Adversarial users inflate their own preferences | `suggest-weights` requires ≥10 distinct sessions per `(modality, factorial_design)` profile signature before that signature contributes; otherwise the row is dropped (counted but not weighted in the grid search) |
| Scoring rubric changes silently break old worked examples | `WEIGHTS_HISTORY` is append-only; `--weights-version` exposes every historical rubric; recipe-pack trackers in `docs/` cite a `weights_version` alongside any score they quote |
| `usage.jsonl` grows unboundedly | Documented as user-managed plain-text — the user can rotate it, truncate it, or delete it at any time. We deliberately do not auto-rotate (auto-rotation has a deletion semantics that surprises users) |
| Schema drift between panelforge versions | Each row stamps `panelforge_version` and `scoring_rubric_version`; `weight_calibration.py` rejects rows whose `scoring_rubric_version` is unknown to its `WEIGHTS_HISTORY`, with a clear error |
| Pick command picks the wrong row (race when running parallel sessions) | `figures pick` requires `--session-id` if more than one row in the last hour has `user_picked: null`; otherwise picks the unique candidate |

## 13. Acceptance criteria

1. Vanilla install — no YAML changes — produces no telemetry artifact, even
   after 100 `figures generate` calls. Verified by `tests/test_telemetry.py`.
2. `telemetry: opt-in` produces one schema-valid row per generate call,
   verified against the §2 JSON schema.
3. `figures suggest-weights` against a synthetic 1000-row dataset returns
   deterministic JSON output matching a golden snapshot under `--seed 42`.
4. `figures suggest --weights-version 1.0.0` reproduces the v1.6.1 shortlist
   for every fixture profile checked into `tests/`.
5. `figures telemetry export` produces a JSONL artifact that re-loads under
   `figures suggest-weights --aggregate-from` without errors.
6. The privacy section of `CLAUDE_CODE_AUTONOMOUS.md` is extended with the
   paragraph specified in §9, reviewed and approved by the spec author.
7. `WEIGHTS_HISTORY` is exported from `panelforge_figures.manifest.scoring`
   and tested for monotonicity (no version is ever removed).

## 14. Out of scope

- Online learning. We do not update weights automatically at any frequency.
- Multi-armed bandit exploration during scoring. The funnel remains
  deterministic.
- A cross-user telemetry aggregation server. Aggregation is offline,
  user-initiated, file-based.
- Per-user weight personalization. The rubric is a single global object;
  per-user variants would fragment recipe-pack trackers and recipe-discovery
  reproducibility.
- Free-text feedback. The pick command records a single recipe name; a
  rationale field invites freeform user data we have promised not to store.
- Automatic schema migration of old `usage.jsonl` rows when `WEIGHTS_HISTORY`
  changes. Old rows are kept verbatim; the calibration tool refuses
  unknown versions with a clear error and the user manually re-exports.
