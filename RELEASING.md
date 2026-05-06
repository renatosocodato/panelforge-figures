# Releasing panelforge-figures

The release pipeline is fully automated via OIDC trusted publishing.
No PyPI tokens are stored as GitHub secrets.

## One-time setup (PyPI side)

The repo owner must register the GitHub repo as a **Trusted Publisher**
on both PyPI and TestPyPI.  This is required only once.

### PyPI (production)

1. Go to https://pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher" (or edit an existing project).
3. Fill in:
   - **PyPI Project Name**: `panelforge-figures`
   - **Owner**: `renatosocodato`
   - **Repository name**: `panelforge-figures`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. Save.

### TestPyPI

Same steps at https://test.pypi.org/manage/account/publishing/ but use
**Environment name**: `testpypi` instead.

### GitHub environment configuration

In the GitHub repo:
1. Settings → Environments → New environment.
2. Create two environments named `pypi` and `testpypi`.
3. (Optional) Add required reviewers for the `pypi` environment to
   gate production publishes.

## Per-release procedure

For a stable release (e.g. `v1.6.1`):

```bash
# 1. Bump version in pyproject.toml + src/panelforge_figures/__init__.py.
# 2. Add a CHANGELOG.md "## [1.6.1] — YYYY-MM-DD" entry.
# 3. Commit + merge via PR.
# 4. After merge, tag and push:
git tag -a v1.6.1 -m "Release v1.6.1"
git push origin v1.6.1
```

The tag push triggers `release.yml`, which:
1. Builds wheel + sdist.
2. Runs `twine check --strict`.
3. Smoke-tests the wheel in a fresh venv.
4. Publishes to PyPI via OIDC (no token).
5. Creates a GitHub Release with notes pulled from CHANGELOG.

For a pre-release (e.g. `v1.6.1-rc1`), follow the same steps; the
workflow auto-detects the suffix and routes to TestPyPI instead.

## Verification

After the workflow completes:
- https://pypi.org/project/panelforge-figures/ should show the new version.
- `pip install panelforge-figures==X.Y.Z` should work in a clean venv.
- The GitHub Release page should have the CHANGELOG excerpt + dist artifacts.

## Rollback

PyPI does not support deleting versions (only yanking).  If a release
is broken:

```bash
# Yank via PyPI web UI (Manage → Project → Releases → yank version).
# Then bump to the next patch and re-release.
```

The yank prevents new installs from selecting the broken version while
preserving the audit trail.
