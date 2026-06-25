# `panelforge_figures.cli` — package map

`cli/` is the **command-line surface**: the `figures` executable (declared as the
`figures` console-script entry point in `pyproject.toml`). It is a thin,
non-interactive, scriptable Click dispatch layer over the
`manifest`/`core`/`safety` engine — most subcommands lazy-import their `manifest/*`
implementation *in-body* so `figures --help` and the base install stay fast and
dependency-light.

For the design rationale, read
[`docs/architecture_deep_dive.md`](../../../docs/architecture_deep_dive.md) §3.10.

---

## Module index

| Module | Role |
|---|---|
| `__init__.py` | The Click group `main` and every subcommand. Top-level imports are kept to `click`/`json`/`logging` + `adapters`/`core`/`catalog`; each command body lazy-imports the heavier `manifest/*` it needs. |
| `__main__.py` | Shim so `python -m panelforge_figures.cli <subcommand>` still works (some tests + downstream scripts rely on it). |
| `tui_scout.py` | The interactive scout TUI behind `figures scout --interactive` (E15, v3.9.0) — a [textual](https://textual.textualize.io/) UI over the read-only `scout_project` pipeline. |

`cli` was promoted from a single module to a **package** in v3.9.0 solely to
co-locate the textual TUI alongside the main Click group; `__main__.py` preserves
the original invocation.

---

## What the commands cover

`figures` dispatches into nearly every `manifest` module. Representative verbs:

- **Render / validate** — `figures render`, `figures validate` (drive
  `render_manifest` / `validate_manifest`).
- **Catalog / discovery** — `figures catalog`, `figures list-recipes`,
  `figures scout` (+ `--interactive`).
- **Audit chain** — `figures audit-venue`, `figures audit-bias`, `figures
  verify-claims`, `figures lint xrefs`, `figures caption`, `figures cite suggest`,
  `figures star-methods`, `figures checklist <name>`, `figures status`,
  `figures ci-audit`.
- **Config** — `figures config set data_class ...` (the only sanctioned path into
  `safety.set_data_class`).
- **MCP** — `figures mcp serve` (calls `mcp.server.serve_stdio_sync`).

Run `figures --help` for the authoritative, live list.

---

## How it fits the architecture

`cli/` is a **surface**, not engine logic: it parses arguments, calls into the
manifest/core pipeline, and formats results. The in-body lazy-import discipline is
deliberate — it keeps the cold-start cost of the executable low and lets the base
install skip heavy optional dependencies until a command that needs them runs.

Note: `figures index emit` (re)generates the checked-in `recipes_index.json`
build artifact — do not run it casually, as it rewrites a tracked file.
