# Session 17 — Gap Analysis: `grant_and_conceptual` (6 → 15, +9)

**Branch:** `v1.1/session-17-grant_and_conceptual`
**Status:** Awaiting user approval. No implementation until the table below is approved.

## Context — what this session is

`grant_and_conceptual` powers **ATHENA**, **MIRROR**, and Horizon
Europe proposals. v1.0 ships the **conceptual triptych**, **executive
summary tile**, **hypothesis diagram**, **team expertise matrix**,
**Gantt with milestones**, and **work-package flow** (6 recipes).
Missing are the **aims pyramid**, **linear methods pipeline**,
**milestone × risk matrix**, **innovation-positioning quadrant**,
**cost-by-WP bars**, **ethics & impact block**, **interdisciplinary
spider**, **deliverables timeline**, and **consortium network graph**
reviewers expect.

## Current 6-recipe state

| # | recipe | family | role |
|---|---|---|---|
| 1 | `conceptual_triptych` | `conceptual` | problem → approach → payoff narrative |
| 2 | `executive_summary_tile` | `conceptual` | headline-impact tile |
| 3 | `hypothesis_diagram` | `conceptual` | central H, supporting data, test predictions |
| 4 | `team_expertise_matrix` | `matrix` | team × competency |
| 5 | `timeline_gantt_with_milestones` | `gantt` | WP / task Gantt |
| 6 | `work_package_flow` | `flow` | WP dependency graph |

## Proposed 9 new recipes

All 9 use **new per-recipe Pydantic contracts** local to their `.py` file. **No changes to `core/contract.py`**. No new top-level dependencies. No cross-modality edits. Designed for A4 portrait FCT / Horizon Europe formats with Portuguese-safe (ASCII-substitute) typography.

### Aims, methods, narrative (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N1 | `research_aims_pyramid` | How do **specific aims** nest under an overarching objective and hypothesis? | `conceptual_triptych` (3-panel linear narrative); `hypothesis_diagram` (H + test) | **Hierarchical** pyramid: objective at top → aims in middle → sub-questions at bottom, colour-coded by stage. Different topology (hierarchical, not linear). | `conceptual` |
| N2 | `methods_pipeline_flow` | What are the **sequential** data-generation and analysis steps? | `work_package_flow` (WP **dependency graph**, potentially cyclic) | **Strictly linear** pipeline with one input and one output, arrow-connected rounded boxes. Axis grammar differs (linear vs DAG). | `flow` |

### Risk, innovation, cost (+3)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N3 | `milestone_vs_risk_matrix` | Which **milestones** are high-risk / high-impact? | `team_expertise_matrix` (team × competency) | **Milestone × axis** 2 × 2 placement with per-milestone tile and risk-rated border. Different axis pair and content type. | `matrix` |
| N4 | `innovation_positioning_quadrant` | Where does **our proposal** sit on a novelty × feasibility quadrant relative to state-of-the-art competitors? | None — no positioning recipe in v1.0 | 2D quadrant with competitor markers + our-proposal marker + quadrant labels. Different axis grammar (positioning plot). | `matrix` |
| N5 | `cost_by_work_package_bar` | How is the **budget** distributed across WPs, broken down by cost category? | `timeline_gantt_with_milestones` (time); `team_expertise_matrix` (competency) | Stacked horizontal bars per WP with category shares + total callout. Different statistic (cost, not time / competency). | `ladder` |

### Ethics, interdisciplinarity, consortium (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N6 | `ethics_and_impact_block` | What are the **ethics** safeguards and **societal impact** pathways of this proposal? | `executive_summary_tile` (headline only); `conceptual_triptych` (narrative arc) | Two-column block with ethics sub-sections (data protection, animal welfare, DEI) + impact sub-sections (scientific, societal, economic). Different content type and layout. | `conceptual` |
| N7 | `interdisciplinary_contribution_spider` | How **interdisciplinary** is the proposal across disciplines (biology, maths, engineering, clinical, industry)? | `team_expertise_matrix` (team × competency, matrix view) | Radar / spider plot with discipline axes and proposal "coverage" polygon; different family (radar) and summary view. | `radar` |

### Team, deliverables (+2)

| # | name | answers_question | nearest existing | why distinct | family |
|---|---|---|---|---|---|
| N8 | `team_network_graph` | How do **partners** in the consortium connect (role, seniority, inter-institutional links)? | `team_expertise_matrix` (team × competency — no relational structure); `work_package_flow` (WP, not partners) | Spring-layout graph with partner nodes (colour by institution) and edges (prior-collaboration / shared-project). Different content type (partners + relations) and axis grammar (graph). | `conceptual` |
| N9 | `deliverables_timeline` | When does each **deliverable** (D) deposit, and which WP does it belong to? | `timeline_gantt_with_milestones` (tasks, not deliverables; shows duration bars) | **Point-event** timeline of deliverables with WP colour coding, status-due markers, and EU-Horizon D1.1-style IDs; not a Gantt duration chart. | `gantt` |

## Distinctness summary

All 9 pass the three distinctness tests:

1. **No name collision** with the 6 existing recipes.
2. **No question duplication** — each answers a question no existing recipe answers (aims hierarchy, linear methods, risk matrix, innovation positioning, cost breakdown, ethics + impact, interdisciplinary coverage, consortium network, deliverable-event timeline).
3. **No grammar duplication** — `conceptual` × 3 (aims pyramid, ethics block, team network) each with distinct layouts; `flow` × 1 (linear) vs existing `work_package_flow` (DAG); `matrix` × 2 (milestone-risk, innovation-positioning) with distinct axis pairs; `ladder`, `radar`, `gantt` each × 1.

## Portuguese-safe typography

All nine recipes emit Helvetica-safe ASCII substitutes for arrows (`->`, `<-`) and mathematical symbols, matching the s14 / s15 polish pattern. No accented characters in data fields — demos use EU-project-style names (WP1, D1.1) that are already ASCII.

## Invariants this session preserves

- [x] No changes to `core/`.
- [x] No new top-level dependencies.
- [x] No edits to other modalities.
- [x] No renames of existing recipes.
- [x] All 9 recipes use the existing `ModalityAesthetic`.
- [x] All 9 families dispatch to existing `quality_rules.py` functions.
- [x] Style-drift ratchet: reuse `PF_FONT_SIZES` and `PF_LINE_WIDTHS`; no new literals.

## STOP — user approval required

**Proposed outcome:** land all 9 → modality goes from **6 → 15** recipes. Total catalog goes from **290 → 299**. Tests projected: **1501 → ~1546** (5 per recipe × 9).

To approve, reply "approved". To adjust, reply with the specific recipes to swap / drop / rename. To abort, reply "abort".
