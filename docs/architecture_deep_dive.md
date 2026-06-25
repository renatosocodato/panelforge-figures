# panelforge-figures — Architecture Deep-Dive

## 0. How to use this document (it's a defense brief, not a tutorial)

This document exists for one reader: the author, preparing to defend every major
design decision in panelforge-figures before open JOSS peer review. It is **not**
a tutorial, not a getting-started guide, and not marketing. If you want to know
*how to render a figure*, read `docs/quickstart.md`. If you want to know *why the
recipe registry is a mutable module-global populated by import side-effects, and
what you will say when a reviewer calls that brittle*, you are in the right place.

The framing is adversarial on purpose. A JOSS reviewer who runs the code, reads
the source, and reads the claims in the docstrings will find the seams. The goal
here is that the author has already found every seam first, knows which ones are
deliberate trade-offs (defensible), which ones are documentation-vs-implementation
gaps (fixable before review), and which ones are genuine structural debt (must be
acknowledged, not hidden). Each subsystem analysis below is honest about all three
categories.

Three conventions used throughout:

- **Decision → rationale → rejected alternative → cost.** Every design decision is
  presented with what was chosen, why, what was rejected, and what the choice
  costs. A decision with no stated cost is a decision not yet understood.
- **"Defensible" vs. "a real gap."** A trade-off is *defensible* when the cost is
  bounded, documented, and the alternative was genuinely worse. It is *a real gap*
  when a claim in the code overstates what the code does, or when an invariant is
  enforced by convention rather than by construction.
- **Honesty over polish.** Where the implementation does not match the docstring,
  this document says so plainly. Section 7 collects the worst of these so the author
  is not blindsided.

Read sections 1 and 2 first — they are the load-bearing philosophy and the single
most important design decision. Section 6 is the rehearsal: the twelve questions a
reviewer is most likely to ask, with the crisp honest answers. Section 7 is the
list of things to fix or to own before submission.

---

## 1. Design philosophy — the cross-cutting principles

panelforge-figures is built on six principles that recur across every subsystem.
They are not aspirational mission-statement language; each one is a concrete
engineering commitment that shows up in the type signatures, and each one has a
real cost the author must be ready to defend.

### 1.1 Modality-first

**The principle.** The ~390–471 figure recipes are organized into ~20 scientific
*modalities* (single-cell embeddings, intravital imaging, calcium signaling, clinical
cohort, cryo-EM, and so on). Each modality owns a single `ModalityAesthetic`
(`core/aesthetic_base.py`) — its palette, colormaps, spine color, annotation
fontsizes, scale-bar policy, label vocabulary — exposed as a module-level `AESTHETIC`
object in the modality's `_aesthetic.py`. Every recipe in a modality calls
`AESTHETIC.apply_to_ax(ax)`, and a CI test verifies that every recipe imports from
its modality's `_aesthetic` module (471/471 recipes pass this).

**Why it was chosen.** Visual coherence is the product. A reviewer flipping through
a gallery should see that all intravital figures look like a family and all
single-cell figures look like a different family, without any recipe author being
able to drift the palette. The per-modality split also encodes genuine domain
differences that a single global stylesheet cannot: intravital figures *require*
scale bars (`required_scale_bars=True`), meta-and-diagnostic figures *forbid* them
(`required_scale_bars=False`).

**What it costs.** Twenty separate `AESTHETIC` objects to maintain, a hard CI rule
that every recipe import the local `_aesthetic`, and a registration-boundary leak:
`register_modality` types its `aesthetic` parameter as `Any`, so the one contract
core most wants to enforce ("every modality satisfies `ModalityAesthetic`") is the
one it accepts untyped. A modality could register a non-`ModalityAesthetic` object
and core would silently accept it.

### 1.2 Contract-bound recipes

**The principle.** Every recipe is a self-contained module with four mandatory
artifacts in the same order: a pydantic `RecipeContract` subclass (the input schema),
a module-private `_demo()` that returns a populated contract, a frozen `_META`
`RecipeMetadata`, and a `render(contract, ax=None, **_)` function decorated with
`@register_recipe`. The contract is the binding interface — the CLI, MCP server,
data-binder, and composition engine all validate user data against
`entry.contract.model_validate(...)` before calling `render`.

**Why it was chosen.** Structural uniformity makes 471 recipes independently
reviewable: open any file, find the same four things. The `_demo()` requirement means
every recipe is runnable with zero external data, which powers the entire
smoke-test / quality-gate harness and lets the MCP server render any recipe on demand.

**What it costs.** Heavy boilerplate duplication (471 near-identical import blocks and
`render` signatures) and — critically — no compile-time enforcement that the four
artifacts exist or agree. Consistency is maintained by convention plus CI, not by the
type system. And the contract guarantee is weaker than the docstring claims (see §2):
`RecipeContract` sets `arbitrary_types_allowed=True`, so raw `np.ndarray` fields — the
inputs recipes most need validated — bypass pydantic entirely.

### 1.3 Agent-discoverability

**The principle.** The system is designed to be driven by an LLM agent, not just a
human at a terminal. This shows up everywhere: the recipe registry is the single
ground-truth catalog with no separate manifest to drift; `recipes_index.json`
(`manifest/catalog.py`) is an agent-facing JSON index embedding the tag taxonomy, the
scoring rubric, and the 8-question intake spec so an agent can reason about recipe
selection without importing Python; the MCP server (`mcp/`) exposes the registry,
scorer, provenance, and projects as Claude tools with auto-generated input schemas
derived from each recipe's pydantic contract via `model_json_schema()`.

**Why it was chosen.** The selection problem (which of ~390 figures answers my
research question?) is exactly the kind of structured-reasoning task an agent does
well, *if* the catalog is machine-readable and the scoring is transparent. Embedding
the intake questions and rubric in the JSON index means an agent never has to
reverse-engineer the selection logic.

**What it costs.** A second representation of several things (intake questions exist as
`IntakeQuestion` dataclasses *and* as embedded JSON), and a determinism burden: agent
consumption demands byte-stable output, which forces the elaborate deterministic
tie-break sort, the pinned `PANELFORGE_BUILT_AT`/`PANELFORGE_GIT_COMMIT` sentinels in
the index writer, and sorted-keys JSON everywhere. The MCP surface also has a real
gap: four `expose_*` config flags are non-functional no-ops (§4.6, §7).

### 1.4 Privacy-by-construction

**The principle.** A three-tier data-class safety layer (`safety/__init__.py`) gates
every capability that touches the network or persists data. The three classes are
`clinical` (forced off, no override), `research` (default; off-host capabilities are
opt-in), and `public` (default-on). Pure predicates — `is_llm_allowed`,
`is_vision_allowed`, `is_telemetry_allowed`, `is_plugin_network_allowed`,
`should_redact_provenance_hashes` — are consulted at every gate site. The LLM
column-binder, the vision figure-scanner, telemetry, and provenance-hash redaction all
fail closed under `clinical`.

**Why it was chosen.** panelforge-figures is a clinical-adjacent tool; regulated data
must stay off-host *by construction*, not by the user remembering to flip a flag. The
policy table is the single source of truth, the predicates are pure functions of the
resolved policy plus environment, and `data_class` is held in one module-global set
only via `set_data_class` — deliberately *not* settable from an env var, so a hostile
environment cannot silently relax clinical mode.

**What it costs.** The guarantee is only as strong as its enforcement points: the
safety module provides predicates, but nothing structurally prevents a new code path
from calling an LLM without consulting `is_llm_allowed` — coverage is by audit, not by
a structural choke-point. The global is process-wide and not thread-safe (acceptable
for single-process CLI/MCP runs, indefensible for a multi-tenant server). And there is
one real enforcement gap: `telemetry.log_invocation` gates only on the project-YAML
opt-in flag and never consults `safety.is_telemetry_allowed`, so a clinical project
with `telemetry: opt-in` in its YAML would write `usage.jsonl` despite the policy
forcing telemetry off (§7).

### 1.5 Reproducibility-as-a-first-class-citizen

**The principle.** Rendering a figure produces a content-addressed provenance sidecar
(`<figure>.provenance.json`, `manifest/provenance.py`): sha256 of the figure bytes and
data bytes, git-blob sha of the recipe module, the resolved statistical contract, and
the audit verdicts. A reproducibility lockfile (`manifest/reproducibility.py`) captures
the environment, RNG seeds, and data hashes for byte-identical replay. All
provenance/lock JSON is written with `indent=2, sort_keys=True` and a trailing newline
so `git diff` shows only real content changes. The render cache (`manifest/render_cache.py`)
keys on recipe-source sha, canonical contract sha, and order-insensitive data sha.

**Why it was chosen.** A figure library whose figures cannot be regenerated bit-for-bit
is not a scientific tool. Content-addressing makes drift detectable and reviewer-verifiable
(`git hash-object recipe.py` reproduces the recorded `module_sha`); the env override
`PANELFORGE_BUILT_AT` lets archival renders produce byte-stable sidecars for CI.

**What it costs.** Determinism is partly the caller's responsibility — RNG state is
captured only when explicitly passed, never introspected, so a recipe that seeds
internally and forgets to thread the seed through produces a lock that cannot reproduce
its bytes. `module_sha` is `None` outside a git tree, silently disabling recipe-drift
detection (despite a docstring promising a sha256 fallback that does not exist). And
`replay_lock` in v2.2.0 only detects environment drift; it does **not** rebuild a venv
or re-render, so "replay success" currently means "env matches lock", not "bytes
reproduced" (§7).

### 1.6 The elevation model

**The principle.** The system was built as a sequence of numbered *elevations* and
*sprints* (E1.7 statistical contracts, E2 claim-check, E7 manuscript-alignment, E8
family-recommendation, E9 novelty/scout, E10 collision, E11 render-cache, E12
star-methods, E13 xref-linter, E14 citation-inserter, E16 venue-auditor, E17
bias-auditor, E18 ci-runner, E20 status-dashboard, and so on), often by separate
"build agents" working asynchronously in the same merge window.

**Why it was chosen.** It let the system grow capability-by-capability without a single
agent holding the whole codebase in working memory, and it explains the pervasive
*best-effort / fail-soft* posture: a module had to stay importable and partially
functional before its dependencies existed. This is why `execute_plan` catches
`ImportError` as soft-notes, why `intake.py` defensively redefines a fallback
`ProjectProfile`, and why almost every cross-subsystem call is lazy-imported.

**What it costs.** It is the deepest source of structural debt. Asynchronous builds
produced duplicated taxonomies (the four phantom families, two notions of
"supporting panel", triplicated TF-IDF code), documentation that references
`docs/spec_*.md` and undefined "Wave/Sprint/Elevation" vocabulary, and a swarm of
`except Exception  # noqa: BLE001` blocks that swallow genuine bugs into warnings. The
elevation labels themselves are undefined without external spec docs a reviewer may not
read.

---

## 2. The foundational contract system (`core/`)

If there is a single most-important design decision in panelforge-figures, it is this:
**the recipe registry is a global, mutable, module-level dict populated by an
`@register_recipe` decorator at import time, and that registry — not any external
manifest file — is the ground truth for the entire catalog.** Everything else in the
architecture is a consequence of, or a reaction to, that choice.

### 2.1 The registry: `register_recipe` and `ensure_all_imported`

`core/contract.py` holds a module-level `_REGISTRY` dict. The `@register_recipe`
decorator, applied to each recipe's `render` function, inserts a `_RegistryEntry`
(metadata + dotted path + render callable + contract type + demo contract, exposing
`full_name = modality.name`) into that dict at decoration time. Because nothing is
registered until imported, `ensure_all_imported()` walks `pkgutil.iter_modules` over the
recipes package to force every modality's decorators to run before any query.

**Rationale.** Co-locating registration with the renderer means a recipe *cannot exist
without being catalogued* — there is no separate manifest to keep in sync, and adding a
recipe is adding a file plus an import line. The CLI, MCP server, gallery generator, and
manifest layer all read the one registry. Duplicate `full_name`s raise `ValueError` at
import (the most likely copy-paste authoring mistake fails fast).

**Rejected alternative.** An explicit declarative registry (an entry-points table or a
YAML/TOML catalog). That would give earlier, clearer errors and no import side-effects,
but it introduces a second source of truth that can drift from the code, and it breaks
the file-per-recipe convention the gallery and tests assume.

**Cost.** This is genuinely process-global, order-dependent, import-side-effect-driven
state. Tests must call `ensure_all_imported()` before the registry is populated. Plugins
reuse the same global, so a third-party plugin import can mutate core state, and plugin
attribution is computed by diffing the registry's full-name set before/after import —
which is not thread-safe. A forgotten import line in a modality `__init__.py` silently
omits a recipe with no error.

### 2.2 `RecipeContract` — the marker base and its honest limitation

`RecipeContract` is a near-empty pydantic `BaseModel` whose only content is
`model_config = {"arbitrary_types_allowed": True}`. Each recipe subclasses it to declare
real fields.

**Rationale.** A uniform validation entry point (`entry.contract.model_validate` /
`entry.contract(**mapped)`) used by the resolver and render loop, while
`arbitrary_types_allowed` permits numpy arrays and other non-pydantic field types.

**The honest limitation — and the most-overstated claim in the codebase.** The module
docstring says "every recipe has a pydantic contract that validates the data it
accepts." `arbitrary_types_allowed=True` *globally disables* pydantic coercion and
validation for any non-standard field type. A recipe declaring a raw `np.ndarray` field
— the common case, since recipes plot arrays — gets **no schema checking at all**.
Validation rigor is silently opt-out per field. The strongest defensible scoping of the
claim is "validates declared scalar/typed fields"; array-shaped inputs, which recipes
most need validated, are unchecked. This must be either documented on the class or
narrowed in the claim before review.

### 2.3 `RecipeMetadata` and the embedded `StatisticalContract`

`RecipeMetadata` is a frozen dataclass (hashable, comparable) carrying catalog metadata:
name, modality, family, `answers_question`, required/optional fields, and a `kw_only`
`StatisticalContract` field with a `default_factory` producing an all-permissive
instance. Frozen-ness lets the contract sit on the otherwise-frozen metadata without
breaking equality/hashing; the permissive default is an explicit backwards-compat
guarantee so the ~390 untagged recipes render unchanged.

**Cost / the indistinguishability problem.** Because the default is all-permissive,
"no contract" and "explicitly permissive contract" are indistinguishable. A reviewer
cannot tell whether a recipe was audited and deemed permissive or simply never tagged.
Only 45/471 recipes declare a real `statistical_contract`, so the rigor guarantee is
opt-in and sparse, and the subsystem currently cannot report audit coverage — a fair
thing for a reviewer to ask for.

### 2.4 `RecipeFamily` and the split-brain family taxonomy

`RecipeFamily` is a closed `StrEnum` of ~19 geometry families that drive the
`tests/quality_rules/` CI gates (a "radar must have a polar axis and ≥2 drawn objects",
a "ladder must have ≥3 bars"). Invalid enum values raise at construction.

**But** the family-recommender and bias-auditor deliberately treat family as a free
string (`meta.family.value`) so plugins and author-recipes can declare families CI does
not gate. The result is a split-brain: core enforces a closed enum, but downstream code
must defensively do `meta.family.value if hasattr(meta.family, "value") else
str(meta.family)`, betraying that family is sometimes an enum and sometimes a bare
string. This is a deliberate decoupling (extensibility for author recipes) that reads as
inconsistency.

### 2.5 The closed-taxonomy enforcement asymmetry

`RecipeFamily` is a `StrEnum`, so invalid values raise at construction. But the three
statistical taxonomies — `DistributionAssumption`, `MultipleComparisonsPolicy`,
`IndependenceStructure` — are `typing.Literal` aliases on a *vanilla* `@dataclass`
(`StatisticalContract`). The module docstring calls them a "closed taxonomy," but
`StatisticalContract(distribution_assumption="gausian")` constructs **without error** —
the closed taxonomy is enforced only by static type-checkers, never at runtime. Two
"closed taxonomies" in the same subsystem with two different runtime-validity guarantees.
A reviewer will reasonably expect parity. The fix is to make `StatisticalContract` a
pydantic model, add a `__post_init__` membership assertion, or promote the three to
`StrEnum`s.

### 2.6 The supporting primitives

The rest of `core/` is the shared visual contract: `Palette` (a frozen dataclass with
cyclic `__getitem__` so `palette[3]` never `IndexError`s — which silently hides
"too many groups" bugs by repeating a color — plus a semantic name map and its own
parallel registry mirroring the recipe registry pattern); `_FontSizes`/`_LineWidths`
singletons and `apply_base_style` (which mutates global `mpl.rcParams`, making it
process-global and not thread-safe, with PDF/PS fonttype 42 and `svg.fonttype "none"`
for editor-friendly vector output); and the drawing primitives including the notorious
`add_halo_label`, which keeps its name and `halo_color`/`halo_width` kwargs but
`del`-etes them and emits a plain `ax.text` — the "halo" is an intentional no-op kept for
API compatibility across ~390 callers. The primitive's name now actively lies about its
behaviour, which is the cleanest small example of the "elevation-era backwards-compat
debt" the whole system carries.

---

## 3. Subsystem-by-subsystem decision walks

### 3.1 Recipes pattern (`recipes/`)

**Purpose.** The 471-recipe authoring convention: a self-contained module per figure,
factored for consistency across 20 modalities.

**Key decisions.**
- *Four-artifact template per file* (contract, `_demo`, `_META`, `render`). Rationale:
  per-file reviewability and zero-external-data runnability. Rejected: class-based or
  entry-point recipe models. Cost: boilerplate, no type-level enforcement.
- *Registration as import side-effect.* Rationale: single ground-truth catalog. Rejected:
  static TOML manifest. Cost: a forgotten `__init__.py` import line silently drops a
  recipe — and there is no CI guard that every `.py` file in a modality directory is
  actually imported.
- *Per-modality `_aesthetic.py` with one `AESTHETIC` object.* Rationale: visual family
  coherence, palette-drift prevention. Rejected: single global stylesheet (erases
  per-modality identity) and raw rcParams (too coarse for label vocabularies / ratio
  colormaps).
- *Optional per-modality `_shared.py` of nested sub-contracts* (e.g. `LoadingsBundle`,
  `KinematicFeatureBundle`) so multiple recipes consume the same canonical data atom.
  Rationale: assemble data once, feed many figures. Cost: applied to only **7 of 20**
  modalities, so the "data atom reuse" guarantee is modality-specific, not a subsystem
  property — and it is undocumented why.
- *`RecipeFamily` → `RULES` coupling* for geometry quality gates. Rationale: one
  geometry test covers all recipes of a family. Cost: gates check crude geometry (line/
  patch counts), not scientific correctness, and the enum is a fixed closed set new
  figure types must be shoehorned into.

**Key abstractions.** `RecipeContract`, `RecipeMetadata`, `RecipeFamily`,
`register_recipe`, `_RegistryEntry`, `ModalityAesthetic`, and the `_shared.py` sub-contracts.

**Connection to the rest.** Recipes are the leaf consumers of `core/`; everything
downstream (discovery, databind, manuscript) reads them only through the registry.

### 3.2 Discovery (`manifest/{scoring, tag_taxonomy, auto_tag, catalog, intake, project_scan}.py`)

**Purpose.** Turn a user's project into a ranked shortlist of recipes via a
locked-weight scoring rubric, a closed tag taxonomy, a deterministic auto-tagger, the
agent-facing JSON index, an 8-question intake, and a project-directory scanner that
pre-fills the intake.

**Key decisions.**
- *`WEIGHTS` as frozen `MappingProxyType` constants in an append-only `WEIGHTS_HISTORY`,
  with import-time assertions that every version sums to 1.0.* Rationale: rankings must
  be reproducible and auditable; a weight change is "a spec amendment, not a refactor."
  Rejected: configurable/learned weights. Cost: re-tuning requires a code change plus
  release.
- *Asymmetric `match_bool`*: a `factorial:false` recipe in a non-factorial project scores
  0.0, not 1.0 — only *affirmative* alignment earns weight. Pinned to the worked
  arithmetic in `RECIPE_SELECTION.md`. Cost: scores skew low; an all-False project can
  never hit 1.0 on those terms.
- *Hand-tuned match carve-outs* (`static/static=0.3`, `mixed/mixed=0.7`, generic
  anchor=0.5) that fire *before* the exact-match branch, each traced to a defect fix and a
  worked example. Cost: order-of-branch matters, and `mixed/mixed=0.7` is the most
  surprising consequence — a mixed recipe on a mixed profile never scores full weight.
- *Fully deterministic lexicographic tie-break* `(-score, -anchor_strength,
  -modality_locality, wave_oldest_first, name_ascending)` for byte-stable output.
- *`emit_index_json` auto-pins `PANELFORGE_BUILT_AT`/`PANELFORGE_GIT_COMMIT`* to fixed
  sentinels (restored in a `finally`) so the committed index is byte-stable for
  `git diff --exit-code`. Cost: it mutates process-global `os.environ` inside a function
  named "emit ... json" — surprising and not thread-safe.

**Key abstractions.** `ProjectProfile`, `ScoredRecipe`, `WEIGHTS`/`WEIGHTS_HISTORY`, the
`match_*` funnel, the `Tag*` `StrEnum`s + `validate_tag`, `auto_tag_recipe`,
`build_index`/`emit_index_json`, `IntakeQuestion`/`INTAKE_QUESTIONS`, `scan_project`.

**Connection.** Reads the registry; feeds the CLI, MCP scorer, and recommendation
layer. The locked rubric is also the input to the offline weight-calibration loop.

**Sharpest gap.** The auto-tagger emits a wave label
`v1.2.0-beta-biophysics_scaling` that does **not** exist in the `TagWave` enum (which has
`v1.2.0-beta-actin_microtubule_morphometry`); `validate_tag` would raise
`TagValidationError` on it. It is latent only because the index path does not re-validate
auto-tags — a real taxonomy/auto-tagger desync to fix and test-pin before publication.

### 3.3 Recommendation (`manifest/{family_recommender, novelty_scout, scout}.py`)

**Purpose.** Three read-only, advisory pipelines: data-driven figure-family
recommendation (E8), literature-novelty classification via a Consensus client (E9p1), and
a project scout that walks a project and synthesizes a multi-figure narrative plan
(E9p2). None auto-selects or auto-executes — the "human chooses" stance is preserved
throughout.

**Key decisions.**
- *Lazy imports of pandas/requests/PyYAML* inside the functions that need them, so the
  three modules stay importable in a minimal install. Cost: import errors surface late.
- *Frozen dataclasses with hand-written `to_dict`/`from_dict`* for an immutable,
  deterministic value layer the scout re-hydrates. Cost: manual serialization must be kept
  in sync by hand.
- *Transparent additive-evidence scoring* (`bump(family, weight, reason)`, clipped to
  [0,1], rationale = joined reasons). Rationale: every recommendation is fully
  explainable, no opaque model. Cost: weights are hand-tuned magic numbers with no
  empirical calibration, and unlike the novelty thresholds they are *not* externalized.
- *First-match-wins novelty thresholds* including a distinctive "stale single paper → 
  ULTRA_NOVELTY" rule. Cost: an assertion, not validated against ground truth.
- *Protected supporting panels* (controls/baselines/QC) never demoted by the novelty
  filter, via `is_supporting_panel`. Cost: keyword-substring protection is brittle and the
  keyword set is duplicated, with different membership, in `scout.py`.
- *4-way Consensus fallback ladder* (explicit client → `use_mock` → API key → mock with
  `RuntimeWarning`). Cost: the offline `MockConsensusClient` returns n=0, which classifies
  as ULTRA_NOVELTY, so the default offline run rates everything maximally novel (loudly
  warned, not silent).

**Connection.** Reads the registry and statistical contracts; the scout composes
family-recommender + novelty-scout + collision into one `ProjectScoutReport`. Read-only:
it writes only a YAML plan the human must approve.

**Sharpest gap.** `recommend_families` emits family strings `comparison`, `correlation`,
`factorial`, `equivalence` that do **not** exist in `RecipeFamily`, so they can *never*
match a registered recipe and always report 0 matches — then get flagged as gaps. The
test suite documents this ("not in RecipeFamily enum → guaranteed 0 matches"), so it is
by-design "gap-only" author-recipe families driving the fill-gap workflow, but it reads
like a bug and is under-documented at the API surface (§4, §6).

### 3.4 Databind & render (`manifest/{data_bridge, render_loop, render_cache, figure_composition, figure_schema}.py`)

**Purpose.** Bind discovered data files to recipe contracts, drive a non-fatal per-recipe
render loop, compose multi-panel figures from a YAML `FigureSpec`, and short-circuit
re-rendering via a sha-keyed incremental cache.

**Key decisions.**
- *Strictly ordered 3-pass mapper* (exact → fuzzy `difflib`@0.8 → LLM fallback) with
  monotonic confidence (1.0 / [0.7,0.95] / 0.5–0.7). Rationale: cheap deterministic passes
  resolve the common case at zero cost and full reproducibility; the expensive
  non-deterministic LLM is reached only when both deterministic passes fail. Rejected: a
  single embedding ranker (makes every binding non-deterministic and adds a model dep).
- *LLM pass fail-closed and hallucination-guarded*: `anthropic` is lazy-imported, gated
  behind `safety.is_llm_allowed()` and `ANTHROPIC_API_KEY`, memoized per
  `(field, sorted-candidates)`, and any returned column not in `candidate_columns` is
  rejected. Rationale: PHI never reaches an LLM even if a key is set; an invented column
  fails closed at bind time, not as a confusing render-time `KeyError`.
- *Failure classification in the render loop*: per-recipe-non-fatal (`ValidationError`,
  generic `Exception`) vs. environmental-fatal (`ImportError`/`OSError` → re-raised as
  `EnvironmentalFailure`, halts). Rationale: one bad recipe should not abort a 20-recipe
  batch, but a missing matplotlib should. `KeyboardInterrupt` propagates.
- *Soft-on-corruption render cache* (missing/corrupt/IO-error/schema-mismatch all warn and
  return empty): the cache is a perf optimization, never a correctness gate. Atomic writes
  via tempfile + `os.replace`; O(1) per-panel staleness via a `dict[panel_id]`.
- *Composition is all-or-nothing*: each panel flows through the same
  `get_recipe(name).render(contract, ax)`, but composition either fully succeeds or
  raises — a half-rendered Figure 1 is worse than a clean failure. `FigureSpec.layout` is
  a pydantic discriminated union (Grid/Gridspec/Freeform).

**Connection.** `data_bridge` adapters feed `render_loop`; `render_cache` is consumed by
`execute_plan`; `figure_composition` reuses the render core with stricter error semantics.

**Sharpest gaps.** `check_staleness` computes and stores `output_sha` but never compares
it — only `output_path.exists()` — so an externally-edited PDF is reported `fresh` and not
re-rendered. `compute_fully_bound` ignores confidence, so a 0.5-confidence LLM guess
renders without review. And `PanelSpec.data` / `aesthetic_overrides` / `shared_aesthetic`
are accepted by the schema but silently ignored by the engine (`_render_panel` always
calls `entry.demo_contract()` and discards `panel.data`) — the composition schema
over-promises (§7).

### 3.5 Stats & provenance (`manifest/{statistical_audit, provenance, reproducibility, power, power_families}.py` + `core/statistical_contract.py`)

**Purpose.** Pre-render statistical gatekeeping (contract → 13-rule audit →
RENDER/WARN/REFUSE), content-addressed provenance + reproducibility lockfiles, and an
adaptive power-analysis layer that sizes samples from a recipe's contract.

**Key decisions.**
- *The audit driver never raises*: `audit_recipe_against_data` always returns an
  `AuditReport`; callers decide whether to lift a "refuse" to
  `StatisticalContractViolation`. Rationale: separates policy from mechanism so the render
  loop, CLI, and sidecar each escalate differently.
- *Central `_DEFAULT_VERDICT` dict + escalation-only `refuses_when`*: a recipe author can
  tighten rigor (warn → refuse) but never de-escalate, keeping the gate monotone.
- *13 private rules of uniform signature in an ordered `_RULES` tuple*. Rationale: trivial
  driver loop, deterministic spec-traceable iteration, `None` = "rule does not apply."
  Cost: the rule set is hard-coded; third parties cannot register a 14th rule.
- *sha256 for figure/data bytes, git-blob sha for the recipe module*. Rationale: sha256 is
  dependency-free collision resistance; git-blob matches what a reviewer computes with
  `git hash-object`. Cost: outside git, `module_sha` is `None` and recipe-drift detection
  silently disables.
- *Power analysis splits a stable facade (`compute_power`/`compute_required_n`) from a
  lazily-imported formula layer*, with statsmodels/scipy lazy. Parametric formulas degrade
  gracefully where a closed form exists (t-test normal approx, correlation Fisher-z) but
  ANOVA/chi-square hard-raise without statsmodels. Nonparametric power uses a single
  Monte-Carlo MWU simulator for all four families — a documented proxy, not the actual
  test's power.

**Connection.** The contract is embedded in `RecipeMetadata`; the audit is consumed by the
render loop (best-effort) and the CLI verb; provenance is written per render; the lock
embeds a provenance-style record. The CLI bridges `RecipeFamily` → `compute_required_n`.

**Sharpest gaps.** The power family vocabulary is almost entirely disjoint from
`RecipeFamily` — only `coef_forest` overlaps — so `compute_required_n` raises `PowerError`
for ~18 of 19 families, and the one CLI power test only asserts the success path, masking
it. `replay_lock` reports `success=True` without re-rendering. And the
`refuses_when`-validated-against-a-rule-registry claim in the docstring is unimplemented:
the only consumer does a plain membership test, so a typo'd rule name silently never
escalates (§7).

### 3.6 Manuscript (`manifest/{execute_plan, manuscript_parse, manuscript_collision, manuscript_scaffold, manuscript_blueprint, manuscript_alignment}.py`)

**Purpose.** Manuscript orchestration: a tolerant execute-plan pipeline, a regex-based
manuscript parser, a collision-policy reconciler (E10), a blueprint inverse-importer, a
venue-aware scaffolder, and a pure-Python TF-IDF manuscript-alignment scorer (E7).

**Key decisions.**
- *`execute_plan` is end-to-end tolerant*: per-panel exceptions become `status="failed"`
  rows, missing optional subsystems are caught as `ImportError` soft-notes; only
  plan-load failure raises. Built during a swarm-build window where dependencies landed
  asynchronously. Cost: bare-except swallows genuine bugs into note strings.
- *Duck-typed access throughout* (`_panel_attr`/`_get`/`_attr` accept objects *or* dicts,
  no import of the owning class). Rationale: decouples from Build-A's evolving schemas,
  makes everything testable with plain-dict mocks. Cost: no static checking; a renamed
  field silently degrades to a default.
- *Regex-based parsing, not a LaTeX AST*; pylatexenc is an optional best-effort
  enrichment hook. Rationale: no hard LaTeX-parser dependency; the parser is tolerant and
  degrades to empty fields rather than raising. Cost: mishandles nested environments,
  verbatim, %-commented commands, custom macros — tolerable only because the collision
  detector treats captions as opaque prose.
- *Strictly non-destructive collision insertions* (`insert_block`/`append_new` write;
  flags are reported only; existing prose is never modified; insertions applied in
  ascending line order with cumulative offset tracking). Rationale: a manuscript is the
  user's intellectual artefact. The four-policy model (detect/update/propose/preserve)
  gives a graduated risk ladder.
- *Methods boilerplate pastes only literal `StatisticalContract` fields and never invents
  statistics.* Rationale: a figures tool must not hallucinate methods text a reviewer
  would treat as fact.

**Connection.** `execute_plan` orchestrates scaffold → render (via `render_loop`) →
caption → manuscript, hard-importing only `render_cache`; the blueprint and collision
modules lazy-cross-import the parser and scaffolder.

**Sharpest gaps.** `manuscript_blueprint`'s docstring claims it "reuses the TF-IDF
infrastructure from `manuscript_alignment`" but the code copy-pastes the six TF-IDF
helpers (triplicated across blueprint, alignment, and citation_inserter) and never
imports alignment — the claim is false. `insert_blocks_into_existing` is exported but
unused, and its "insert BEFORE" semantics disagree with the live "insert AFTER"
implementation in collision — a latent off-by-one trap. And "preserve" names two
different behaviours in `execute_plan` vs. `ManuscriptPolicy` (§7).

### 3.7 Auditors (`manifest/{venue_auditor, bias_auditor, xref_linter, claim_check, caption, citation_inserter, star_methods, reporting_checklists, status_dashboard, ci_runner}.py`)

**Purpose.** A family of independent, best-effort, non-mutating (except
`citation_inserter`) pre-submission auditors that read provenance sidecars and the parsed
manuscript to emit structured Pass/Warn/Fail reports, unified by a bundled CI runner and a
status dashboard.

**Key decisions.**
- *Metadata/provenance-driven, best-effort*: each check reads the figure's
  `<figure>.provenance.json` and produces a finding rather than raising, skipping
  gracefully when the contract is silent. `bias_auditor` "never inspects pixels"
  (deterministic, fast) — though `venue_auditor`'s color-blind check *is* pixel-based
  (Brettel/Viénot deuteranopia simulation), an asymmetry worth stating up front.
- *Three-valued claim verdicts*: `claim_check` marks a claim UNVERIFIABLE (not
  UNSUPPORTED) whenever there is no audit / missing field / un-parseable assertion; only a
  direct numeric contradiction yields UNSUPPORTED. Rationale: a screen that cries wolf
  gets ignored.
- *Venue rules as a single frozen `VENUE_RULES` table* of frozen `VenueRules` dataclasses
  (None = "no cap / skip"), hand-transcribed from each journal's Instructions to Authors.
  Cost: a snapshot with no dated provenance/URL, so rules can silently go stale.
- *Closed-taxonomy `StrEnum`s for finding kinds/severities* (no free-form strings) so
  reports stay stable across runs and JSON round-trips.
- *`citation_inserter` is the only mutating auditor and is defensive*: always backs up to
  `.bak`, refuses to double-cite a sentence that already has a citation, applies edits in
  reverse order so earlier offsets stay valid.
- *The CI runner sandboxes every step* behind a global try/except and a per-step
  dispatcher, mapping each auditor's bespoke verdict onto a common `StepStatus`, with
  `skip_missing_inputs` so early-phase projects run green.

**Connection.** All consume the provenance sidecar schema (an implicit, un-typed
cross-module contract). `ci_runner` is the integration hub, lazy-importing every other
auditor. None of the ten auditor modules is re-exported from `manifest/__init__.py` (kept
import-cheap; less discoverable).

**Sharpest gaps.** No single canonical figure-id form (`Figure 3A` vs. `Figure 3a` vs.
`figure_3a` vs. `fig:3a`), so cross-auditor correlation needs ad-hoc re-normalization. The
`claim_check` `|r| ≥ 0.1` default marks a 1%-of-variance correlation as SUPPORTED — a weak
magic number a reviewer will challenge. And a check that raises is recorded as a
`truncated_y_axis` finding (commented "# generic"), poisoning a real honesty-finding
bucket with internal errors (§7).

### 3.8 Extensibility & learning (`manifest/{recipe_authoring, vision_input, telemetry, weight_calibration}.py`, `plugins/`, `projects/`)

**Purpose.** Five loosely-coupled extension points: add recipes (authoring co-pilot +
plugins), seed intake from reference figures (vision), orchestrate across projects
(registry/portfolio), and close a privacy-gated active-learning loop (opt-in telemetry →
offline weight calibration).

**Key decisions.**
- *Recipe authoring generates source TEXT* (a self-registering module string), not live
  objects, so a scaffolded recipe lands on disk identical in shape to the hand-written
  ones and participates in the same test/gate machinery. Split into
  `scaffold_recipe`/`write_scaffold`/`render_demo_to_gallery` so the pure build, the
  clobber-refusing I/O, and the optional matplotlib render are separable.
- *Plugin discovery is dual-path and never automatic*: entry-points group
  `panelforge.plugins` for installable packages, plus a walked `panelforge_plugins/`
  directory for single files; callers must invoke `discover_all_plugins` explicitly so the
  registry stays deterministic in tests. Attribution is computed by registry set-diff (not
  declared). Cost: directory plugins `exec` arbitrary user code with no sandbox; attribution
  is not thread-safe.
- *Vision is fail-closed behind a layered gate* (`safety.is_vision_allowed`: clinical
  refuses unconditionally, research treats API-key presence as opt-in, public default-on),
  cached by image sha-256, and sends image bytes + recipe Python but **never** CSV/Parquet
  values. Cost: the closed-taxonomy family guard silently *drops* a hallucinated family
  rather than surfacing it.
- *The cross-project registry stores PATHS not DATA* in a per-user XDG YAML; corruption
  renames to `.broken-<ts>` and returns an empty registry instead of bricking the CLI.
- *Telemetry is opt-in via a VCS-tracked `telemetry: opt-in` line*, parsed with a
  zero-dependency regex (not pyyaml) so the path stays fail-closed, atomic writes,
  `log_invocation` swallows all exceptions and returns "".
- *Weight calibration is strictly offline and deterministic*: grid-searches ±0.05
  perturbations of the locked weight vector, re-uses logged sub-scores, and only emits a
  JSON proposal a maintainer applies by hand behind a `SCORING_RUBRIC_VERSION` bump.
  Nothing auto-mutates weights.

**Connection.** Authoring embeds `core` symbols in generated text; plugins reuse
`register_recipe`; vision mirrors `project_scan.InferredAnswer`; weight-calibration is the
only intra-cluster coupling to `scoring`.

**Sharpest gap.** `telemetry.log_invocation` enforces only the project-YAML opt-in and not
`safety.is_telemetry_allowed`, so the clinical data-class invariant holds only for the MCP
caller, not the core library function (§4.1, §7).

### 3.9 Safety & MCP (`safety/`, `mcp/`)

**Purpose.** The privacy-by-construction data-class layer (covered as §1.4 and revisited
in §4.1) plus a lazy-loaded MCP server exposing the registry, scorer, index, provenance,
projects, and double-gated telemetry as Claude tools.

**Key decisions.**
- *Policy cells are documented strings, not booleans* (`enabled`/`opt_in`/`disabled`/
  `off`/`redacted`/`full`/`allowed`/`disallowed`), because the spec distinguishes
  forced-OFF-no-override from default-OFF-but-opt-in-able — a bool collapses the two.
- *RESEARCH is the default class* (not clinical or public): clinical-by-default silently
  breaks demo users, public-by-default silently exposes regulated users; research is the
  opt-in middle.
- *MCP SDK is lazy-imported* inside `create_server`/`serve_stdio`, re-raised as
  `MCPUnavailableError` so the base install needs no `[mcp]` extra.
- *Telemetry is double-gated*: at server construction AND in every handler at call time,
  so a mid-session `data_class` flip cannot leave a tool exposed.
- *Every tool handler returns a `{"success": ...}` envelope*; exceptions are caught at
  three levels and never escape, because an uncaught exception crashes the stdio JSON-RPC
  framing.
- *Recipe `inputSchema` is auto-generated from the pydantic contract* via
  `model_json_schema()` so client and server validation never drift.

**Connection.** Reads `core` + `scoring` + `provenance` + `projects` + `telemetry`; the
safety predicates are consumed by caption, data_bridge, vision, provenance,
status_dashboard, and the CLI.

**Sharpest gap.** The `expose_scorer`/`expose_index`/`expose_provenance`/`expose_projects`
flags do **not** gate registration — only `register_recipe_tools` actually wires the SDK
decorators; the other five `register_*_tools` are no-ops, and the scorer/index/provenance/
project tools are unconditionally added regardless of the flags. No `call_tool` handler is
tested at all (§4.6, §7).

### 3.10 Surfaces (`cli/`, `notebook/`, `adapters/`, `themes/`, `transforms/`, `templates/`)

**Purpose.** The user-facing presentation layers — a large Click CLI, a Jupyter API +
IPython magic, the data-adapter registry, per-venue rcParams themes, declarative DataFrame
transforms, and static scaffold templates — all thin dispatch over the
manifest/core/safety engine.

**Key decisions.**
- *The CLI is a single ~4689-line Click module where every subcommand lazy-imports its
  `manifest/*` implementation in-body*, so `figures --help` and the base install stay
  fast and dependency-light (top-level imports are only click/json/logging/adapters/core/
  catalog). Cost: navigability — at ~4.7k lines the lazy-import discipline could be kept
  just as well by a command-per-module layout.
- *`cli` was promoted to a package in v3.9.0* solely to co-locate the textual TUI
  (`tui_scout.py`), with a `__main__.py` shim preserving `python -m panelforge_figures.cli`.
- *Adapters are callables behind a Protocol + dict registry with a `local.<name>` escape
  hatch* that `exec`s `figures/adapters/local/<name>.py` from the manuscript repo. The
  pickle/npz adapters are hardened (suffix gate, cwd containment, `allow_pickle=False`).
- *`derive_columns` restricts user expressions to `pandas.DataFrame.eval` strings*, not
  Python `eval` — manifests are shared config and must not be a code-execution surface.
  (The notebook magic deliberately *does* use Python eval, because that context is the
  user's own REPL.)
- *Themes are a self-autoloading registry* (a one-file drop-in calling `register_theme`
  with a zero-arg callable returning an rcParams dict). Transforms, by contrast, are a
  closed fixed dict of six pandas ops — an extensibility asymmetry with adapters.
- *Notebook returns frozen dataclasses that duck-type Jupyter's `_repr_html_`/`_repr_png_`*
  rather than importing IPython, keeping the base install slim.

**Connection.** The CLI dispatches into nearly every manifest module; adapters/transforms
feed `resolver.py` in the data → recipe pipeline; themes layer on `core.style`.

**Sharpest gaps.** The CLI reaches into private manifest internals (`RecipeBinding as _RB`
in `generate_cmd`; `_resolve_consensus_client` in `tui_scout.py`) wrapped in defensive
excepts that mask upstream renames. The `templates/` directory has no in-package consumer
and `outputs.gitignore` is not even packaged by the current globs. `notebook.render`
accepts a `data=` kwarg it silently ignores. And `nature.py` ships a dead
`"semibold" if False else "bold"` conditional (§7).

---

## 4. Cross-cutting design decisions

These are the decisions that span subsystems — the connective tissue a reviewer reads as
"the architecture," distinct from any one module.

### 4.1 The data-class safety gate

A single `DataClass` `StrEnum` (clinical/research/public) resolves to a `DataClassPolicy`
of string-valued cells, held in one locked `_POLICIES` table. Pure `is_*_allowed`
predicates are the gate API, consumed at every network/persistence site. `data_class`
lives in one module-global, settable only via `set_data_class` (never an env var), so the
override surface is auditable. This is the structural expression of principle 1.4.

The two honest caveats the author must own: (1) enforcement is by *audit of gate sites*,
not a structural choke-point — there is an integration test proving the `data_bridge`
gate fires under clinical, which is the strongest defense, but nothing prevents a future
code path from skipping the predicate; (2) `telemetry.log_invocation` does not consult
`is_telemetry_allowed`, so the clinical-forces-telemetry-off invariant holds for the MCP
wiring but not the core library function. Both are fixable; (2) is the higher priority.

### 4.2 The closed-taxonomy tag system

`tag_taxonomy.py` defines `TagAnchor`/`TagDimensionality`/`TagDynamics`/`TagWave` as
`StrEnum`s validated at YAML-parse time, with an `unknown` sentinel for low-confidence
auto-tags and forward-compat *silent skip* for unrecognized tag names. The auto-tagger is a
pure, deterministic, stdlib-only regex engine that falls back to `unknown` rather than
guessing, paired with a curated YAML override layer (`_merge_tags` classifies provenance as
auto/override/merged). The design degrades brittleness to `unknown` rather than to wrong
tags.

The cost — and a real gap — is that the silent-skip-for-unknown-names means a *misspelled
key* (`anchorr: DISCC1`) passes validation entirely, which is exactly the class of typo the
module docstring claims to catch. The guarantee holds only for correctly-spelled keys.

### 4.3 The locked scoring rubric

`WEIGHTS` are frozen `MappingProxyType` tables in an append-only `WEIGHTS_HISTORY`, with
import-time 1.0-sum assertions. Re-tuning is a versioned spec amendment, not a refactor; a
1.1.0 "shadow-mode" entry is the opt-in experimentation escape hatch. The match functions'
constants are hand-tuned to reproduce the worked arithmetic in `RECIPE_SELECTION.md`. The
honest framing for a reviewer: this is a transparent expert system whose rules are
*asserted, not learned* — defensible as auditable and deterministic, indefensible as an
empirically-calibrated model. The weight-calibration loop exists precisely to let a
maintainer re-tune *with* a version bump, never silently.

### 4.4 The provenance / reproducibility chain

Render → content-addressed sidecar (sha256 figure/data bytes, git-blob recipe sha,
resolved contract, audit verdicts; schema 1.1.0) → optional reproducibility lock (env
snapshot, RNG seeds, data hashes). All JSON is `indent=2, sort_keys=True` for clean
diffs; `PANELFORGE_BUILT_AT` overrides the one non-deterministic field. This is the
spine of principle 1.5. The chain is genuine and verifiable for the inputs it tracks; the
caveats (output-mutation not detected, `module_sha` git-only, `replay_lock` does not
re-render, RNG determinism is the caller's job) are collected in §7 and answered in §6.

### 4.5 The auditor pattern

Ten independent, frozen-dataclass-based, `to_dict`-serializing, `render_*_markdown`-emitting,
sandboxed-orchestrator auditors, each reading the provenance sidecar and the parsed
manuscript, unified by `ci_runner` mapping every bespoke verdict onto a common
`StepStatus`. The consistency of this pattern across ten modules — every one with a
dedicated test file — is one of the system's genuine engineering strengths and should be
presented as such. The weaknesses are the absence of a shared verdict enum (each auditor
invents its own three-band vocabulary, hand-mapped in `ci_runner`) and the un-typed
provenance-sidecar cross-module contract.

### 4.6 The MCP surface

A lazy-loaded stdio server exposing the registry, scorer, index, provenance, projects, and
double-gated telemetry as Claude tools, with auto-generated input schemas and a
never-escape `{"success": ...}` envelope. It is the concrete expression of principle 1.3.
Its two real liabilities are the non-functional `expose_*` flags (a reviewer who sets
`expose_scorer=False` still gets scorer tools) and the total absence of `call_tool`
handler tests — the content/dispatch layer is validated only indirectly through the
underlying unit tests. Both must be documented as partially-implemented or fixed.

---

## 5. The dependency map

The system is a strict layering: `core/` is a true leaf foundation that imports no sibling
subsystem at module scope (its only inward dependency is a *lazy* import of `recipes`
inside `ensure_all_imported`). Everything else depends inward on `core`.

```
                            ┌──────────────────────────────────────────┐
                            │                  core/                    │
                            │  contract.py  ── register_recipe,         │
                            │                  RecipeContract,          │
                            │                  RecipeMetadata,          │
                            │                  RecipeFamily,            │
                            │                  _REGISTRY                 │
                            │  statistical_contract.py ── StatisticalContract
                            │  aesthetic_base.py ── ModalityAesthetic   │
                            │  palette.py / style.py / primitives.py    │
                            └──────────────────────────────────────────┘
                                   ▲                       ▲
                  (import side-effect│registration)        │(reads contracts/metadata)
                                   │                       │
        ┌──────────────────────────┴───────┐              │
        │            recipes/               │              │
        │  471 modules × {Contract,_demo,   │              │
        │   _META,@register_recipe render}  │              │
        │  per-modality _aesthetic.py       │              │
        │  optional _shared.py sub-contracts│              │
        └──────────────────────────┬────────┘              │
                                   │                       │
                                   │ (ensure_all_imported  │
                                   │  populates registry)  │
                                   ▼                       │
        ┌──────────────────────────────────────────────────┴───────────────────────┐
        │                                manifest/                                   │
        │                                                                            │
        │   DISCOVERY        scoring · tag_taxonomy · auto_tag · catalog ·           │
        │                    intake · project_scan                                   │
        │   RECOMMENDATION   family_recommender · novelty_scout · scout              │
        │   DATABIND/RENDER  data_bridge · render_loop · render_cache ·              │
        │                    figure_composition · figure_schema · resolver           │
        │   STATS/PROV       statistical_audit · provenance · reproducibility ·      │
        │                    power · power_families                                  │
        │   MANUSCRIPT       execute_plan · manuscript_{parse,collision,scaffold,    │
        │                    blueprint,alignment}                                    │
        │   AUDITORS         venue_auditor · bias_auditor · xref_linter ·            │
        │                    claim_check · caption · citation_inserter ·             │
        │                    star_methods · reporting_checklists ·                   │
        │                    status_dashboard · ci_runner                            │
        │   LEARNING         recipe_authoring · vision_input · telemetry ·           │
        │                    weight_calibration                                      │
        └───────┬───────────────────┬────────────────────┬───────────────────┬──────┘
                │                    │                    │                   │
   (lazy: is_*_allowed gates)  (reads registry)   (reads registry)    (reads scoring)
                │                    │                    │                   │
                ▼                    ▼                    ▼                   ▼
        ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
        │   safety/    │   │  plugins/    │   │  projects/   │   │  cli/ · mcp/ ·   │
        │  (leaf;      │   │ (reuses      │   │ (path        │   │  notebook/       │
        │   pure       │◄──┤  register_   │   │  registry)   │   │  adapters/themes/│
        │   predicates)│   │  recipe)     │   │              │   │  transforms/     │
        └──────────────┘   └──────────────┘   └──────────────┘   └──────────────────┘
                ▲                                                          │
                └──────────────── (cli/mcp/notebook consult safety) ──────┘

Layer rule:   core  ──►  recipes  ──►  manifest  ──►  {cli, mcp, notebook}
              safety is a pure leaf consulted by manifest + surfaces.
              plugins + projects sit beside manifest, reusing core's registry.
              Cross-subsystem calls inside manifest/ are almost all LAZY imports
              (an elevation-era discipline so each module stays independently
              importable before its dependencies exist).
```

The two architectural facts a reviewer should take from this diagram: (1) `core/` is a
clean leaf — the dependency direction is never violated; (2) within `manifest/`, the
near-universal use of lazy imports is what lets the asynchronous-build model work, at the
cost of import errors surfacing at call time rather than import time.

---

## 6. Questions a reviewer will ask

Twelve questions a skeptical JOSS reviewer is most likely to ask, with the crisp, honest
answers.

**Q1. Your registry is mutable global state populated by import side-effects — isn't that
brittle?**
Yes, it is genuinely process-global and order-dependent, and it forces
`ensure_all_imported()` before any query. The defense: it is a deliberate plugin-friendly
design (plugins reuse the same decorator; duplicate names raise `ValueError` at import),
it is test-backed (`test_contracts.py`), and the import-time cost is bounded. The honest
limit: it is not thread-safe and a forgotten `__init__.py` import line silently omits a
recipe. I would add a CI test asserting every `.py` file in a modality is imported.

**Q2. You claim "every recipe has a pydantic contract that validates the data it accepts."
Does it?**
Only for declared scalar/typed fields. `RecipeContract` sets
`arbitrary_types_allowed=True`, so raw `np.ndarray` fields — the inputs recipes most need
validated — bypass pydantic entirely. I am scoping the claim before review and documenting
the limitation on the class.

**Q3. Where do the scoring weights come from?**
They are a designed, versioned editorial rubric (sum-to-1.0-asserted, frozen,
shadow-mode-extensible), not an empirically-calibrated model. The match-function constants
(0.3/0.5/0.7/0.8) are hand-tuned to reproduce the published worked examples in
`RECIPE_SELECTION.md`. Defensible as a transparent expert system; honestly *not* a learned
model, and the recommender weights specifically are not externalized for re-tuning.

**Q4. The statistical-rigor contract looks like vaporware — is it real?**
It is real but opt-in: 45/471 recipes declare one, with an explicit all-permissive default
so legacy recipes are unaffected. The audit is a deliberately conservative heuristic gate
(KS at p<0.01, missingness>30%, etc.), not a statistician. Two honest gaps: "no contract"
is indistinguishable from "permissive contract," and the subsystem cannot currently report
audit coverage. The `refuses_when`-is-validated-against-a-rule-registry docstring claim is
unimplemented and will be fixed or reworded.

**Q5. Is the reproducibility claim real?**
Content-addressing is genuine and reviewer-verifiable (`git hash-object` reproduces
`module_sha`; sorted-keys JSON diffs cleanly). The honest caveats: provenance detects
output *deletion* but not output *mutation* (`output_sha` is stored, never compared);
`module_sha` is `None` outside a git tree, silently disabling recipe-drift detection;
`replay_lock` in v2.2.0 detects env drift but does not re-render, so "replay success" ≠
"bytes reproduced"; RNG determinism is the caller's responsibility.

**Q6. The four families `comparison`/`correlation`/`factorial`/`equivalence` never match a
recipe — is that a bug?**
No, it is by-design "gap-only" author-recipe families that drive the `fill-gap` workflow,
and the test suite documents it. But the boundary is under-documented at the API surface
and looks like a bug to a fresh installer; I am documenting it explicitly in the
`recommend_families` docstring and gap rationale.

**Q7. Is the power-analysis feature actually usable from the CLI?**
The formula math is sound and formula-level tested, but the CLI integration is broken for
~18 of 19 recipe families because `RecipeFamily` values don't match the power family
slugs (only `coef_forest` overlaps), so `compute_required_n` raises for the rest — and the
one CLI test masks this by only asserting the success path. This is a real wiring gap (not
a math gap) that needs an explicit `RecipeFamily → power-family` mapping and a regression
test.

**Q8. Your regex LaTeX parser will silently mis-parse real manuscripts.**
True at the margins (nested environments, custom macros, %-escaped commands). The
mitigation: the only downstream consumer treats captions as opaque prose, the optional
pylatexenc hook gives a higher-fidelity path, and collision is insert-only — so the failure
mode is degraded matching, never corruption.

**Q9. The bias auditor never looks at the figure — how can it catch a truncated axis?**
It checks the declared contract/audit metadata against the data summary, so it catches
honesty defects *encoded in the recipe*; a defect introduced by hand-editing the rendered
PDF is out of scope by design. Note the asymmetry I state up front: the venue auditor's
color-blind check *is* pixel-based, so the cluster is not uniformly metadata-only.

**Q10. Your privacy claims are strong — is the clinical gate actually enforced?**
The policy schema invariants (categorical-only telemetry profile, atomic writes,
hash redaction, VCS-tracked opt-in) are solid, and there is an integration test proving the
`data_bridge` LLM gate fires under clinical. The one real gap: `telemetry.log_invocation`
enforces only the project-YAML opt-in and not `safety.is_telemetry_allowed`, so the
clinical-forces-telemetry-off invariant holds for the MCP path but not the core function.
Fixable by a lazy `is_telemetry_allowed()` call mirroring the vision gate.

**Q11. Directory plugins `exec` arbitrary code — is that safe?**
It executes untrusted code by design, which is standard for a plugin system, but it is
undocumented as a trust boundary and discovery is at least explicit/opt-in (never automatic
at import). I am adding an explicit trust-boundary note to the module and function
docstrings, matching the privacy call-outs the projects and telemetry modules already
carry.

**Q12. Why is `cli/__init__.py` 4689 lines — isn't that unmaintainable?**
The size is the deliberate consequence of the lazy-import contract (every command imports
its heavy implementation in-body so `figures --help` and the base install stay fast). The
cost is navigability, and the right refactor — a `cli/commands/*.py` layout that preserves
the same lazy loading — is the single highest-value structural improvement in the surfaces
cluster. It is a maintainability issue, not a correctness bug.

---

## 7. Known structural debt

> **Status (2026-06): this register is the ORIGINAL pre-remediation snapshot.**
> The HIGH items (#1–#5) were resolved in PRs #96–#97; the MEDIUM/LOW tail
> (#6–#22) in PRs #97–#98; and a follow-up adversarial re-audit closed the
> residual edge cases it surfaced (telemetry write/read gate, power
> optional-dependency error translation, multi-letter figure-id stems, atomic
> modality registration, MCP list/dispatch symmetry). Item #17
> (`add_halo_label`) is an intentional, documented compatibility shim, not a
> defect. The entries below are kept verbatim as the historical findings and are
> each now covered by a regression test — read their present-tense wording as
> "as originally found", not "as currently shipped".

An honest inventory of the thin, weak, and over-promising areas, so the author is not
blindsided. Ordered roughly by severity.

**High — claim/implementation gaps a reviewer running the code can trip:**

1. **Power analysis is reachable for ~1 of 19 recipe families.** The `RecipeFamily` enum
   and the power-family vocabulary are almost disjoint (only `coef_forest` overlaps), so
   `compute_required_n` raises `PowerError` for every other family. The lone CLI power test
   only asserts the success path, hiding it. *Fix: an explicit family-mapping table + a
   per-family regression test.*

2. **`telemetry.log_invocation` bypasses the data-class gate.** It checks only the
   project-YAML opt-in, not `safety.is_telemetry_allowed`, so a clinical project with
   `telemetry: opt-in` would write `usage.jsonl`. *Fix: add a lazy `is_telemetry_allowed()`
   no-op-if-closed check inside `log_invocation`.*

3. **The `refuses_when`-validated-against-a-rule-registry claim is false.** The
   `statistical_contract.py` docstring promises rule-name validation at audit time; the only
   consumer does a plain membership test, so a typo'd rule name (`underpowred`) silently
   never escalates. *Fix: implement the validation or correct the docstring.*

4. **The auto-tagger emits a wave label that fails its own taxonomy.**
   `v1.2.0-beta-biophysics_scaling` is not in `TagWave`; `validate_tag` would raise. Latent
   only because the index path skips re-validation. *Fix: reconcile the strings + add a test
   that every emittable wave validates.*

5. **The MCP `expose_*` flags don't gate anything.** Four of six `register_*_tools` are
   no-ops; scorer/index/provenance/project tools are added unconditionally. No `call_tool`
   handler is tested. *Fix: honor the flags inside `_list_tools`/`_call_tool` or document
   them as reserved; add handler-level tests.*

**Medium — over-promising schema/API surface and silent degradations:**

6. **Composition schema over-promises.** `PanelSpec.data`, `aesthetic_overrides`, and
   `FigureSpec.shared_aesthetic` are accepted but silently ignored — `_render_panel` always
   calls `demo_contract()` and discards `panel.data`. A YAML author pointing a panel at a
   real CSV silently gets demo data. *Fix: wire the fields or mark them
   not-yet-consumed like `PartitionedPanelSpec` already is.*

7. **Render cache detects output deletion but not mutation.** `output_sha` is computed and
   stored but never compared in `check_staleness`; an externally-edited PDF reports `fresh`.
   *Fix: compare the on-disk sha, or drop the column and document the scope.*

8. **No confidence floor in the bind→render path.** `compute_fully_bound` never consults
   `FieldBinding.confidence`, so a 0.5-confidence LLM guess renders without review. *Fix:
   add an optional `min_confidence` threshold.*

9. **`replay_lock` does not actually replay.** v2.2.0 reports `success=True` without
   rebuilding a venv or re-rendering; `recipe_full_name`/`contract_dict` params are accepted
   but unused. *Fix: wire `verify_byte_identical`, or rename the result so "success" does not
   overstate verification.*

10. **TF-IDF code is triplicated and the blueprint docstring lies about reuse.** The six
    helpers are copy-pasted across blueprint, alignment, and citation_inserter; the
    blueprint claims to "reuse the TF-IDF infrastructure from `manuscript_alignment`" but
    never imports it. *Fix: extract a shared `manifest/_tfidf.py`; correct the docstring.*

11. **`insert_blocks_into_existing` is dead and disagrees with the live inserter.** It is
    exported but unused; its "insert BEFORE" semantics contradict the live "insert AFTER"
    in `apply_update_policy` — a latent off-by-one trap. *Fix: route through one
    implementation or delete the dead one.*

12. **No canonical figure-id form across auditors.** `Figure 3A` / `Figure 3a` /
    `figure_3a` / `fig:3a` proliferate, so cross-auditor correlation is ad-hoc and silently
    case-sensitive. *Fix: one shared `normalise_figure_id` helper.*

13. **Magic-number thresholds without justification.** `claim_check`'s `|r| ≥ 0.1`
    (a 1%-of-variance correlation marked SUPPORTED) and `manuscript_blueprint`'s
    `min_similarity = 0.4` on one-line TF-IDF vectors are uncalibrated. *Fix: raise/justify
    `|r|` to ~0.3; document or surface the blueprint threshold.*

14. **Surfaces reach into private manifest internals.** `generate_cmd` reconstructs
    `RecipeBinding as _RB`; `tui_scout.py` imports `_resolve_consensus_client` with a
    `type: ignore` inside a silent except. An upstream rename breaks them silently. *Fix:
    promote those to public APIs.*

15. **The `register_modality` aesthetic boundary is untyped.** It accepts `Any`, so a
    modality registering a non-`ModalityAesthetic` object is accepted silently — the one
    type core most wants to enforce at registration is the one it does not. *Fix: a
    `TYPE_CHECKING` import + runtime `isinstance` check.*

**Low — naming smells, dead code, and missing orientation docs:**

16. **The closed-taxonomy enforcement asymmetry** (`RecipeFamily` is a runtime-validated
    `StrEnum`; the three `StatisticalContract` `Literal`s are static-check-only on a vanilla
    dataclass).

17. **`add_halo_label` lies about its behaviour** (no halo; dead `halo_color`/`halo_width`
    kwargs `del`-eted), kept for ~390-caller compatibility.

18. **Internal-error findings poison a real bucket** — a `bias_auditor` check that raises is
    recorded as `truncated_y_axis` ("# generic"); add a `BiasFindingKind.internal_error`.

19. **Two notions of "supporting panel"** with different keyword sets in `novelty_scout`
    vs. `scout`; **two meanings of "preserve"** in `execute_plan` vs. `ManuscriptPolicy`.

20. **Inconsistent public-surface hygiene.** `PanelExecutionStatus` is a hand-rolled `str`
    subclass amid `StrEnum`s everywhere else; `plugins/__init__.py` has no `__all__`;
    `scoring`/`tag_taxonomy`/`catalog` define no `__all__`; `palettes()`/`semantic_color()`
    and `enrich_with_pylatexenc` are public-looking but unexported; `report_to_json` and
    `_scout_report_to_json` are dead; `nature.py` ships `"semibold" if False else "bold"`.

21. **Missing package READMEs everywhere.** `core/`, `recipes/`, `manifest/`, `safety/`,
    `mcp/`, `plugins/`, `projects/`, `cli/`, and `templates/` lack package-level orientation
    docs; the elevation/wave/sprint vocabulary is undefined without external
    `docs/spec_*.md`. For the most-depended-on packages this is a maintainability liability a
    JOSS reviewer will note. *Fix: add short README/docstring maps; resolve the E-numbers to
    capabilities.*

22. **`templates/` has no in-package consumer** and `outputs.gitignore` is not packaged by
    the current `package-data` globs; the four scaffold files are read by no Python module.
    *Fix: document who copies them or wire a `figures init` command; fix the packaging glob.*

None of items 16–22 are correctness bugs in the happy path. Items 1–15 are the ones a
reviewer running the code could substantiate; of those, 1–5 are the highest-value fixes to
land before submission, because each is a place where a claim in the code or docstring
overstates what the code actually does — which is the one category of finding a JOSS
reviewer treats as a credibility issue rather than a feature request.
