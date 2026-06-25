<!--
Thanks for contributing to panelforge-figures!
Keep PRs focused. See CONTRIBUTING.md for the full local dev loop — the
checklist below mirrors exactly what CI enforces on every PR.
-->

## What this changes

<!-- A short description of the change and the motivation. Link any related issue: "Closes #123". -->

## Type of change

- [ ] Bug fix
- [ ] New recipe / modality
- [ ] CLI / library feature
- [ ] Docs / packaging / CI
- [ ] Refactor (no behavior change)

## Checklist — these are the CI gates (run them locally first)

- [ ] `ruff check src tests` is clean
- [ ] `pytest -q -m "not slow"` passes (note which optional extras you installed, e.g. `.[dev,power,mcp]`)
- [ ] If recipe metadata/tags changed: `figures index emit` run and the updated `recipes_index.json` is **committed** (CI fails on index drift)
- [ ] `figures index validate` passes
- [ ] If a recipe's appearance changed: `figures gallery regenerate` run and updated PNGs committed (`figures gallery diff` shows the drift)
- [ ] Recipe count is intentional — `figures catalog --json` matches what you meant to add/remove (CI floors at ≥107; the suite is currently 471)
- [ ] No secrets added (the `secret-scan` / gitleaks job must stay green; run `gitleaks dir .` locally)
- [ ] Added/updated tests for any behavior change; new public API has a docstring

## Notes for reviewers

<!-- Anything reviewers should focus on, trade-offs, or follow-ups intentionally left out of scope. -->
