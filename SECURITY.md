# Security Policy

This document covers the panelforge-figures supported versions, the
responsible-disclosure policy, the hooks downstream consumers should
configure, and (optionally) the recipe for rewriting git history when
sensitive identifiers leak into past commits.

## Supported versions

| Major | Status                          |
|-------|---------------------------------|
| 3.x   | Active — receives security fixes |
| < 3.0 | End of life — no fixes           |

The current security baseline is **v3.14.1** (security patch release).
Patch releases on the active major receive backports for any
issue flagged via the disclosure channel below.

## Reporting a vulnerability

If you find a security issue in panelforge-figures, **please do not
file a public GitHub issue**. Instead, e-mail the maintainer at:

> renato.socodato@gmail.com

Include:

- A short description of the vulnerability.
- A reproducer (minimum viable example, command sequence, or commit
  hash that demonstrates the leak).
- The version (`figures --version`) and Python environment.

We try to acknowledge new reports within **5 business days** and to
ship a patch (or a documented mitigation) within **30 days** of
initial acknowledgement, whichever is sooner.

Coordinated disclosure is preferred — please give us a chance to
prepare a fix before public discussion.

## Pre-commit hooks (recommended for downstream consumers)

panelforge-figures ships a `.pre-commit-config.yaml` that activates
three checks on every commit:

1. **detect-secrets** — catches accidentally-committed credentials
   (API keys, private keys, etc.).
2. **gitleaks** — secondary scan with a different ruleset; complements
   detect-secrets.
3. **ruff** + **ruff-format** — code-style + lint.

To opt in (one-time setup):

```bash
pip install pre-commit detect-secrets
pre-commit install
detect-secrets scan > .secrets.baseline   # only if .secrets.baseline is missing
```

Every subsequent `git commit` then runs the three checks before the
commit lands. To skip them in an emergency (do not make a habit of
this):

```bash
SKIP=detect-secrets,gitleaks git commit ...
```

`SECURITY.md` and the CI workflow `.github/workflows/secret-scan.yml`
also run gitleaks on every push and pull request to `main`, providing
a server-side backstop independent of the local pre-commit hook.

## History rewrite (OPTIONAL — destructive)

The current tree is scrubbed of personal paths and unpublished-project
references as of v3.14.1. **Historical commits still contain the
original identifiers.** A `git filter-repo` rewrite can remove them
from the past as well, but it is *destructive*: it rewrites every
commit hash, breaks every cached clone and fork, and invalidates every
git tag's signature. Only do this if the residual exposure in the
history actually matters to your threat model.

```bash
# 1. Install git-filter-repo (https://github.com/newren/git-filter-repo)
pip install git-filter-repo

# 2. Clone a fresh mirror — DO NOT rewrite history on your working clone.
git clone --mirror https://github.com/<owner>/panelforge-figures.git
cd panelforge-figures.git

# 3. Prepare a replacements file with the patterns to scrub.
cat > /tmp/replacements.txt <<'EOF'
<home>==>~
<home>==>~
example_modality_a==>example_modality_a
example_modality_b==>example_modality_b
example_grant==>example_grant
example_factorial_manuscript==>example_factorial_manuscript
morphometry_biophysics_workspace==>morphometry_biophysics_workspace
EOF

# 4. Dry-run first to inspect what would change.
git filter-repo --replace-text /tmp/replacements.txt --dry-run

# 5. Apply for real (creates a new history).
git filter-repo --replace-text /tmp/replacements.txt

# 6. Force-push the rewritten history.  Coordinate with collaborators
#    FIRST — they will need to re-clone after this lands.
git push --mirror --force origin
```

After step 6:

- **All collaborators must re-clone.** Existing clones will have stale,
  conflicting history and any local branch they were working on will
  need to be replayed onto the rewritten parent.
- **All forks become stale.** Forks on GitHub continue to host the
  pre-rewrite history; fork owners must rebase or re-fork.
- **All signed tags are broken.** Re-sign every tag you care about
  (`git tag --sign --force <tag>` then `git push --tags --force`).

This is why we leave the history alone by default. The current-tree
scrub (v3.14.1) is sufficient for the published release artefact;
the history rewrite is an extra step you take only if your audit
explicitly requires zero residual exposure.

## Threat model

panelforge-figures is a **renderer**, not a data-storage system. The
library never network-calls without explicit user opt-in (the
optional `claude-autonomous` and `mcp` extras), never executes
plugin code without the user having installed it locally, and never
silently writes data outside the working project tree.

The primary security concerns for this library are therefore:

1. **Plugin trust** — plugins are arbitrary Python that runs in the
   panelforge process. Treat them with the same caution you would
   any `pip install`.
2. **Personal-information leaks** — paths, project IDs, or unpublished
   manuscript names that end up in committed files or rendered PDFs
   leak the user's identity / work-in-progress. v3.14.1 introduces
   the gitleaks CI step and the pre-commit hook to catch these.
3. **Reproducibility-bundle privacy** — `figures lock` writes a
   reproducibility bundle that includes the user's Python+OS+package
   manifest. Treat the bundle as PII-equivalent; do not commit it to
   a public repo without review.

Out of scope:

- Sandboxing plugin execution (see roadmap `spec_project_plugins.md`).
- Cryptographic signing of recipe outputs.
- Auditing the matplotlib/numpy/etc. supply chain (deferred to the
  Python packaging ecosystem).
