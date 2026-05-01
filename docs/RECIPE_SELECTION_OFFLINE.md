# Recipe Selection — Offline Mirror

**Status:** Frozen offline copy. The authoritative version is [`docs/RECIPE_SELECTION.md`](RECIPE_SELECTION.md), which ships with the live index. Use this file when the index is unreachable or the agent is air-gapped.

**Staleness warning.** This file may lag the online version by one or more minor releases. Worked examples in particular are pinned — fresh examples ship in the online doc. Always check `index_meta.panelforge_version` against the version noted at the top of this document before trusting the rules below.

**Pinned to:** `panelforge_version = 1.0.0` (Wave 2 baseline).

---

## 1. The 8-question intake script

Ask each question verbatim. Empty / "I don't know" answers map to `null` and exclude that dimension from scoring (its weight is redistributed to answered dimensions).

1. **Manuscript anchor.** Is there a specific manuscript or model anchor (DISC1, CDC42, RhoA, or another tagged anchor)? If yes, name it. Otherwise reply `none`.
2. **Factorial design.** Does your figure summarise a factorial design (2 × 2 sex × genotype, dose × time, etc.)? `true` / `false`.
3. **Equivalence claim.** Does your figure need to commit to a TOST / null-accepting equivalence claim (i.e. show that two conditions are bounded-equivalent)? `true` / `false`.
4. **Dynamics.** What is the temporal character of the data? `static` / `kymograph` / `live` / `ordered_pseudotime` / `mixed`.
5. **Dimensionality.** Spatial dimensionality? `2D` / `3D` / `mixed`.
6. **Modality allow-list.** Which modalities should be searched? Empty list = all 23 modalities. Otherwise a comma-separated subset (e.g. `biophysics_scaling, mixed_effects_models`).
7. **Hard filters.** Any required-must-have boolean filters? Common ones: `compartment_aware`, `scale_aware`. Empty `{}` = none.
8. **Shortlist size.** How many recipes should the shortlist surface? Default `12`. Range `1–50`.

Output: a `profile` dict consumed by the scorer.

---

## 2. Locked weights

| Dimension | Weight |
|---|---|
| factorial | 0.30 |
| equivalence | 0.25 |
| anchor | 0.20 |
| dynamics | 0.15 |
| dimensionality | 0.10 |
| **Sum** | **1.00** |

Threshold: drop scores `< 0.40`.

---

## 3. Match functions (compact)

**Boolean (factorial, equivalence)** — presence-checked:

```
profile=True  AND recipe.tag=True  → 1.0
otherwise                          → 0.0
```

**Anchor** — graded:

```
exact match                                    → 1.0
recipe.anchor = "generic"                      → 0.5
profile = "both" / 2-anchor pair, recipe in it → 0.7
otherwise                                      → 0.0
```

**Dynamics** — graded:

```
exact match AND profile ≠ "static"   → 1.0
profile = "mixed" AND any match      → 0.8
recipe.dynamics = "static"           → 0.3   (baselines always useful)
otherwise                            → 0.0
```

**Dimensionality** — graded:

```
exact match              → 1.0
profile = "mixed"        → 0.7   (uniform soft credit)
otherwise                → 0.0
```

**Tie-breakers (in order):** anchor strength → modality locality → wave age (older first) → alphabetical by `{modality}.{recipe}`.

---

## 4. Worked example (compressed) — DISC1 biophysics figure

**Profile.** anchor=`DISC1`; factorial=`false`; equivalence=`true`; dynamics=`static`; dim=`mixed`; modalities=`[biophysics_scaling, actin_microtubule_morphometry]`; hard_filters=`{compartment_aware: true}`; shortlist=`12`.

**Pool reduction.** 448 → 100 (modality scoping) → ~31 (compartment_aware filter).

**Score breakdown** for `biophysics_scaling.persistence_length_lp_with_equivalence_bounds`:

| Dimension | Profile | Recipe | Match | × Weight | = |
|---|---|---|---|---|---|
| factorial | false | false | 0.0 | 0.30 | 0.000 |
| equivalence | true | true | 1.0 | 0.25 | 0.250 |
| anchor | DISC1 | DISC1 | 1.0 | 0.20 | 0.200 |
| dynamics | static | static | 0.3 | 0.15 | 0.045 |
| dimensionality | mixed | mixed | 0.7 | 0.10 | 0.070 |
| | | | | **Total** | **0.565** |

**Top three (tied at 0.565):**

1. `biophysics_scaling.compartment_paired_delta_scatter`
2. `biophysics_scaling.hierarchical_effect_size_ladder`
3. `biophysics_scaling.persistence_length_lp_with_equivalence_bounds`

Tie-broken by anchor strength (all 1.0) → modality locality (all `biophysics_scaling`) → wave age (all `v1.4.0-beta-disc1_manuscript_companion`) → alphabetical (final order as printed).

For two additional worked examples (CDC42 factorial, generic-no-anchor failure case), see the online [`RECIPE_SELECTION.md`](RECIPE_SELECTION.md) §4.2 and §4.3.

---

## 5. Override flags (compact)

| Flag | Effect |
|---|---|
| `--weights factorial=0.5,equivalence=0.4,…` | Replace locked weights (must sum ≤ 1.0). |
| `--include {modality}.{recipe}` | Force-include regardless of score. |
| `--exclude {modality}.{recipe}` | Force-exclude regardless of score. |
| `--shortlist-size N` | Top-N truncation (default 12; range 1–50). |
| `--threshold T` | Override 0.40 cut-off. |
| `--explain {modality}.{recipe}` | Print full breakdown for a single recipe. |

---

## 6. Failure-mode quick reference

| Symptom | Action |
|---|---|
| Empty shortlist after threshold | Identify largest pool-narrowing filter; offer to relax. If profile has no anchor + no factorial + no equivalence, instruct user to commit to at least one orienting signal (see §4.3 of online doc). |
| Shortlist dominated by one wave | Surface wave concentration; recommend `--shortlist-size 24` for wave-balanced view. |
| Tie cluster across families | Group display by `family` so user picks by visual approach. |
| Hard filter contradicts modality scope | Surface both; ask user which to relax. |

---

## 7. Refresh check

Before trusting this offline doc:

1. Compare the version string in this header (`panelforge_version = 1.0.0`) to `index_meta.panelforge_version` in any reachable copy of the index.
2. If they match, the rules below are current.
3. If the index version is newer, the rules below may be stale — fetch [`RECIPE_SELECTION.md`](RECIPE_SELECTION.md) before using.
4. If the index is unreachable, proceed with these rules and tag the resulting manifest with `discovery_log.offline_mode: true` so downstream review can flag the decision.
