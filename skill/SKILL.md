---
name: panelforge-figures
description: Bootstrap, resurvey, or extend publication-grade figures in any manuscript repo. Use when the user asks to set up figures, generate manifests, add figures, refresh after package updates, or survey an unfamiliar analysis repo. Operates across arbitrary manuscript layouts via modality-first recipe matching. Always proposes with justifications against alternatives — never silently selects generic fallbacks.
---

# panelforge-figures skill

Agentic layer for setting up, updating, and extending the
`panelforge-figures` system inside any manuscript repository. The package
itself is fully deterministic; this skill is used once per repo (bootstrap),
then occasionally (resurvey, add_figure).

## Mode selection

- If `figures.manifest.yaml` does NOT exist → **bootstrap**.
  Read `modes/bootstrap.md`.
- If `figures.manifest.yaml` exists AND the user asks to refresh/adapt →
  **resurvey**. Read `modes/resurvey.md`.
- If `figures.manifest.yaml` exists AND the user asks to add ONE figure →
  **add_figure**. Read `modes/add_figure.md`.
- If the user's intent is ambiguous, ask them to confirm which mode.

## Universal prerequisites

1. Verify `panelforge_figures` is installed:
   ```
   pip show panelforge_figures
   ```
   If missing, offer to install — confirm before running:
   ```
   pip install git+https://github.com/renatosocodato/panelforge-figures.git@v0.1.0-alpha
   ```
   Future stable: `@v0.1.0`.
2. Generate the catalog:
   ```
   figures catalog --json > /tmp/pf_catalog.json
   ```
   This is your ground truth for the installed version.
3. Verify git context:
   ```
   git rev-parse --show-toplevel
   ```
   Abort if not in a git repository.
4. Verify a clean working tree unless the user has confirmed uncommitted
   edits are intentional.

## Universal finishing steps

1. Run `figures validate figures.manifest.yaml` — must pass.
2. Run `figures render figures.manifest.yaml` — must produce all outputs
   under `figures/outputs/`.
3. Present a summary diff to the user: files added, files modified,
   figures produced with their paths.
4. Offer to commit on a new branch and open a PR, OR leave uncommitted.

## Non-negotiable behaviors

- **Propose with justification.** For every recipe you select, state at
  least one alternative from the same modality and why you rejected it.
  The justification is shown to the user BEFORE any file is written.
  The catalog's `alternatives_in_modality` field gives you the list of
  siblings to compare against.
- **Loud generic-fallback flags.** If no modality-specific recipe matches
  a data source, you MUST explicitly tell the user:
  > "I'm falling back to a generic recipe (`<name>`) because no
  > modality-specific recipe in `<inferred_modality>` matches this data.
  > Consider stubbing a custom recipe."
  Do not silently substitute.
- **Gallery-based preview.** When proposing a recipe, reference its
  gallery PNG path (`docs/gallery/<modality>/<recipe>.png` inside the
  installed package, also in the repo) so the user can see what it
  produces.
- **Local adapters are per-repo.** Never modify the installed package.
  Custom adapters go in `figures/adapters/local/` inside the manuscript
  repo.
- **One-shot manifest authoring.** Write the full manifest once the user
  has approved the plan. Do not iterate across many small edits.

## Constraints

- Do not modify anything outside `figures/`, `figures.manifest.yaml`,
  `figures.theme.toml`, `.github/workflows/figures.yml`, and `.gitignore`.
- Do not install the package globally without explicit user consent.
- Do not invent recipe names — only use names present in the catalog.
- Do not silence `figures validate` errors. Fix the cause.

## References

- `modes/bootstrap.md`
- `modes/resurvey.md`
- `modes/add_figure.md`
- `references/recipe_catalog_format.md`
- `references/manifest_schema.md`
- `references/contract_reference.md`
- `references/adapter_guide.md`
- `references/modality_guide.md`
- `references/local_adapter_template.py`
- `example_manifests/*.yaml`
- `templates/*`
