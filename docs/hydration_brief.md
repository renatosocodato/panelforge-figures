# v1.1 Session Brief — Template

The skeleton every session fills in. Generic name fields are
`<MODALITY>`, `<SESSION_NUM>`, `<V10_COUNT>`, `<V11_TARGET>`,
`<PRIORITY_CONTEXT>`. Per-modality parameterized versions live under
[`docs/hydration_briefs/`](hydration_briefs/).

---

# Task: v1.1 session `<SESSION_NUM>` — hydrate `recipes/<MODALITY>/` to `<V11_TARGET>` recipes

## Context

`panelforge-figures` is live at `v1.0.<PATCH>`, installed at the user's
Python environment. Repo: `github.com/renatosocodato/panelforge-figures`.
Current modality `<MODALITY>` has `<V10_COUNT>` recipes. This session
expands it to ≥ `<V11_TARGET>`.

Priority context for this modality: `<PRIORITY_CONTEXT>`

## Hard constraints

- Do not modify any modality other than `<MODALITY>`
- Do not modify `core/style.py`, `core/layout.py`, `core/export.py`,
  `core/primitives.py`, `core/palette.py`, `core/aesthetic_base.py`,
  `themes/`, `cli.py`, `manifest/`
- Permitted contract extension: add new Pydantic models to
  `core/contract.py` if strictly required. All additions must be
  backward-compatible (no breaking changes to existing contracts).
  Clearly comment them with `"Added for v1.1 session <SESSION_NUM>"`
- No new package dependencies
- Every new recipe: ≥ 80 lines (excluding docstring/imports), honors
  `<MODALITY>/_aesthetic.py`, uses semantic palette lookup, has
  `demo_contract` attribute, has gallery PNG, has quality-gate test,
  has aesthetic-compliance test
- Do not silence warnings, do not bypass existing tests, do not skip
  failing tests

## Commit structure (three commits, squash-merged at PR close)

### Commit 1 — Gap analysis (markdown only)

1. Read `src/panelforge_figures/recipes/<MODALITY>/__init__.py` to
   list existing recipes and their `answers_question` fields
2. Read `src/panelforge_figures/recipes/<MODALITY>/_aesthetic.py` to
   internalize the modality's visual DNA
3. Examine `docs/gallery/<MODALITY>/*.png` to see what's already
   visually covered
4. Propose `<GAP>` new recipes (where `<GAP> = <V11_TARGET> − <V10_COUNT>`)
   as a table with columns:
   - `name` (snake_case, describes scientific question)
   - `answers_question` (one-sentence scientific question the recipe visualizes)
   - `contract` (existing contract from `core/contract.py`, or new contract name to be added)
   - `required_fields`
   - `optional_fields`
   - `closest_existing_alternative` (from the current `<V10_COUNT>` roster)
   - `why_distinct` (how it differs from the closest alternative)
   - `visual_signature` (2-3 sentences on what makes this recipe visually distinct — aesthetic choices, annotation types, colormap, layout)
   - `data_shape_hints` (file format, column patterns, typical n)
5. Commit the table to a new file:
   `docs/hydration_gap_analysis/session_<SESSION_NUM>_<MODALITY>.md`
6. **STOP and await user approval of the table before Commit 2.** Do
   not proceed to implementation.

### Commit 2 — Implementation

For each approved recipe in the gap analysis:

1. Add contract to `core/contract.py` if it's new
2. Create `src/panelforge_figures/recipes/<MODALITY>/<recipe_name>.py`
3. Implement the recipe:
   - `from ._aesthetic import AESTHETIC` at top
   - `from ..core.palette import get_palette, semantic` at top
   - `from ..core.primitives import <needed primitives>` at top
   - Function signature:
     `def <recipe_name>(ax, contract, palette=AESTHETIC.primary_palette, **opts) -> Axes`
   - Validate contract at entry:
     `contract = <ContractName>.model_validate(contract)`
   - Apply `AESTHETIC.apply_to_ax(ax)`
   - Render per the `visual_signature` specified in gap analysis
   - Honor all fidelity requirements from `docs/architecture.md`
     (halo'd labels, `smart_fmt`, bootstrap CIs where applicable,
     ring-marker overlays for violins, etc.)
   - ≥ 80 lines excluding docstring + imports
   - Attach `.demo_contract()` returning a realistic synthetic input
4. Update `src/panelforge_figures/recipes/<MODALITY>/__init__.py` to
   register the new recipe in the modality's `RECIPES` dict with full
   metadata (`answers_question`, `contract`, `alternatives_in_modality`,
   etc.)
5. If `_aesthetic.py` needs new vocabulary (e.g. a new annotation
   style the new recipes share), extend it without breaking existing
   recipes. Each extension is additive.
6. Update `docs/recipes_by_modality.md` and
   `docs/recipes_by_question.md` by running `figures catalog --json`
   and regenerating via the existing doc-generator script

### Commit 3 — Gallery + tests

1. Run `figures gallery regenerate --modality <MODALITY>` — produces
   updated PNGs in `docs/gallery/<MODALITY>/`
2. Commit all new and updated gallery PNGs
3. Add to `tests/quality_rules/<MODALITY>.py`: entries for each new
   recipe specifying family-specific fidelity markers (e.g. "recipe X
   must have ≥ 2 halo'd text annotations", "recipe Y must have a
   filled CI band + mean line + per-group legend")
4. Run full test suite: `pytest -q`
5. Assert test count has grown by the number of new recipes times the
   number of test layers (smoke + quality + aesthetic compliance = 3
   tests per recipe)
6. Run `figures catalog --json` and confirm modality recipe count
   matches `<V11_TARGET>` or higher

## PR discipline

Branch name: `v1.1/session-<SESSION_NUM>-<MODALITY>`

PR title: `feat(<MODALITY>): hydrate to <V11_TARGET> recipes — v1.1 session <SESSION_NUM>`

PR body:
- Before/after recipe counts
- List of new recipes with one-line descriptions
- Link to gap analysis file
- Link to gallery PNG diff summary
- Test count before/after
- Confirmation that no cross-modality files changed

## Universal finishing steps

1. `pytest -q` green on Python 3.11 and 3.12 matrix
2. `figures catalog --json | jq '.modalities[] | select(.name=="<MODALITY>") | .recipes | length'` returns ≥ `<V11_TARGET>`
3. `figures render tests/fixtures/minimal.manifest.yaml` produces outputs
4. Gallery diff CI check passes (no unwanted regression in untouched modalities)
5. `CHANGELOG.md` updated with `v1.1.0-s<SESSION_NUM>` block listing new recipes
6. Tag release: `git tag v1.1.0-s<SESSION_NUM> && git push --tags`
7. GitHub release via `gh release create v1.1.0-s<SESSION_NUM> --title "v1.1.0 session <SESSION_NUM> — <MODALITY>" --notes-file <changelog section>`
8. Report PR URL and release URL to user

## Success criteria

- Modality `<MODALITY>` has ≥ `<V11_TARGET>` recipes
- All new recipes pass smoke + quality + aesthetic-compliance tests
- Gallery regenerated with new PNGs
- No changes outside `recipes/<MODALITY>/`, `core/contract.py`,
  `docs/gallery/<MODALITY>/`, `docs/hydration_gap_analysis/`,
  `docs/recipes_by_modality.md`, `docs/recipes_by_question.md`,
  `CHANGELOG.md`, `tests/quality_rules/<MODALITY>.py`
- Tagged release `v1.1.0-s<SESSION_NUM>` exists
- PR merged to `main` via squash
