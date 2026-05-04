# `panelforge_workspace/` — agent state cache

Hi! If you're reading this, you've stumbled across the workspace directory
that the `figures` CLI auto-creates the first time it runs against your
project. Nothing in here is precious — this whole tree is **disposable
cache**.

## What is it?

When a Claude Code agent (or anyone running the autonomous bootstrap
documented in [`CLAUDE_CODE_AUTONOMOUS.md`](../CLAUDE_CODE_AUTONOMOUS.md))
walks the seven-step procedure on your project, it stages intermediate
state here so subsequent runs don't have to redo work that already
converged. Think of it the way `pip` thinks of `~/.cache/pip/`:
regenerable, never load-bearing, safe to nuke.

## What's inside

- **`profile.json`** — the assembled `ProjectProfile` from `figures intake`
  / `figures profile scan`. Captures the eight intake answers (anchor,
  factorial, equivalence, dynamics, dimensionality, modalities, hard
  filters, shortlist size) plus the per-field confidence band (`[inferred]`
  / `[inferred — review]` / `[asking]`) the scanner emitted. The scorer
  reads this file; the bridge reads this file; the render loop reads this
  file. It is the *only* persisted form of the user's intake answers.
- **`data_bridge_cache.json`** — confirmed column→contract bindings produced
  by `figures bridge` after checkpoint 2. On subsequent runs the bridge
  looks here first and skips the (slow, paid) Pass-3 LLM step entirely
  when bindings haven't changed. Delete this file to force a fresh bridge
  run.
- **`.gitignore`** — a single-line ignore rule so the directory's
  contents don't accidentally land in your project's git history. The
  file itself is harmless to commit; everything else here should not be.

## Should I commit it?

**No.** This directory belongs in your project's top-level `.gitignore`:

```gitignore
# panelforge-figures auto-generated cache — never commit.
panelforge_workspace/
```

`profile.json` carries no secrets, but it's tied to a specific scan run
and is regenerated automatically — committing it just adds noise to
diffs. `data_bridge_cache.json` is even more volatile.

## How do I reset?

```bash
rm -rf panelforge_workspace/
```

That's it. The next `figures intake` (or `figures profile scan`) call
will recreate the directory, rerun the scan, prompt you through the
intake checkpoints again, and rebuild the bridge cache from scratch.
Use this whenever you change your project's `manuscript.tex`, switch
manuscript anchors, or just want a clean slate.

## See also

- [`CLAUDE_CODE_AUTONOMOUS.md`](../CLAUDE_CODE_AUTONOMOUS.md) — the
  seven-step procedure that populates this directory.
- [`docs/AGENT_RECIPES.md`](../docs/AGENT_RECIPES.md) — worked-example
  walkthrough showing what ends up in here at each step.
