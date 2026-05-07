# Spec: Data-Class Safety Mode (`data_class`)

**Status:** Draft v1 — executable scope for v2.0.0 elevation
**Owner:** Safety / regulated-research track (W8 swarm scribe)
**Targets:** `panelforge-figures` v2.0.0
**Companion specs:** `spec_provenance_chain.md`,
`spec_composition_layer.md`, plus parallel v2.0.0 elevations under
`docs/spec_*.md`

---

## TL;DR

`panelforge-figures` v1.6.1 ships an LLM-bridge (Pass-3 column mapping)
that calls Anthropic's API by default whenever `ANTHROPIC_API_KEY` is in
the environment and the `claude-autonomous` extra is installed. PR #55
added a *disclosure* of that behaviour but **no enforcement**. A
clinician with PHI-bearing CSVs cannot adopt a tool whose default code
path may transmit column names off-host — even if column names alone
are unlikely to leak PHI in practice, "unlikely" is not a defensible
posture for IRB / HIPAA review.

This spec proposes a single configuration field —
`data_class: clinical | research | public` — declared in
`panelforge.project.yaml`. The field gates **every** elevation that
touches the network or persists derived state: the LLM bridge, vision
input (W5), telemetry (W6), provenance hashes (W3), and any future
plugin that declares `network_required: true`. A new CLI verb
`figures audit data-class` scans column names for PHI/PII patterns and
warns the user when their declared `data_class` understates the risk
implied by their data. `figures config show` and `figures config set
data_class` round out the user-facing surface.

The result is one tool that serves three audiences — public-research
demo users, regulated researchers, and clinicians — with defaults that
are appropriate for each, and a single declarative knob to switch
between them.

---

## 1. Why now — the problem statement

Three observations have converged.

1. **v1.6.1 ships LLM-by-default behaviour with disclosure but no
   enforcement.** The privacy block under `CLAUDE_CODE_AUTONOMOUS.md`
   §"Privacy & data handling" tells users *what* the bridge sends and
   *how* to opt out. Opt-out is achieved by uninstalling the extra or
   unsetting an environment variable. There is no first-class way to
   say "this project must never invoke an LLM, regardless of which
   extras are installed on which machine".
2. **Clinical / regulated researchers cannot adopt a tool where the
   safe configuration is achieved by absence.** IRB-approved analysis
   pipelines must demonstrate a positive guarantee that no off-host API
   call happens. "We didn't install the extra" is not auditable; "the
   project file declares `data_class: clinical` and the CLI refuses to
   call Anthropic in that mode" is.
3. **Public-research demo users want maximum capability with minimum
   ceremony.** A user fitting a recipe to a synthetic toy dataset for a
   tutorial gains nothing from clinical-grade defaults; the LLM bridge
   and vision input *should* be on by default for them.

A single binary "regulated mode" toggle would solve (2) but lose
nuance: research-with-de-identified-PHI is a real middle ground where
LLM-and-vision should be opt-in, telemetry should be opt-in, but the
provenance hash of the de-identified data file is fine to record. The
three-class taxonomy below captures all three audiences.

---

## 2. The three classes

| `data_class` | LLM Pass-3 | Telemetry | Vision | Provenance hash | Default posture |
|---|---|---|---|---|---|
| `clinical` | DISABLED — bridge returns UNBOUND | OFF — write is a no-op | DISABLED — refuse to call | redacted (column names + n_rows kept; sha256 of data omitted) | conservative |
| `research` | OPT-IN — `--llm` flag or `enable_llm: true` | OPT-IN — `enable_telemetry: true` | OPT-IN — `enable_vision: true` | full | balanced (default class if unset) |
| `public` | DEFAULT-ON — runs whenever extras installed and key present | OPT-IN — `enable_telemetry: true` | DEFAULT-ON | full | maximum capability |

The default class when `data_class` is absent from
`panelforge.project.yaml` is **`research`**. Defaulting to `clinical`
would silently break demo users; defaulting to `public` would silently
expose regulated-research users. `research` is the safe middle ground:
opt-in for everything that calls home, full provenance, no surprises.

---

## 3. `panelforge.project.yaml` schema extension

The existing v1.6.1 schema (see `CLAUDE_CODE_AUTONOMOUS.md`
§"`panelforge.project.yaml` schema") gains two fields:

```yaml
# panelforge.project.yaml
anchor: DISC1
factorial: false
modalities: [biophysics_scaling]

# new in v2.0.0:
data_class: clinical                    # one of clinical | research | public
data_class_overrides:                   # optional — fine-grained
  vision: false                          # already false in clinical default
  telemetry: false                       # already false in clinical default
  provenance_hash: redacted              # already redacted in clinical default
  llm_bridge: false                      # already false in clinical default
  allowed_columns: [patient_id_hashed]   # PHI-scanner allow-list
```

**Field semantics.**

- `data_class` (string, optional, default `research`). If present,
  must be one of `clinical | research | public`. Any other value is a
  schema error caught at load time (raises `DataClassError` with the
  list of valid values).
- `data_class_overrides` (object, optional). Each key, when set,
  overrides the corresponding default for the declared class. The
  override engine is **strictly subtractive for clinical**: a
  `clinical` project may not opt back into LLM, vision, telemetry, or
  unredacted provenance via overrides. Attempting to do so raises
  `DataClassError("clinical class is non-relaxable")`. For `research`
  and `public` projects, overrides may turn things off (always
  permitted) or on (within that class's allowed set).
- `data_class_overrides.allowed_columns` (list[str], optional). Column
  names in this list are exempt from PHI-pattern scanning. Used to
  silence false-positives (e.g. a sanitised `patient_id_hashed` column
  whose name lexically matches the medium-risk pattern but whose
  contents are SHA-256 digests).

Schema is enforced by extending `manifest/schema.py` (or a new
`safety/project_schema.py`); load-time validation runs in
`project_scan.py` before any other elevation is consulted.

---

## 4. PHI/PII column-name patterns (the audit scanner)

The scanner is pattern-based — it does **not** read cell values. It
matches column names case-insensitively after stripping non-alphanumeric
characters (so `Patient-DOB`, `patient_dob`, `PatientDOB` all collapse
to `patientdob`). Three risk tiers.

**High-risk** (definite PHI/PII; trigger ERROR if `data_class !=
clinical`):

```
patient_dob, dob, mrn, ssn, phn, subject_id_full,
address, street_address, email, email_addr,
phone, phone_number, telephone,
date_of_birth, birth_date, birthday,
medical_record, npi
```

**Medium-risk** (potential PHI when combined; trigger WARN if
`data_class == public`, INFO if `data_class == research`):

```
patient_id, subject_id, study_id, encounter_id,
visit_id, accession, sample_id_full,
zip, zipcode, postal_code,
age_at_event, age_yr, age_years,
sex, gender, race, ethnicity
```

**Low-risk** (no action; included as a positive control for tests):

```
cell_id, well_id, feature, measurement,
area_um2, intensity_mean, velocity,
condition, replicate, batch, channel
```

Patterns live in `src/panelforge_figures/safety/phi_patterns.yaml`
(YAML for easy user-facing inspection and contribution). The scanner
exposes `match_column(name) -> RiskTier | None`. A column may match
both tiers simultaneously (e.g. a contrived `patient_dob_age_yr`); the
higher tier wins.

---

## 5. `figures audit data-class` — column-name scanner

```text
$ figures audit data-class
Scanning columns under data/ ...
  data/cells.parquet   34 columns
  data/subjects.csv     8 columns

PHI/PII risk report
-------------------
HIGH-RISK columns (data_class=research is INADEQUATE):
  data/subjects.csv :: patient_dob       -> matches pattern "dob"
  data/subjects.csv :: mrn               -> matches pattern "mrn"

Recommendation: set `data_class: clinical` in panelforge.project.yaml,
or remove / hash these columns before running `figures generate`.

Exit code: 2 (error)
```

**Behaviour matrix.**

| Finding | `data_class=clinical` | `data_class=research` | `data_class=public` |
|---|---|---|---|
| High-risk column found | INFO (acknowledged) | ERROR — exit 2 | ERROR — exit 2 |
| Medium-risk column found | INFO | INFO | WARN — exit 0 |
| Only low-risk columns | OK — exit 0 | OK — exit 0 | OK — exit 0 |

The scanner walks `data/` recursively for `*.csv`, `*.parquet`,
`*.feather`, `*.h5ad` (column names only — never cell values; for h5ad
we read `obs.columns` and `var.columns` from the file's metadata
header). Files matching `data_class_overrides.allowed_columns` are
filtered before tier evaluation.

Exit codes: 0 = clean / WARN-only, 2 = ERROR. CI integration is via
`figures audit data-class --strict` which promotes WARN to ERROR.

---

## 6. Enforcement points — every elevation honours `data_class`

The matrix below is **load-bearing**. Every elevation in the v2.0.0
roadmap must explicitly check `data_class` at its entry point. The
integration test in §11 walks all gates to enforce this contract.

| Gate | Module | Check | Behaviour when `data_class=clinical` |
|---|---|---|---|
| LLM Pass-3 (W4) | `manifest/data_bridge.py::_llm_pass` | first line of function | return `(None, 0.0, "data_class=clinical disables LLM bridge")` |
| Vision input (W5) | `manifest/vision_input.py::call_vision` | first line | raise `DataClassError("vision disabled by data_class=clinical")` |
| Telemetry (W6) | `manifest/telemetry.py::record_event` | first line | early-return `None` (no file write); log INFO once per session |
| Provenance hash (W3) | `manifest/provenance.py::compute_data_hash` | post-compute redaction step | replace `data_sha256` with `"REDACTED-data_class=clinical"`; preserve column names + n_rows |
| Plugin loader | `recipes/plugin_loader.py` | per-plugin `plugin.yaml` parse | refuse to load any plugin with `network_required: true`; log to stderr; continue with remaining plugins |

The `safety/__init__.py` module exports a single helper:

```python
from panelforge_figures.safety import (
    DataClass,
    load_data_class,                         # reads project.yaml
    is_llm_allowed, is_vision_allowed,
    is_telemetry_allowed, is_provenance_full,
    plugin_network_allowed,
)
```

Each gate calls the corresponding `is_X_allowed()` predicate.
Predicates are pure functions of `(DataClass, overrides)` — no side
effects, fully unit-testable, identical across modules.

---

## 7. Worked examples

### Example A — clinical (de-identified ICU vitals study)

```yaml
# panelforge.project.yaml
anchor: none
modalities: [tabular_clinical]
data_class: clinical
data_class_overrides:
  allowed_columns: [patient_id_hashed]   # column is sha256 of MRN
```

User runs `figures generate`. `data_bridge._llm_pass` is invoked from
the resolver; it returns immediately with reason
`"data_class=clinical disables LLM bridge"`. Pass-1 exact and Pass-2
fuzzy still run; unbound contract fields surface in the checkpoint-2
mapping table for manual binding. `figures audit data-class` reports
HIGH-RISK columns `patient_dob`, `mrn` if present — but with
`data_class=clinical` declared, the audit logs them as INFO, not
ERROR. Telemetry writes are no-ops. Vision API is refused if any
recipe attempts it. Provenance sidecars contain
`data_sha256: "REDACTED-data_class=clinical"` while keeping
`column_names`, `n_rows`, `recipe_id`, and the rendering-environment
hash for full reproducibility on the original host.

### Example B — research (default; CDC42 factorial paper)

```yaml
# panelforge.project.yaml
anchor: CDC42
factorial: true
modalities: [biophysics_scaling, actin_microtubule_morphometry]
# data_class omitted → defaults to "research"
```

All three elevations (LLM, vision, telemetry) are **off** unless the
user explicitly enables them on the CLI (`figures generate --llm
--vision`) or in the project file
(`data_class_overrides: {llm_bridge: true}`). Provenance is full.
`figures audit data-class` warns nothing if columns are typical
biophysics field names; surfaces ERROR if `mrn` or `patient_dob` slip
in (sanity check: this catches the "I forgot to set data_class to
clinical" failure mode).

### Example C — public (synthetic demo data)

```yaml
# panelforge.project.yaml
anchor: DISC1
modalities: [biophysics_scaling]
data_class: public
```

Pass-3 LLM and vision are default-on. `figures generate` invokes the
LLM whenever `ANTHROPIC_API_KEY` is set without further opt-in.
Telemetry remains opt-in (we never collect telemetry without an
explicit user toggle, regardless of class). Public class is intended
for synthetic test data, tutorials, conference demos. The audit
scanner WARNS on medium-risk patterns (defensive: a tutorial author
who accidentally commits a `subject_id` column will see the warn).

---

## 8. CLI surface

```text
figures audit data-class [--strict] [--data DIR]
    Scan column names under data/ for PHI/PII patterns.
    --strict promotes WARN to ERROR.

figures config show
    Print current data_class and resolved overrides.
    Format: human-readable table; --json for machine parse.

figures config set data_class <value>
    Interactive setter. On clinical, prints the implications
    table from §2 and asks for confirmation. Updates
    panelforge.project.yaml in place (preserves comments via
    ruamel.yaml round-trip loader).

figures config set <key> <value>
    Generic setter for data_class_overrides.<key>.
```

`figures config show` example output:

```
panelforge.project.yaml resolved configuration
----------------------------------------------
data_class:           clinical
LLM bridge:           DISABLED   (forced by data_class)
Vision input:         DISABLED   (forced by data_class)
Telemetry:            OFF        (forced by data_class)
Provenance hash:      REDACTED   (forced by data_class)
Plugin network:       DISABLED   (forced by data_class)

Allow-list columns:   patient_id_hashed
```

---

## 9. Files to create / modify

**NEW**

- `src/panelforge_figures/safety/__init__.py` (~150 LOC) —
  `DataClass` enum, `load_data_class()`, six `is_X_allowed()`
  predicates, `DataClassError`.
- `src/panelforge_figures/safety/phi_pattern_scanner.py` (~150 LOC) —
  pattern table loader, `match_column()`, `scan_directory()`,
  exit-code mapping.
- `src/panelforge_figures/safety/phi_patterns.yaml` — high / medium /
  low pattern lists; user-inspectable.
- `tests/test_data_class_safety.py` (~250 LOC) — see §11.

**EDIT**

- `src/panelforge_figures/manifest/data_bridge.py` — add gate to
  `_llm_pass`; one new line at function entry plus updated docstring.
- `src/panelforge_figures/manifest/telemetry.py` (W6) — gate
  `record_event()`; no-op when not allowed.
- `src/panelforge_figures/manifest/vision_input.py` (W5) — gate
  `call_vision()`; raise `DataClassError`.
- `src/panelforge_figures/manifest/provenance.py` (W3) — redact
  `data_sha256` when not full.
- `src/panelforge_figures/cli.py` — register `audit data-class`,
  `config show`, `config set` subcommands.
- `CLAUDE_CODE_AUTONOMOUS.md` — new "Data-class safety" section under
  the privacy disclosure; cross-references this spec.

---

## 10. Test surface

```python
# tests/test_data_class_safety.py — ~250 LOC

def test_clinical_disables_llm_bridge():
    """Bridge returns UNBOUND with explanatory reason when clinical."""

def test_clinical_telemetry_write_is_noop():
    """record_event() returns None and writes no file even if
       enable_telemetry=true is set in overrides — clinical is
       non-relaxable."""

def test_clinical_vision_refused_with_key_present():
    """call_vision() raises DataClassError even when ANTHROPIC_API_KEY
       is in env — the network call must not be issued."""

def test_research_opt_in_flags_work():
    """research + enable_llm=true → bridge runs.
       research + enable_llm=false (default) → bridge skipped."""

def test_public_defaults_llm_on():
    """public class + key present → _llm_pass executes; without
       further opt-in flag."""

def test_phi_scanner_finds_mrn_positive_control():
    """match_column('mrn') == HIGH; match_column('Patient_DOB') == HIGH
       (case + separator insensitive)."""

def test_phi_scanner_passes_cell_id_negative_control():
    """match_column('cell_id') is None; match_column('area_um2') is None."""

def test_data_class_overrides_fine_grain():
    """research + overrides.vision=true → vision allowed; same project
       + overrides.llm=false → llm forbidden even with --llm flag."""

def test_clinical_overrides_cannot_relax():
    """data_class=clinical + overrides.llm=true → DataClassError at
       project load."""

def test_missing_data_class_defaults_to_research():
    """Project file with no data_class field → load_data_class()
       returns DataClass.RESEARCH; INFO log line emitted."""

def test_provenance_hash_redacted_in_clinical():
    """compute_data_hash() under clinical returns
       'REDACTED-data_class=clinical'; column_names + n_rows preserved."""

def test_plugin_with_network_required_refused_in_clinical():
    """A test plugin with network_required: true in plugin.yaml is
       rejected at load; non-network plugins still load."""

def test_audit_data_class_high_risk_errors_in_research():
    """Synthetic data dir with column 'patient_dob' + research class →
       audit returns exit code 2."""

def test_integration_all_gates_walk():
    """Single test that imports every gate and asserts each calls
       safety.is_X_allowed() — guards against future feature regression
       (a new elevation that forgets to gate)."""
```

The integration test (`test_integration_all_gates_walk`) is the
critical guard: it discovers gate functions by introspection (a
registry decorator `@safety.gate("llm")`) and fails CI if a new
elevation lands without registering. This implements the "future
regression" mitigation in §12.

---

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| User mis-declares — labels clinical data as `research` | `figures audit data-class` catches via column-name scan; CI hook recipe in `RELEASING.md` runs audit before any commit touching `data/`. |
| Future elevation regresses (forgets to gate) | `test_integration_all_gates_walk` walks the gate registry; a new gate without registration fails CI. The `safety.gate` decorator makes registration declarative and hard to forget. |
| PHI scanner false positives (e.g. `subject_id` for cell-line subject) | `data_class_overrides.allowed_columns` allow-list per project; well-documented in `figures audit data-class --help`. |
| User hides `data_class: clinical` in overrides to "speed things up" via env var hack | `data_class` cannot be set via env var — only via project YAML. CLI prints the resolved class on every `figures generate` invocation (one line, suppressible only with `--quiet`). |
| Schema drift between `safety/__init__.py` predicates and gate sites | All predicates and gate sites import from a single `safety` module; predicate signatures are unit-tested for stability. |

---

## 12. Acceptance criteria

A v2.0.0 release ships data-class safety **only** when all of the
following hold:

1. Three modes (`clinical`, `research`, `public`) have distinct,
   table-documented behaviour matching §2; `figures config show`
   surfaces the matrix.
2. PHI scanner catches `patient_dob`, `mrn`, `ssn`, `dob`,
   `email`, `phone` in positive-control fixtures and passes
   `cell_id`, `area_um2`, `feature` in negative-control fixtures.
3. All five enforcement points (LLM, vision, telemetry, provenance,
   plugins) check `data_class` and pass dedicated gate tests.
4. `figures config show` prints a clear, scannable summary; `--json`
   variant matches a documented schema.
5. `figures config set data_class clinical` interactive flow shows the
   implications table and requires explicit `y` confirmation.
6. `test_integration_all_gates_walk` passes — i.e. every elevation
   that touches network or persists state has registered a gate.
7. Default behaviour (no `data_class` field) is `research` with all
   network-touching elevations OFF.

---

## 13. Out of scope

These belong in follow-up specs, not v2.0.0:

- **GDPR-specific compliance helpers** — right-to-erasure tooling,
  data-subject access export. Defer to `spec_gdpr_helpers.md`.
- **HIPAA Safe-Harbor automatic redaction** — programmatic stripping
  of the 18 HIPAA identifiers from input files. The v2.0.0 scope is
  *detection and refusal*, not *transformation*. Defer.
- **Audit logs** — who set `data_class`, when, with what previous
  value. Useful for institutional review but is its own subsystem.
  Defer to `spec_audit_log.md`.
- **Network egress firewalling** — a kernel-level guarantee that no
  outbound socket opens regardless of code paths. The `data_class`
  contract is enforced inside the application; users requiring
  hardware-level guarantees should run inside a network-isolated
  container. Defer.
- **Per-recipe `data_class` requirements** — a future recipe may
  declare `min_data_class: research` to refuse to render against
  `public` synthetic data. Sketched in `spec_recipe_versioning.md`;
  not implemented here.

---

## 14. Open questions for v2.0.0 owner

1. Should `data_class: research` (the default) emit a one-line stderr
   notice on first `figures generate` invocation, prompting the user
   to confirm? Pro: avoids silent default. Con: noise for the 90% of
   users for whom `research` is correct.
2. Where do third-party plugins declare their data-class needs —
   `plugin.yaml::min_data_class` (allow-list semantics) or
   `plugin.yaml::network_required: bool` (single bit)? This spec uses
   the bit; the recipe-versioning spec may want the allow-list.
3. Should `figures audit data-class` block `figures generate` by
   default, or only on `--strict`? Current draft: warn-only at
   `generate` time, ERROR at audit time; the user must opt into a
   blocking audit via a pre-render hook. Open for discussion.

---

*End of spec — `docs/spec_data_class_safety.md` (v2.0.0 elevation, W8).*
