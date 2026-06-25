# Contributing to panelforge-figures

Thanks for your interest in contributing! This guide describes the local
development loop. **Every command here is exactly what CI runs** — if it passes
locally, it passes on GitHub.

By participating you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md). For usage questions (not contributions),
see [SUPPORT.md](SUPPORT.md).

**Contents:**
[1. Dev environment](#1-development-environment) ·
[2. Invariants / CI gates](#2-project-invariants-what-ci-enforces) ·
[3. Code style](#3-code-style) ·
[4. Adding a recipe](#4-the-recipe-contract--adding-a-recipe) ·
[5. Index & gallery](#5-the-recipe-index-and-gallery) ·
[6. Tests](#6-tests) ·
[7. Security & privacy](#7-security--privacy) ·
[8. Commits & PRs](#8-commits--pull-requests) ·
[9. Releases](#9-releases-maintainers)

---

## TL;DR — the local gate

```bash
# one-time setup (note the quotes — required on zsh / macOS)
python -m pip install -e ".[dev]"

# the checks CI enforces on every PR
ruff check src tests
pytest -q -m "not slow"
figures index emit && git diff --exit-code recipes_index.json && figures index validate
```

If those three pass and you didn't change a recipe's appearance, your PR will go
green. The rest of this document explains each step and the project invariants
behind them.

---

## 1. Development environment

Requires **Python ≥ 3.11** (CI tests 3.11 and 3.12).

```bash
git clone https://github.com/renatosocodato/panelforge-figures.git
cd panelforge-figures

# a virtual environment is recommended
python -m venv .venv && source .venv/bin/activate

# editable install with the dev tools
python -m pip install -e ".[dev]"
```

> **zsh / macOS gotcha:** the brackets in `.[dev]` are a glob pattern in zsh
> (the macOS default shell) and will fail with `no matches found: .[dev]`.
> **Always quote it:** `pip install -e ".[dev]"`. (Bash does not need the
> quotes, but they are harmless there.)

The `dev` extra pulls in `pytest`, `pytest-cov`, `ruff`, `jsonschema`,
`hypothesis`, and `seaborn`. This runs the **core** suite. A handful of tests
that exercise optional dependencies are **skipped** unless you install those
extras too:

```bash
# run the optional-dependency tests as well (power analysis, MCP server, …)
python -m pip install -e ".[dev,power,mcp,recommender,novelty]"
```

This is intentional and matches CI, which installs only `.[dev]` — so those
tests skip on CI as well. Install the extras locally only if you're touching
those subsystems.

After installation the `figures` CLI is on your PATH:

```bash
figures --version          # figures, version 3.14.1
figures --help             # full command list
```

(Equivalent without installing: `PYTHONPATH=src python -m panelforge_figures.cli …`.)

---

## 2. Project invariants (what CI enforces)

| Invariant | Gate | How to check |
|---|---|---|
| Lint clean | `ruff check src tests` | run it |
| Tests pass | `pytest -q -m "not slow"` | run it |
| Catalog builds; recipe count ≥ 107 (CI floor — **currently 471**) | `figures catalog --json` | CI asserts `n >= 107` |
| `recipes_index.json` is **not stale** | `figures index emit` ⇒ no diff | see §4 |
| Index is schema-valid | `figures index validate` | run it |
| Gallery re-renders; ≥ 107 PNGs (CI floor; one per recipe = 471) | `figures gallery regenerate` | see §5 |
| No secrets committed | `gitleaks` (`secret-scan` job) | `gitleaks dir .` |
| **No warnings** | `pytest` runs with `filterwarnings=error` | any new warning fails the suite |

The last one is worth calling out: the test suite treats warnings as errors. If
your change introduces a `DeprecationWarning` (or any warning), the suite will
fail. Fix the cause, or — only for a genuine third-party warning outside our
control — add a narrowly-scoped ignore to `[tool.pytest.ini_options]`
`filterwarnings` in `pyproject.toml`.

---

## 3. Code style

Linting and import-sorting are handled by **ruff** (line length 100, target
`py311`, rule sets `E`, `F`, `W`, `I`, `UP`):

```bash
ruff check src tests          # the gate (must be clean)
ruff check --fix src tests    # auto-fix what it can (import order, simple lint)
```

CI runs `ruff check src tests`; keep it clean. Note: the project's gate is the
**linter** — CI does not run `ruff format`, so please don't reformat the whole
tree (`ruff format` would touch hundreds of files and add noise to your diff).
Match the style of the surrounding code.

---

## 4. The recipe contract & adding a recipe

Every recipe is a self-contained module with four mandatory artifacts, in order:
a pydantic `RecipeContract` subclass (the input schema), a private `_demo()`
returning a populated contract, a frozen `_META` `RecipeMetadata`, and a
`render(contract, ax=None, **_)` decorated with `@register_recipe`. Recipes are
named by the **scientific claim** they visualize (`bistability_hysteresis`), not
the shape they draw.

Scaffold a new recipe with the CLI — it wires up all four artifacts plus a test
and a gallery PNG; you fill in the rendering body:

```bash
figures author-recipe \
  --modality <modality> \
  --name <recipe_name> \
  --family <family> \
  --research-question "<plain-English question this figure answers>"
```

(`--modality`, `--name`, `--family`, and `--research-question` are all required;
run `figures author-recipe --help` for the full option list.)

Browse what already exists first (the design rule: name an alternative in the
same modality and say why it's rejected):

```bash
figures list-recipes --by-modality
figures show-recipe <modality>.<recipe>
```

See also `docs/adding_a_recipe.md` and `docs/adding_a_modality.md`.

---

## 5. The recipe index and gallery

Two committed artifacts are **generated** from the recipe registry and must stay
in sync, or CI fails:

**`recipes_index.json`** — the agent-facing catalog. If you add/remove a recipe
or change recipe metadata or tags, regenerate and **commit** it:

```bash
figures index emit                      # writes recipes_index.json (stable headers auto-set at repo root)
git diff --exit-code recipes_index.json # CI runs this — a non-empty diff means "stale, regenerate & commit"
figures index validate                  # schema + content check
```

> This index-drift check is the single most common CI surprise: a recipe/tag
> change that passes the tests still fails CI if you forget to re-emit and commit
> the index. `figures index emit` is deterministic.

**`docs/gallery/<modality>/<recipe>.png`** — one example image per recipe. If
your change alters a recipe's **appearance**, regenerate and commit the affected
PNGs:

```bash
figures gallery diff         # show which recipes' rendered output drifted
figures gallery regenerate   # re-render all gallery PNGs (heavy)
```

If you didn't touch rendering, you don't need to regenerate the gallery.

---

## 6. Tests

```bash
pytest -q -m "not slow"      # the PR suite (this is the default; addopts already excludes "slow")
pytest -q                    # same as above — "slow" e2e tests are deselected by default
pytest tests/test_foo.py     # a single module while iterating
```

- Add or update tests for any behavior change. New public API needs a docstring.
- The `slow` marker is reserved for heavyweight end-to-end tests; they run on the
  scheduled `recipe_tags_audit` workflow, not on PRs.
- Coverage (as CI reports it):
  `pytest -q -m "not slow" --cov=panelforge_figures --cov-report=term-missing`.

---

## 7. Security & privacy

- **Never commit secrets.** The `secret-scan` (gitleaks) job runs on every PR.
  Check locally before pushing:

  ```bash
  gitleaks dir .
  ```

- panelforge is **privacy-by-construction**: a three-tier data class
  (`clinical` / `research` / `public`) gates every off-host capability (LLM
  column binding, vision, telemetry, network plugins). `clinical` forces them
  **off** and cannot be overridden. If you touch any of those channels, preserve
  this guarantee and add a test for the `clinical` path.
- Never include real clinical or personally identifying data in issues, tests,
  fixtures, or commits. Use synthetic data (every recipe's `_demo()` already
  provides some).

---

## 8. Commits & pull requests

- Keep PRs focused on a single change; smaller is easier to review.
- Branch off `main`; open the PR against `main`.
- Fill in the PR template — its checklist mirrors the CI gates in §2.
- Make sure the three TL;DR checks pass locally first.

---

## 9. Releases (maintainers)

Releases are automated via `.github/workflows/release.yml` (tag → build →
PyPI via OIDC → GitHub Release → Zenodo archive). The one-time setup is
documented in [`SETUP-PYPI.md`](SETUP-PYPI.md) and
[`SETUP-ZENODO.md`](SETUP-ZENODO.md). Bump the version in `pyproject.toml` and
`CITATION.cff` together.

---

Questions? Open an
[issue](https://github.com/renatosocodato/panelforge-figures/issues/new/choose).
Thank you for contributing!
