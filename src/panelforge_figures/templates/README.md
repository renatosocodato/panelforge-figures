# `panelforge_figures.templates` — package map

`templates/` holds **static user-facing scaffold files** — starter content a user
copies into their own manuscript repository to bootstrap a panelforge figures
workflow. These are not Python modules and no module imports them at runtime; they
are pure data shipped inside the wheel via the `[tool.setuptools.package-data]`
globs in `pyproject.toml`.

For where this fits, read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §3.10.

---

## The scaffold files

| File | What it is | Who copies it / where |
|---|---|---|
| `manifest.yaml` | A minimal `figures` manifest: `version`, `theme`, `palette`, a `catalog_fingerprint` placeholder, an empty `figures: []` list, and an `export` block (formats, outdir, dpi). | User copies it into their repo (conventionally as `figures.manifest.yaml`, the default path `figures render` / `figures validate` look for) and fills in `figures:`. |
| `theme.toml` | A two-line theme/palette selection stub (`theme`, `palette`). | User copies it into their project config to pin the active theme + palette. |
| `workflow.yml` | A GitHub Actions workflow that installs panelforge-figures, validates `figures.manifest.yaml`, renders, and uploads `figures/outputs/` as a build artifact. | User copies it to `.github/workflows/figures.yml` for CI rendering. |
| `outputs.gitignore` | Two ignore lines (`figures/outputs/`, `figures/cache/`) so rendered output + the render cache stay untracked. | User copies its contents into their repo `.gitignore` (or drops it in as `figures/.gitignore`). |

---

## Copied manually (for now)

There is **no in-package consumer** of these files and no `figures init` command —
the scaffolds are copied by hand today, and are structured so a future
`figures init`-style command could stamp them out (e.g. filling
`catalog_fingerprint` at bootstrap). Until such a command exists, treat them as
documentation-by-example: copy, rename to the conventional paths above, and edit.

---

## Packaging note

All four files must ship in the wheel. The `package-data` globs in `pyproject.toml`
cover them by extension:

```toml
[tool.setuptools.package-data]
panelforge_figures = [
    "templates/*.yaml",      # manifest.yaml
    "templates/*.toml",      # theme.toml
    "templates/*.yml",       # workflow.yml
    "templates/*.gitignore", # outputs.gitignore
]
```

The `*.gitignore` glob is required because `outputs.gitignore` has no extension
matched by the other three patterns — without it the file would be silently
omitted from the wheel. If you add a scaffold with a new extension, add a matching
glob here too.
