# Spec: Provenance Chain (`figures provenance`)

**Status:** Draft v1 — executable scope for v2.0.0 elevation
**Owner:** Reproducibility track
**Targets:** `panelforge-figures` v2.0.0
**Companion specs:** `spec_recipe_versioning.md`, `spec_audit_rules.md`,
`spec_rendering_environment.md`

---

## TL;DR

Every rendered figure (`figures generate`) writes a sidecar
`<figure>.provenance.json` next to the PDF/PNG. The sidecar
content-addresses the figure back to (a) its source data files, (b) the
recipe module that produced it, (c) the scorer state that selected it,
and (d) the rendering environment.

A new CLI verb — `figures provenance {show,verify,bundle,diff}` —
operates on these sidecars. `verify` recomputes every hash and re-runs
the recipe; if any byte of input changed (data, recipe, scorer weights,
panelforge version), the verifier flags exactly which dimension drifted.
For manuscripts, `bundle` produces a self-contained tarball that any
reviewer can re-render bit-identical on a fresh checkout.

This is the missing audit trail between the published PDF and the
science. It is the foundation for "click here to reproduce this figure"
in supplements.

---

## 1. Why now

v1.6.1 ships rendered PDFs as flat artifacts. When a reviewer (or, three
years from now, the lab member who inherited the project) asks *"how
was Figure 3B made?"*, the answer today is a chain of tribal knowledge:
which CSV, which column mapping, which recipe revision, which scorer
weights, which matplotlib version. None of that lives next to the PDF.

The reproducibility crisis in computational biology is largely a
provenance crisis. Recent surveys put the fraction of published
computational figures that can be re-run from supplied artifacts at
under 30%. Most of the loss is not in algorithms — it's in the
undocumented linkage between a figure file and the inputs that produced
it. `panelforge-figures` already has a deterministic recipe registry, a
typed contract, and a scorer; we have every piece of metadata required.
We have not, until now, written it down next to the figure.

The provenance chain closes that gap. It does not change *how* figures
are rendered. It records *what* was rendered and lets anyone confirm it.

---

## 2. Provenance JSON schema

### 2.1. Canonical example

```json
{
  "schema_version": "1.0.0",
  "figure_path": "figures/figure_03_panel_A.pdf",
  "figure_sha256": "f7a9c32b...e1",
  "rendered_at": "2026-05-04T15:32:00Z",
  "recipe": {
    "full_name": "actin_microtubule_morphometry.compartment_paired_delta_scatter",
    "module_sha": "8b1f2c9a...",
    "panelforge_version": "2.0.0",
    "panelforge_git_commit": "aa31f80c...",
    "module_path": "src/panelforge_figures/recipes/actin_microtubule_morphometry/compartment_paired_delta_scatter.py"
  },
  "data": {
    "sources": [
      {
        "path": "data/effect_sizes.csv",
        "sha256": "11d4e7b9...",
        "n_rows": 30,
        "format": "csv",
        "size_bytes": 4096
      }
    ],
    "column_mapping": {
      "feature": "feature_name",
      "d": "cohen_d",
      "ci_low": "ci_low_95",
      "ci_high": "ci_high_95"
    }
  },
  "scorer": {
    "version": "1.0.0",
    "weights": {
      "factorial": 0.30,
      "equivalence": 0.25,
      "anchor": 0.20,
      "dynamics": 0.15,
      "dimensionality": 0.10
    },
    "score": 0.565,
    "tied_with": ["actin_mt.X", "biophysics.Y"],
    "profile": {
      "manuscript_anchor": "DISC1",
      "factorial_design": false,
      "longitudinal": true,
      "n_observations": 30
    }
  },
  "audit": {
    "rules_passed": ["n_at_least_10", "normality_p_gt_0.05", "ci_provided"],
    "rules_warned": [],
    "rules_failed": []
  },
  "rendering_environment": {
    "python_version": "3.12.4",
    "matplotlib_version": "3.9.0",
    "numpy_version": "2.0.1",
    "panelforge_version": "2.0.0",
    "platform": "darwin",
    "panelforge_workspace": "panelforge_workspace/",
    "font_cache_sha256": "3a8c1f...",
    "rng_seed": 42,
    "deterministic": true
  }
}
```

### 2.2. Field semantics

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | Semver. v2.0.0 ships `"1.0.0"`. |
| `figure_path` | yes | Repo-relative; never absolute (privacy). |
| `figure_sha256` | yes | sha256 of the PDF byte stream. |
| `rendered_at` | yes | ISO-8601 UTC. Set to `"1970-01-01T00:00:00Z"` when `--committed` flag is set (see §7). |
| `recipe.module_sha` | yes | git blob sha of the recipe `.py` file *as committed*; falls back to a sha256 of the bytes if outside a git tree. |
| `recipe.panelforge_git_commit` | yes | git HEAD sha; `"uncommitted"` if dirty tree. |
| `data.sources[].sha256` | yes | sha256 of the file bytes (not parsed contents). |
| `data.column_mapping` | yes | Verbatim from the binding (intake → render_loop). |
| `scorer.score` | yes | The scorer score that selected this recipe in the most recent shortlist. `null` if the recipe was rendered standalone (`figures render <name>`). |
| `audit.*` | yes | List of audit rule IDs (see `spec_audit_rules.md`). |
| `rendering_environment.deterministic` | yes | `true` iff the recipe declares `_demo` deterministic and seed is fixed. See §7. |

The full schema lives at `docs/provenance.schema.json` (JSON-Schema
draft 2020-12) and is enforced on read by `provenance verify`.

---

## 3. CLI surface

All commands are subcommands of a new top-level group:

```
figures provenance show <figure.pdf>
figures provenance verify <figure.pdf> [--strict] [--ignore-env]
figures provenance bundle <figure.pdf> [-o <out.tar.gz>]
figures provenance diff <a.pdf> <b.pdf> [--json]
```

### 3.1. `show`

Pretty-prints the sidecar with section headers and human-readable
hashes (first 12 chars + ellipsis). Exit 0 on success, exit 2 if
sidecar missing.

### 3.2. `verify`

The core operation. Steps:

1. Load `<figure>.provenance.json`; schema-validate.
2. Recompute `figure_sha256` from the PDF on disk → compare.
3. Recompute every `data.sources[].sha256` → compare.
4. Recompute `recipe.module_sha` → compare.
5. Compare `panelforge_version` to currently installed → flag drift.
6. Re-import the recipe, re-run with the same column mapping and the
   data files (now verified by hash), produce a *fresh* PDF in
   `/tmp/<figure>.verify.pdf`, sha256 it, compare to original.

Output is a structured report: each of the six checks gets ✓ / ✗ /
⚠. Exit 0 only if all are ✓. With `--strict`, environment drift
(matplotlib version, platform) becomes ✗ instead of ⚠.

`--ignore-env` collapses environment differences to ⚠, useful when a
reviewer is on a different platform.

### 3.3. `bundle`

Produces a `.tar.gz` containing:

```
bundle/
  figure.pdf
  figure.provenance.json
  recipe/
    actin_microtubule_morphometry/
      __init__.py
      _aesthetic.py
      compartment_paired_delta_scatter.py
  data/
    effect_sizes.csv
  README.md   # auto-generated: how to re-render
  requirements.txt   # frozen pip list
```

Bundle is self-contained: anyone with a Python 3.12 + matplotlib stack
and `pip install panelforge-figures==<exact_version>` can run

```
figures provenance verify bundle/figure.pdf
```

inside the unpacked tarball and recover bit-identical output.

### 3.4. `diff`

Loads both sidecars, structurally diffs them, and reports drift by
dimension:

```
$ figures provenance diff baseline.pdf revised.pdf

  RECIPE   :  identical (8b1f2c9a...)
  DATA     :  DIFFERENT
                effect_sizes.csv: 11d4e7b9... → 22e5f8c0...
                                  (n_rows 30 → 31)
  SCORER   :  weights changed
                anchor: 0.20 → 0.25
                dynamics: 0.15 → 0.10
  ENV      :  matplotlib 3.9.0 → 3.10.1
```

This makes "what changed between Figure 3 in submission v1 and v2 of the
manuscript" answerable in one command.

---

## 4. Worked examples

### Example A — happy path (bit-identical)

```
$ figures generate
[render] actin_microtubule_morphometry.compartment_paired_delta_scatter ...
[provenance] wrote figures/compartment_paired_delta_scatter.provenance.json

$ figures provenance verify figures/compartment_paired_delta_scatter.pdf
  figure_sha256       ✓ f7a9c32b...
  data.sources        ✓ 1 file verified
  recipe.module_sha   ✓ 8b1f2c9a...
  panelforge_version  ✓ 2.0.0
  rendering_env       ✓ matplotlib 3.9.0 darwin
  re-render           ✓ bit-identical
verify: PASS (6/6 checks)
```

### Example B — data tampering detected

A collaborator modifies the CSV ("just adding a row, surely safe"):

```
$ vim data/effect_sizes.csv         # adds one row

$ figures provenance verify figures/compartment_paired_delta_scatter.pdf
  figure_sha256       ✓ f7a9c32b...
  data.sources        ✗ data/effect_sizes.csv: sha256 MISMATCH
                        recorded:  11d4e7b9...
                        on disk:   22e5f8c0...
                        (n_rows 30 → 31)
  ...
verify: FAIL (1 mismatch)

remediation:
  This figure no longer reflects the data on disk. Either:
    (a) re-run `figures generate` to refresh the figure for the new data, or
    (b) restore data/effect_sizes.csv to sha 11d4e7b9... if the change was unintended.
```

### Example C — manuscript audit bundle

```
$ figures provenance bundle figures/figure_03_panel_A.pdf -o supp_figure_03A.tar.gz
[bundle] figure.pdf                        12.3 KB
[bundle] figure.provenance.json             4.1 KB
[bundle] recipe/ (3 files)                 18.7 KB
[bundle] data/effect_sizes.csv              4.0 KB
[bundle] README.md (auto)                   1.2 KB
[bundle] requirements.txt                   2.8 KB
wrote supp_figure_03A.tar.gz (43.1 KB)
```

The author uploads `supp_figure_03A.tar.gz` to the journal as a
supplement. Reviewer downloads, unpacks, runs
`figures provenance verify bundle/figure.pdf` and sees ✓ ✓ ✓. The
review tool of the future could automate this on submission.

---

## 5. Cryptographic considerations

### 5.1. Why sha256, and what it does (and does not) buy

The provenance chain uses **sha256** for every content hash: figure
bytes, source-data bytes, recipe-module bytes, font cache. The choice
is deliberate:

- **sha256 over sha1** — sha1 is broken for collision resistance
  (SHAttered, 2017); even though we are not relying on cryptographic
  security here, picking a non-broken hash is free.
- **sha256 over sha512** — half the bytes on disk, identical security
  posture for our use case, native support in CPython's `hashlib`, and
  the size of `module_sha` and `figure_sha256` strings end up
  user-readable when truncated to 12 chars.
- **sha256 over BLAKE3** — BLAKE3 is faster but adds a third-party
  dependency. The target dataset for any single figure is rarely above
  100 MB; sha256 throughput on a 2020-era laptop (~500 MB/s) is not the
  bottleneck.
- **sha256 over git's blob hash** — git uses sha1 for blob addressing;
  using sha256 throughout means our hashes are stable even when the
  underlying repo migrates to sha256 git (already supported, not yet
  default), and makes the format git-agnostic for non-git users.

sha256 is used here for **content addressing**, not for tamper-evident
signing. A motivated adversary with write access to both the PDF *and*
the `.provenance.json` can produce a consistent pair. The provenance
chain raises the cost of accidental drift to near zero; it does not
defeat malice.

### 5.2. Recommended pattern for archival

For tamper-evident archival (e.g. preregistration or grant deliverables),
the recommended pattern is: produce the bundle as in §3.3, then sign the
bundle externally with GPG or sigstore:

```
$ figures provenance bundle figures/fig.pdf -o fig.tar.gz
$ gpg --detach-sign --armor fig.tar.gz       # produces fig.tar.gz.asc
```

We document this pattern but do not bundle GPG into `panelforge-figures`.
Keys and trust roots are out of scope. A future elevation may ship a
`figures provenance sign` thin wrapper, but only after community feedback
on key management.

---

## 6. Determinism requirements

For `provenance verify` to consistently report `re-render: bit-identical`,
the rendering pipeline must be deterministic in the strict sense:

1. **Random seed**. Every recipe that uses randomness must accept a
   `seed` field in its contract, default to a constant (canonically
   `42`), and use `np.random.default_rng(seed)` exclusively. A pre-flight
   audit (`figures audit determinism`) scans all 448 recipes for use of
   `np.random.seed`, `random.seed`, or `random.random` without a seed,
   and reports violations.
2. **Matplotlib font cache**. We hash `~/.cache/matplotlib/fontlist-*.json`
   and store it in `rendering_environment.font_cache_sha256`. If it
   differs at verify time, environment drift is flagged. We do not fail
   verification on font cache drift unless `--strict`.
3. **Timestamp normalization**. PDFs embed a creation timestamp by
   default. We override it to `"D:19700101000000Z"` via matplotlib's
   `pdf.metadata` rcParams when `figures generate --committed` is set.
   `rendered_at` in the sidecar separately records the wall-clock time
   for human reference.
4. **Locale**. We set `LC_ALL=C` for the duration of `figures generate`
   to suppress locale-driven number formatting drift.
5. **Float order**. Recipes must not depend on dict insertion order
   for floating-point reductions; this is enforced via a lint rule.

Recipes that cannot meet these requirements declare
`@register_recipe(deterministic=False)`; their provenance writes
`rendering_environment.deterministic: false` and `verify` emits
`non_deterministic_warning` instead of comparing re-render bytes.

---

### 6.6. Spec ambiguities flagged for review

Three points where the spec deliberately leaves open questions for the
v2.0.0 release-engineering pass:

- **Cross-platform numerical determinism.** The current text accepts
  byte-identical PDFs as the gold standard but provides a tolerance mode
  for cross-platform reviewers. The threshold of "what counts as
  acceptable numerical drift" (last-bit floats? sub-pixel rendering
  shifts in tick locations?) is intentionally not pinned here; it
  belongs in `spec_rendering_environment.md`.
- **Bundle dependency closure.** `requirements.txt` in the bundle
  freezes a `pip list` snapshot, but does not freeze C library
  dependencies (libpng, libfreetype, etc.). For full reproducibility a
  Docker image or `pyproject.toml` lockfile would be needed. We defer
  this to a follow-on elevation (`spec_repro_container.md`).
- **`scorer.profile` schema.** The profile dict is open-ended in v1.0
  of the schema. We expect it to crystallize into a fixed schema in
  v1.1 once the scorer-elevation lands and we know which profile fields
  are load-bearing.

## 7. CLI integration

`figures generate` writes provenance by default. Two flags govern the
behavior:

| Flag | Effect |
|---|---|
| `--no-provenance` | Suppress sidecar emission. Useful in tight dev loops. |
| `--committed` | Normalize timestamps + require clean git tree; fails if dirty. Used in CI / for archival renders. |

`figures render <recipe>` (single-recipe rerender) also writes
provenance, with `scorer.score: null` since no shortlist context exists.

---

## 8. Files to create / modify

**New files**

- `src/panelforge_figures/manifest/provenance.py` (~350 LOC)
  - `ProvenanceRecord` (Pydantic)
  - `compute_file_sha256(path) -> str`
  - `compute_module_sha(module_path, repo_root) -> str` (git blob falls back to sha256)
  - `write_provenance(record, sidecar_path) -> None`
  - `load_provenance(sidecar_path) -> ProvenanceRecord`
  - `verify_provenance(record, repo_root, *, strict=False) -> VerifyReport`
  - `bundle_provenance(record, out_tarball) -> Path`
  - `diff_provenance(a, b) -> DiffReport`
- `docs/provenance.schema.json` (JSON-Schema draft 2020-12)
- `tests/test_provenance.py` (~250 LOC, ~20 tests; see §9)

**Edited files**

- `src/panelforge_figures/manifest/render_loop.py`
  Emit `<recipe>.provenance.json` after each successful PDF write. The
  hook lives at the bottom of `_render_one()` after `export.save_pdf`
  succeeds. Failure to write provenance is non-fatal, logged as a warning.
- `src/panelforge_figures/cli.py`
  Add `provenance` subcommand group with the four verbs from §3.
- `src/panelforge_figures/core/contract.py`
  Add optional `deterministic: bool = True` keyword to
  `@register_recipe`. Surfaces in metadata.

---

## 9. Test surface

Twenty tests in `tests/test_provenance.py`, organized:

**Schema (5 tests)**
- `test_provenance_record_round_trip` — write then load → equal
- `test_schema_validates_canonical_example`
- `test_schema_rejects_missing_required_field`
- `test_schema_rejects_bad_hash_format`
- `test_unknown_extra_fields_rejected_strict_mode`

**Hashing (4 tests)**
- `test_sha256_stable_across_runs`
- `test_module_sha_matches_git_blob`
- `test_module_sha_falls_back_outside_git`
- `test_data_sha256_detects_single_byte_change`

**verify (5 tests)**
- `test_verify_passes_immediately_after_render`
- `test_verify_flags_data_drift`
- `test_verify_flags_recipe_drift`
- `test_verify_flags_panelforge_version_drift`
- `test_verify_non_deterministic_recipe_emits_warning_not_failure`

**bundle / diff (4 tests)**
- `test_bundle_round_trip_re_renders_bit_identical`
- `test_diff_identifies_recipe_only_drift`
- `test_diff_identifies_data_only_drift`
- `test_diff_identifies_scorer_weight_drift`

**Integration (2 tests)**
- `test_figures_generate_writes_provenance_by_default`
- `test_figures_generate_no_provenance_flag_suppresses`

---

## 10. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Random-seed control across all 448 recipes is incomplete; `verify` produces spurious mismatches. | High | Ship `figures audit determinism` in v2.0.0-rc1; make it part of the v2 release gate. Recipes that fail the audit are flagged `deterministic=False` and verify emits warnings, not failures. |
| Floating-point determinism varies across CPU architectures (e.g. last-bit drift between Intel and Apple Silicon). | Medium | Document tolerance: `verify` accepts byte-identical PDFs as ✓ but provides `--tolerance numerical` (decoder-level comparison via PyMuPDF) for cross-platform reviewers. |
| Provenance file size: 10s of KB per figure × 100 figures = MB of JSON in the repo. | Low | Bundle uses `.tar.gz` (compresses ~10×). Sidecars are tracked in git via LFS for large data files only; JSON itself compresses well in normal git. |
| Path leakage: absolute paths in `panelforge_workspace` could leak usernames. | Medium | All paths normalized to repo-root-relative on write; absolute paths rejected by schema. |
| Recipe-module evolution: `module_sha` changes whenever the file is touched, even cosmetically; spurious "drift" reports. | Medium | `diff` prints `module_sha changed but rendered output identical` as an *info* line, not a failure. |
| Re-render at verify time is slow for some recipes (~5s × 100 figures = 8 min). | Low | `verify --no-rerender` skips step 6, falling back to hash-only verification. CI uses full re-render; interactive review uses fast mode. |

---

## 11. Acceptance criteria

The provenance chain ships when **all five** of these tests pass on
`main`:

1. **Universal determinism** — `figures generate --all-recipes` followed
   by a second `figures generate --all-recipes` produces 448
   bit-identical PDFs (sha256 match).
2. **Drift detection** — `provenance verify` correctly flags any
   single-byte change to a source CSV (parameterized over 5 representative
   recipes).
3. **Bundle round-trip** — `provenance bundle` followed by extraction in
   `/tmp/fresh-checkout` and re-`verify` passes all six checks for 5
   representative figures.
4. **Diff specificity** — synthetic mutations to (a) recipe source, (b)
   data CSV, (c) scorer weights, (d) matplotlib version each produce a
   `diff` report that names exactly that dimension and no other.
5. **Schema conformance** — every `provenance.json` produced by
   `figures generate` validates against `docs/provenance.schema.json`
   (enforced as a pytest parametrize over the 448 recipe demos).

---

## 12. Out of scope

- **Cryptographic signing.** GPG / sigstore integration is recommended in
  §5 but lives outside the package. Users sign bundles externally.
- **Provenance for runtime parameters that vary at scoring time.**
  Scorer-internal random samples, tie-breaking RNG state, and other
  ephemerals are out of band; we record the resolved decision, not the
  selection process.
- **Cross-version migration.** A v1.x → v2.0 schema migration tool is
  not part of this elevation. v1.x has no provenance; v2.0 starts fresh.
  Future schema bumps (1.0 → 2.0) will ship a migration script as a
  separate elevation.
- **Editor integration.** "Click here in VS Code to see how this PDF was
  made" is desirable but lives in a separate tooling track.
- **Database-backed provenance.** A central registry of all rendered
  figures across a lab is outside the scope of a single-repo tool.
- **Provenance for non-`figures generate` outputs.** Manual matplotlib
  scripts, ad-hoc Jupyter renders, etc. are not auto-instrumented; users
  who want provenance call `panelforge_figures.manifest.provenance.write`
  directly.
