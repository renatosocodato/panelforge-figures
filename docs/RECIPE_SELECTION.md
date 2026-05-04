# Recipe Selection — Decision Log

**Status:** Wave 2 spec (matches `recipes_index.json` once `index_meta.tags_enabled = true`).
**Companion documents:**
- [`AGENT_BOOTSTRAP.md`](../AGENT_BOOTSTRAP.md) — entry plane for first-contact agents.
- [`docs/recipes_index.schema.json`](recipes_index.schema.json) — JSON-Schema for the index.
- [`docs/RECIPE_SELECTION_OFFLINE.md`](RECIPE_SELECTION_OFFLINE.md) — frozen offline mirror.

This document is the **prose contract** for the panelforge-figures recipe-discovery system. It explains how an agent walks a user from a vague figure request ("I need a Cdc42 sex-by-genotype panel") through a deterministic, audit-ready shortlist of `{modality}.{recipe}` candidates. Read this once; thereafter, the index `scoring_rubric` block is the source of truth for weights and the `intake_questions` block is the source of truth for questions.

---

## 1. The funnel

Discovery is a five-stage pipeline. Each stage takes the previous stage's output and narrows it.

```
project intake (8 Q&A)
        │
        ▼
modality shortlist (≤6 modalities)
        │
        ▼
family shortlist (≤8 visual families)
        │
        ▼
recipe shortlist (≤12 recipes by default; configurable)
        │
        ▼
wave / build-order plan (chronological group + sparse-checkout list)
```

Each arrow is **deterministic given the intake answers and the index**. Two agents asked the same eight questions on the same index version produce the same shortlist. That property is load-bearing — it is what lets us version, replay, and audit figure-discovery decisions across a manuscript.

### Stage 1 — Project intake

Eight closed-form questions, asked verbatim from `index["intake_questions"]`. Output: a `profile` dict with keys `anchor`, `factorial`, `equivalence`, `dynamics`, `dimensionality`, `modalities` (allow-list), `hard_filters` (e.g. `{compartment_aware: true}`), `shortlist_size`.

Rule: **the intake never invents tags the user did not give.** If a user skips a question, the corresponding profile key is `null` and that dimension is excluded from scoring (its weight is redistributed proportionally across answered dimensions — see §3 on `--weights` overrides for the override path).

### Stage 2 — Modality shortlist

Filter `index["modalities"]` by the user's `modalities` list. If the list is empty, all 23 modalities survive. The modality count drives the sparse-checkout decision tree in `AGENT_BOOTSTRAP.md` step 4 (≤3 modalities → sparse-checkout; 4+ → full clone).

### Stage 3 — Family shortlist

Within surviving modalities, bucket recipes by `family`. The family bucket is informational — agents do not score families directly — but the surfaced visual-family histogram lets the user reject an entire approach (e.g. "no `coef_forest` panels — I want raw distributions") before recipe-level scoring runs.

### Stage 4 — Recipe shortlist

Apply the locked-weight scorer (§3) to every recipe in surviving modalities. Drop scores below threshold (0.40). Rank survivors by score, then by tie-breakers. Truncate at `shortlist_size` (default 12).

### Stage 5 — Wave / build-order plan

Group surviving recipes by `tags.wave`. Inside each wave bucket, order by score descending. The wave label tells the agent **how battle-tested** a recipe is: older waves (`v1.0`, `v1.1`) have years of CI, gallery review, and downstream consumption; newer waves (`v1.5.0-beta-cdc42_factorial_companion`) are weeks old and may need extra QA before publication.

---

## 2. Stage criteria — what gets dropped

| Stage | Signal | Drop rule |
|---|---|---|
| Intake | Eight answers | Empty answers → dimension weight redistributed (or set to 0 with `--weights`). |
| Modality | `index["modalities"][m].name` | Drop modalities not in user's allow-list. |
| Family | `recipe.family` | No drop here — informational only. User may apply a `--exclude-family` filter. |
| Recipe | `recipe.tags` × `scoring_rubric` | Drop hard-filter mismatches (e.g. `compartment_aware: true` profile drops recipes with `tags.compartment_aware = false`). Drop weighted score < 0.40. |
| Wave | `recipe.tags.wave` | No drop — used only for ordering and for QA-confidence signalling. |

---

## 3. The scoring rubric

The rubric lives in `index["scoring_rubric"]` as a JSON object. It is locked by `panelforge_version` — bumping the rubric is a minor-version bump.

### 3.1 Locked weights

| Dimension | Weight | Match function |
|---|---|---|
| `factorial` | **0.30** | Boolean (see §3.2) |
| `equivalence` | **0.25** | Boolean (see §3.2) |
| `anchor` | **0.20** | Graded (see §3.3) |
| `dynamics` | **0.15** | Graded (see §3.4) |
| `dimensionality` | **0.10** | Graded (see §3.5) |
| **Sum** | **1.00** | |

Weights are deliberately heaviest on `factorial` because a 2 × 2 (or 2 × N) factorial design is the most expensive, most reviewer-scrutinised statistical commitment a manuscript can make — recipes that natively render factorial summaries (interaction forests, marginal-mean grids, mediator-decomposition slopes) are vastly more useful than generic plots. `equivalence` ranks second because TOST / null-accepting bounds are an active editorial differentiator. `anchor` ranks third because matching a manuscript's protein / model anchor (DISC1, CDC42, RhoA, etc.) often dictates the colour palette and label vocabulary. `dynamics` and `dimensionality` are tertiary signals.

### 3.2 Boolean match (factorial, equivalence)

```
if profile[dim] is True and recipe.tags[dim] is True:
    contribution = 1.0 × weight
else:
    contribution = 0.0
```

The rule is **presence-checked**, not symmetric: profile=False does not credit recipes that lack the tag. This biases the shortlist toward recipes that actively feature the user's requested design property. Users who want a factorial-agnostic shortlist either leave `factorial=null` (which redistributes the 0.30 weight) or set `--weights factorial=0.0` explicitly.

### 3.3 Anchor match (graded)

```
exact match (profile.anchor == recipe.tags.anchor):                   1.0
recipe.tags.anchor == "generic":                                       0.5
profile.anchor in {"both", any 2-anchor pair} and recipe matches one:  0.7
otherwise:                                                             0.0
```

`generic` is the universal-fallback anchor — a meta-and-diagnostic recipe like `effect_size_funnel_plot` carries `anchor: generic` and is scored 0.5 against any anchor query. Recipes that ship inside a manuscript-companion pack (DISC1, CDC42, etc.) carry the manuscript anchor and earn full 1.0 only against that exact query.

### 3.4 Dynamics match (graded)

```
exact match (profile.dynamics == recipe.tags.dynamics)
   AND profile.dynamics ≠ "static":                                    1.0
profile.dynamics == "mixed" and any concrete dynamics value matches:   0.8
recipe.tags.dynamics == "static":                                      0.3   (baselines always useful)
otherwise:                                                             0.0
```

The "static recipes are always 0.3" rule encodes the engineering reality that static-summary plots — boxplots, raincloud, coefficient forests — are the **substrate** of any manuscript figure. Even a kymograph-heavy biophysics paper needs static effect-size panels for its summary figures. Note: a profile that explicitly requests `dynamics=static` does **not** elevate matching static recipes to 1.0 — those still earn 0.3, because "I want static" is read as "I have no dynamics signal to exploit," not as a positive selection criterion.

### 3.5 Dimensionality match (graded)

```
exact match (profile.dim == recipe.tags.dim):                          1.0
profile.dim == "mixed" (always):                                       0.7
otherwise:                                                             0.0
```

`mixed` is a soft credit applied uniformly when the profile signals "I have both 2D and 3D data" or refuses to commit. Recipes that explicitly declare `dim: mixed` (rare — they auto-adapt) also score 1.0 on exact match.

### 3.6 Tie-breakers

When two recipes carry identical weighted scores, tie-break in this order:

1. **Anchor strength** — exact-match anchor (1.0) beats `generic` (0.5).
2. **Modality locality** — recipes from the modality with the most surviving candidates win (the user implicitly endorsed that modality by giving it a denser shortlist).
3. **Wave age** — older `tags.wave` wins (more battle-tested; v1.0 > v1.1 > v1.5.0-beta-*).
4. **Alphabetical** — by full name `{modality}.{recipe}`.

> **Spec note.** Wave-age ordering is "older first" by design — this prioritises recipes that have already absorbed gallery review, downstream usage, and CI churn. If the user has expressed a preference for newer / experimental variants (e.g. they explicitly say "show me the cdc42-companion recipes"), they are expected to use `--include` overrides (§6) rather than reverse the tie-breaker.

### 3.7 Threshold

Recipes with weighted score `< 0.40` are dropped. The threshold is calibrated against Example 3 (§4.3) — pure-generic profiles produce zero shortlist, which is the desired behaviour.

---

## 4. Worked examples

### 4.1 Example 1 — DISC1 biophysics figure

**Profile (from intake):**

| Question | Answer |
|---|---|
| Manuscript anchor? | `DISC1` |
| Factorial design? | `false` |
| Equivalence claim? | `true` |
| Dynamics? | `static` |
| Dimensionality? | `mixed` |
| Modality allow-list? | `[biophysics_scaling, actin_microtubule_morphometry]` |
| Hard filters? | `{compartment_aware: true}` |
| Shortlist size? | `12` |

**Stage 2 — modality scoping.** Filtering 23 modalities to 2 (`biophysics_scaling` + `actin_microtubule_morphometry`) drops the pool from 448 → 100 recipes (51 + 49).

**Stage 4 — hard filters.** The `compartment_aware: true` filter drops every recipe whose `tags.compartment_aware ≠ true`. After hard filters, ~31 recipes survive.

**Stage 4 — scoring.** For a representative compartment-aware, equivalence-flagged, DISC1-anchored, static recipe like `biophysics_scaling.persistence_length_lp_with_equivalence_bounds`:

| Dimension | Profile | Recipe tag | Match value | Contribution |
|---|---|---|---|---|
| factorial | false | false | 0.0 (presence-checked) | 0.30 × 0.0 = **0.000** |
| equivalence | true | true | 1.0 (exact) | 0.25 × 1.0 = **0.250** |
| anchor | DISC1 | DISC1 | 1.0 (exact) | 0.20 × 1.0 = **0.200** |
| dynamics | static | static | 0.3 (static-baseline rule) | 0.15 × 0.3 = **0.045** |
| dimensionality | mixed | mixed (or any) | 0.7 (mixed-soft-credit) | 0.10 × 0.7 = **0.070** |
| **Total** | | | | **0.565** |

Three recipes tie at score `0.565`:

- `biophysics_scaling.compartment_paired_delta_scatter` — whole-cell vs protrusion-internal effect deltas.
- `biophysics_scaling.hierarchical_effect_size_ladder` — polymer → network → territory → geometry → whole-cell effect-size cascade.
- `biophysics_scaling.persistence_length_lp_with_equivalence_bounds` — TOST equivalence bounds on Lₚ across compartments.

**Tie-break.** All three have anchor strength 1.0 (DISC1 exact). All three live in `biophysics_scaling`. All three carry `tags.wave = v1.4.0-beta-disc1_manuscript_companion` (same age). Alphabetical wins: the order printed above is the canonical surfacing order.

**What the agent should say:**

> Three biophysics recipes scored 0.565, all anchored to DISC1 with compartment-aware effect statistics. Two render coefficient ladders (paired-delta and hierarchical); one renders an equivalence-bounded split violin. Pick the equivalence panel if your figure needs to commit to a null-accepting claim; pick the hierarchical ladder if you want the polymer-to-cell scale cascade in one panel; pick the paired-delta scatter for whole-cell vs protrusion-internal contrast.

### 4.2 Example 2 — CDC42 sex-divergent surveillance figure

**Profile:**

| Question | Answer |
|---|---|
| Manuscript anchor? | `CDC42` |
| Factorial design? | `true` |
| Equivalence claim? | `false` |
| Dynamics? | `static` |
| Dimensionality? | `2D` |
| Modality allow-list? | `[mixed_effects_models, biophysics_scaling, intravital_imaging]` |
| Hard filters? | `{}` |
| Shortlist size? | `10` |

**Stage 2 — modality scoping.** 3 modalities → 132 recipes (20 + 51 + 61).

**Stage 4 — hard filters.** None applied; ~120 recipes survive after the index's automatic incompatibility checks (e.g. recipes that require 3D voxel data are dropped against `dim: 2D`).

**Stage 4 — scoring.** For `mixed_effects_models.two_way_anova_summary_plot` (factorial-native, CDC42-anchored, 2D, static):

| Dimension | Profile | Recipe tag | Match value | Contribution |
|---|---|---|---|---|
| factorial | true | true | 1.0 (exact, presence-checked) | 0.30 × 1.0 = **0.300** |
| equivalence | false | false | 0.0 (presence-checked) | 0.25 × 0.0 = **0.000** |
| anchor | CDC42 | CDC42 | 1.0 (exact) | 0.20 × 1.0 = **0.200** |
| dynamics | static | static | 0.3 (static-baseline) | 0.15 × 0.3 = **0.045** |
| dimensionality | 2D | 2D | 1.0 (exact) | 0.10 × 1.0 = **0.100** |
| **Total** | | | | **0.645** |

Top three by score:

- `mixed_effects_models.two_way_anova_summary_plot` — F, p, partial η² for {sex, genotype, sex × genotype}. Score **0.645**.
- `mixed_effects_models.sex_stratified_roc_loocv` — sex-stratified ROC with leave-one-out validation. Score **0.645**.
- `biophysics_scaling.quartile_stacked_bar_by_factor` — dissipation-quartile stacked bars by sex × genotype. Score **0.645**.

**Comparison to Example 1.** The top score in Example 2 (0.645) exceeds the top score in Example 1 (0.565) by exactly 0.080 — which is the gap between scoring 1.0 vs 0.7 on dimensionality (0.030) plus the presence of factorial credit at 0.300 minus the equivalence credit at 0.250 that Example 1 receives. This is the rubric working as intended: factorial designs out-rank equivalence designs by a 0.30 vs 0.25 weighting, propagating directly to shortlist ordering.

**Tie-break.** All three score 0.645. `mixed_effects_models` has more matches (it owns 2 of the 3) → wins modality-locality. Inside `mixed_effects_models`: same anchor strength, same wave (`v1.5.0-beta-cdc42_factorial_companion`), so alphabetical: `sex_stratified_roc_loocv` < `two_way_anova_summary_plot`. **Final order: `sex_stratified_roc_loocv` → `two_way_anova_summary_plot` → `quartile_stacked_bar_by_factor`.**

(The breakdown table above lists `two_way_anova_summary_plot` first for arithmetic readability; the actual canonical surfacing order applies tie-breakers.)

### 4.3 Example 3 — generic library use (no manuscript anchor)

**Profile:**

| Question | Answer |
|---|---|
| Manuscript anchor? | `none` |
| Factorial design? | `false` |
| Equivalence claim? | `false` |
| Dynamics? | `static` |
| Dimensionality? | `2D` |
| Modality allow-list? | (all) |
| Hard filters? | `{}` |
| Shortlist size? | `15` |

**Pool.** All 448 recipes.

**Best-case scoring.** For a recipe carrying `anchor: generic`, `dynamics: static`, `dim: 2D` (and false/absent factorial + equivalence — the only candidates for "best generic"):

| Dimension | Profile | Recipe tag | Match value | Contribution |
|---|---|---|---|---|
| factorial | false | false | 0.0 (presence-checked) | **0.000** |
| equivalence | false | false | 0.0 (presence-checked) | **0.000** |
| anchor | none | generic | 0.5 (generic credit) | 0.20 × 0.5 = **0.100** |
| dynamics | static | static | 0.3 (static-baseline rule) | 0.15 × 0.3 = **0.045** |
| dimensionality | 2D | 2D | 1.0 (exact) | 0.10 × 1.0 = **0.100** |
| **Total** | | | | **0.245** |

**Top score: 0.245 — below the 0.40 threshold.**

> **DEFECT-2 reconciliation note.** The static-baseline carve-out in §3.4 (static profile + static recipe → 0.3, not 1.0) applies uniformly across all three worked examples. Earlier drafts of this document credited Example 3's dynamics dimension at 1.0 × 0.15 = 0.150 and reported a total of 0.350; that arithmetic was inconsistent with the rule that `dynamics=static` is read as "no temporal signal to discriminate on" rather than as a positive selection criterion. The corrected total is 0.245 — still well below the 0.40 threshold, so the empty-shortlist outcome and recovery message below are unchanged.

**The shortlist is empty.** This is the correct, designed-for outcome: a profile with no factorial, no equivalence, and no anchor commitment carries no orienting signal — the system refuses to recommend, because every recommendation it could make would be an arbitrary pick from the 448-recipe library.

**Recovery path.** The agent surfaces this message:

> No recipes cleared the 0.40 threshold. Your profile has no manuscript anchor, no factorial design, and no equivalence claim — all three of the heavy-weight scoring signals are off. To produce a shortlist, commit to **at least one** of:
> - a manuscript anchor (DISC1, CDC42, or another tagged anchor),
> - a factorial design flag,
> - an equivalence-claim flag.
>
> Alternatively, browse the catalog directly via `figures catalog --by-modality` and pick recipes by hand.

This failure mode is graceful: the user understands *why* there's no shortlist and what minimum commitment unblocks one.

---

## 5. Failure-mode protocols

### 5.1 No recipes clear threshold

(See Example 3 above for the canonical case.) Beyond the generic-profile case, threshold misses also occur when hard filters over-narrow. The agent should:

1. Identify the hard filter that dropped the most recipes (compute `count(pool) - count(post-filter)` per filter).
2. Surface: "Your `compartment_aware: true` filter dropped 89 of 100 candidates. Relax it?"
3. If user accepts, re-run scoring with the filter removed.

### 5.2 Shortlist dominated by one wave

When `≥ 80%` of shortlist entries share `tags.wave`, the agent flags:

> 11 of 12 shortlist recipes ship in `v1.5.0-beta-cdc42_factorial_companion` (a 4-week-old companion pack). These are well-tested in CI but have not yet absorbed manuscript-level usage feedback. Consider asking for a wave-balanced shortlist via `--shortlist-size 24` to surface more battle-tested alternatives.

### 5.3 Identical scores, different visual approaches

When ≥ 3 recipes tie at the same score across ≥ 2 families, the agent groups by family before printing:

```
Score 0.565 (3 recipes):
  family=coef_forest:  hierarchical_effect_size_ladder, compartment_paired_delta_scatter
  family=split_violin: persistence_length_lp_with_equivalence_bounds
```

The user can pick by visual approach instead of by name lottery.

### 5.4 Hard filter contradicts modality scoping

If the user has set `modalities=[clinical_cohort]` and `hard_filters={compartment_aware: true}`, the post-filter pool is empty (clinical-cohort recipes are not compartment-aware). The agent surfaces both filters and asks which to relax — never silently drops one.

---

## 6. Override mechanisms

The `figures intake` CLI accepts these overrides:

| Flag | Effect |
|---|---|
| `--weights factorial=0.5,equivalence=0.4,anchor=0.1` | Replace locked rubric weights. Must sum to ≤ 1.0; remaining mass goes to dropped dimensions at 0. The CLI rejects sets that sum to > 1.0. |
| `--include {modality}.{recipe}` | Force a recipe into the shortlist regardless of score (appended at the bottom, tagged `[forced-include]`). |
| `--exclude {modality}.{recipe}` | Drop a recipe from the shortlist regardless of score. |
| `--shortlist-size N` | Truncate to top N (default 12). Must be `1 ≤ N ≤ 50`. |
| `--threshold T` | Override the 0.40 cut-off (default 0.40, range 0.0–1.0). Lower thresholds expand the shortlist; raise to tighten. |
| `--no-tie-break-by-wave` | Skip the wave tie-breaker (use only modality-locality + alphabetical). For agents that prefer recency over battle-tested-ness. |
| `--explain {modality}.{recipe}` | Print the full score breakdown for a single recipe (debug mode — does not produce a shortlist). |

Overrides are saved to the manifest output under a `discovery_log` block so the agent's choices are auditable downstream.

---

## 7. Glossary

| Term | Definition |
|---|---|
| **Profile** | The dict produced by intake: `{anchor, factorial, equivalence, dynamics, dim, modalities, hard_filters, shortlist_size}`. |
| **Hard filter** | A boolean tag (e.g. `compartment_aware`) applied as an absolute drop, before scoring. |
| **Soft signal** | A scoring-rubric dimension (factorial, equivalence, anchor, dynamics, dim) whose contribution is weighted, not absolute. |
| **Wave** | A named beta pack (e.g. `v1.4.0-beta-disc1_manuscript_companion`) that ships a coherent batch of recipes. |
| **Shortlist** | The post-threshold, post-tie-break, top-N recipe list returned to the user. |
| **Modality locality** | The number of surviving (post-filter) recipes a given modality contributes to the pre-shortlist pool. |

---

## 8. Versioning and stability

- The locked weights in §3.1 are part of the `panelforge_version` minor-version contract. Any change to weights, match-function rules, or tie-breakers requires a minor-version bump and a CHANGELOG entry.
- The intake question wording in `index["intake_questions"]` is part of the same contract — agents that have memorised the questions verbatim must continue to work after a minor-version bump unless the bump explicitly notes intake changes.
- New tag dimensions (e.g. a future `temporal_resolution`) are additive: they ship at weight 0.0 by default and require an explicit minor-version bump to receive nonzero weight.
- This document is regenerated together with the index. If `index_meta.panelforge_version` and the version string in this document's header differ, the index is the source of truth.

---

## 9. See also

- [`AGENT_BOOTSTRAP.md`](../AGENT_BOOTSTRAP.md) — first-contact procedure (fetch + retrieve + sparse-checkout).
- [`docs/RECIPE_SELECTION_OFFLINE.md`](RECIPE_SELECTION_OFFLINE.md) — frozen offline mirror of the intake script + scoring rules + a single worked example (this document's Example 1).
- [`docs/recipes_index.schema.json`](recipes_index.schema.json) — machine-readable schema for the index (including `scoring_rubric` and `intake_questions` blocks).
- [`docs/cdc42_factorial_companion_pack_tracker.md`](cdc42_factorial_companion_pack_tracker.md) — the CDC42 pack that supplies Example 2's top recipes.
- [`docs/disc1_manuscript_companion_pack_tracker.md`](disc1_manuscript_companion_pack_tracker.md) — the DISC1 pack that supplies Example 1's top recipes.
- [`docs/recipes_by_modality.md`](recipes_by_modality.md) — human-browsable catalog (alphabetical-by-modality).
- [`docs/recipes_by_question.md`](recipes_by_question.md) — human-browsable catalog (grouped by `answers_question`).
