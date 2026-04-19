# v1.1 Hydration Coordinator

Keep this document open for the full ~11-week hydration. It is the single
source of truth for sequencing, invariants, and progress.

## Premise

v1.0 landed cleanly. `panelforge-figures` is pip-installable at
`v1.0.0`, skill installable via
`claude skill install github:renatosocodato/panelforge-figures`, 137
recipes across 20 modalities, all tests green. v1.1 expands this to
**320+ recipes** with a floor of 15 per modality — 18-22 for central
modalities, 10-15 for forward-looking ones — **without touching core
architecture**.

> **Note (captured 2026-04-19):** at the moment this plan was saved,
> the repo was at `v0.1.0`, not `v1.0.0`. The plan's version labels
> (`v1.1.0-s01` etc.) are forward-looking. Before kicking off Session
> 01, decide whether to (a) retag the current stable release as
> `v1.0.0` first, or (b) rename `v1.1` → `v0.2` throughout the briefs.
> This decision only affects tag names, not the plan's content or
> invariants.

## Non-negotiables for v1.1

These hold across every session. If any session violates one, roll it
back.

1. **One modality per PR.** No cross-modality edits in a single
   session, ever. *Exception:* extending `core/contract.py` with new
   contract classes is permitted when strictly necessary, but only
   with backward-compatible defaults.
2. **No changes to `core/` beyond contract additions**, no changes to
   `themes/`, no changes to CLI or manifest schema. v1.1 is pure
   recipe expansion.
3. **No new dependencies.** Existing package dep set is frozen.
4. **Every new recipe ≥ 80 lines**, honors modality `_aesthetic.py`,
   has `demo_contract`, gallery PNG, quality-gate test,
   aesthetic-compliance test. Fidelity gate from v1.0 applies
   unchanged.
5. **Squash-merge every session PR.** One commit per modality in
   `main` branch history. Session PRs have three commits pre-squash:
   gap analysis, implementation, gallery+tests.
6. **Each session is user-gated.** Claude Code proposes the 8+ new
   recipes with justifications (question answered, contract
   requirements, alternatives in modality, distinctness) before
   writing any code. **No session writes recipes without approval of
   the proposal table.**
7. **Each session produces a single tagged release**
   (`v1.1.0-s01`, `v1.1.0-s02`, …, `v1.1.0-s20`), culminating in
   `v1.1.0` tagged after session 20.

## Cadence rules

- **Minimum 48 hours between sessions.** Use the gap to render at
  least one figure from the newly-hydrated modality in a real
  manuscript context. Aesthetic drift, missing primitives, awkward
  contracts — you catch these in use, not in review.
- **Sessions 1-4: one per week.** High-priority modalities, slow
  pace, you're learning what real use reveals.
- **Sessions 5-10: up to two per week.** Second-tier modalities,
  pattern established.
- **Sessions 11-20: up to three per week if you have bandwidth.**
  Breadth modalities, lower urgency, lighter use-case pressure.
- **Stop rule.** If any session's rendered output makes you wince in
  a real manuscript, halt hydration. Run a `v1.0.x` or `v1.1.0-fix`
  patch to address the aesthetic regression before proceeding.
  Quality floor > schedule.

## Session sequence

| # | Modality | v1.0 | v1.1 target | Tag | Priority rationale |
|---|---|---|---|---|---|
| 01 | `rhogtpase_dynamics` | 12 | 18 | `v1.1.0-s01` | Manuscript 3 + µRedoxScape + scaffold v4.3 |
| 02 | `fret_biosensors` | 10 | 18 | `v1.1.0-s02` | Scaffold v4.3 FRET-RhoA, active |
| 03 | `actin_microtubule_morphometry` | 12 | 20 | `v1.1.0-s03` | DISC1 + scaffold v4.3 + Neuron |
| 04 | `mixed_effects_models` | 9 | 16 | `v1.1.0-s04` | Every paper |
| 05 | `sensitivity_analysis` | 8 | 15 | `v1.1.0-s05` | Manuscript 3 Box 1 |
| 06 | `redox_imaging` | 8 | 15 | `v1.1.0-s06` | µRedoxScape |
| 07 | `intravital_imaging` | 8 | 15 | `v1.1.0-s07` | Neuron + 2P witness |
| 08 | `gillespie_stochastic` | 7 | 15 | `v1.1.0-s08` | HOME-GATE-TRAP dwell |
| 09 | `omics_differential` | 10 | 16 | `v1.1.0-s09` | Targetome |
| 10 | `calcium_signaling` | 6 | 15 | `v1.1.0-s10` | Scaffold v4.3 GCaMP6f |
| 11 | `single_cell_embeddings` | 7 | 15 | `v1.1.0-s11` | Targetome scRNA |
| 12 | `dose_response_pharmacology` | 5 | 15 | `v1.1.0-s12` | ATHENA |
| 13 | `network_and_pathway` | 5 | 15 | `v1.1.0-s13` | Commentary + Targetome |
| 14 | `biophysics_scaling` | 5 | 15 | `v1.1.0-s14` | Manuscript 3 collapse |
| 15 | `diffusion_and_tracking` | 5 | 15 | `v1.1.0-s15` | Intravital downstream |
| 16 | `spatial_statistics` | 4 | 15 | `v1.1.0-s16` | Complements intravital |
| 17 | `grant_and_conceptual` | 6 | 15 | `v1.1.0-s17` | ATHENA / MIRROR / Horizon |
| 18 | `meta_and_diagnostic` | 4 | 15 | `v1.1.0-s18` | QC panels |
| 19 | `clinical_cohort` | 3 | 15 | `v1.1.0-s19` | ATHENA downstream |
| 20 | `cryoem_and_structure` | 3 | 15 | `v1.1.0-s20` | Collaborator work |

Final tag after session 20: **`v1.1.0`**.

## Progress tracker

The live tracker lives at [`docs/recipe_gap_tracker.md`](recipe_gap_tracker.md)
and is updated on every PR merge.

## Cross-session artifacts

These are updated by v1.0 but honored by every v1.1 session:

- [`docs/architecture.md`](architecture.md) — design contract reference
- [`docs/gallery/index.md`](gallery/index.md) — auto-regenerated each session
- [`docs/recipes_by_modality.md`](recipes_by_modality.md) — auto-regenerated each session
- [`docs/recipes_by_question.md`](recipes_by_question.md) — auto-regenerated each session
- [`CHANGELOG.md`](../CHANGELOG.md) — appended per session with a modality summary block
- [`docs/hydration_brief.md`](hydration_brief.md) — the session brief template (Part 2)

## End of v1.1 — final tagging

After session 20's PR merges cleanly:

1. Final release: `git tag v1.1.0 && git push --tags`
2. `gh release create v1.1.0 --title "v1.1.0 — hydration complete" --notes "20 sessions complete. Recipe count: <final>. See CHANGELOG.md for per-session breakdown."`
3. Update `README.md` recipe count and gallery link
4. Regenerate the full `docs/gallery/index.md` one final time
5. Announce in the skill's bootstrap mode: the catalog the agent reads
   now exposes 320+ recipes; this dramatically changes the density of
   the "propose with justification" table.

## Per-session briefs

Each of the 20 sessions has a ready-to-paste brief in
[`docs/hydration_briefs/`](hydration_briefs/). Index:

- [Session 01 — rhogtpase_dynamics](hydration_briefs/session_01_rhogtpase_dynamics.md)
- [Session 02 — fret_biosensors](hydration_briefs/session_02_fret_biosensors.md)
- [Session 03 — actin_microtubule_morphometry](hydration_briefs/session_03_actin_microtubule_morphometry.md)
- [Session 04 — mixed_effects_models](hydration_briefs/session_04_mixed_effects_models.md)
- [Session 05 — sensitivity_analysis](hydration_briefs/session_05_sensitivity_analysis.md)
- [Session 06 — redox_imaging](hydration_briefs/session_06_redox_imaging.md)
- [Session 07 — intravital_imaging](hydration_briefs/session_07_intravital_imaging.md)
- [Session 08 — gillespie_stochastic](hydration_briefs/session_08_gillespie_stochastic.md)
- [Session 09 — omics_differential](hydration_briefs/session_09_omics_differential.md)
- [Session 10 — calcium_signaling](hydration_briefs/session_10_calcium_signaling.md)
- [Session 11 — single_cell_embeddings](hydration_briefs/session_11_single_cell_embeddings.md)
- [Session 12 — dose_response_pharmacology](hydration_briefs/session_12_dose_response_pharmacology.md)
- [Session 13 — network_and_pathway](hydration_briefs/session_13_network_and_pathway.md)
- [Session 14 — biophysics_scaling](hydration_briefs/session_14_biophysics_scaling.md)
- [Session 15 — diffusion_and_tracking](hydration_briefs/session_15_diffusion_and_tracking.md)
- [Session 16 — spatial_statistics](hydration_briefs/session_16_spatial_statistics.md)
- [Session 17 — grant_and_conceptual](hydration_briefs/session_17_grant_and_conceptual.md)
- [Session 18 — meta_and_diagnostic](hydration_briefs/session_18_meta_and_diagnostic.md)
- [Session 19 — clinical_cohort](hydration_briefs/session_19_clinical_cohort.md)
- [Session 20 — cryoem_and_structure](hydration_briefs/session_20_cryoem_and_structure.md)
