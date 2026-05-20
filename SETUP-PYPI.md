# Setup — first-time PyPI publish via OIDC trusted publisher

This document covers the **one-time manual setup** required before the
first PyPI publish. After it's done, every subsequent release is fully
automated by `.github/workflows/release.yml`: tag → CI builds → CI
publishes via OIDC → CI creates the GitHub Release.

Total time to complete: ~5 minutes (mostly waiting for PyPI page loads).

---

## Why trusted publishing (no API token)

The release workflow uses GitHub's OpenID Connect (OIDC) trusted-publisher
flow. PyPI verifies the workflow's identity via the OIDC token GitHub
issues at runtime — no `PYPI_API_TOKEN` secret is stored anywhere. This
is the supply-chain-hardened pattern recommended by PyPA since 2023.

References:
- https://docs.pypi.org/trusted-publishers/
- https://github.com/pypa/gh-action-pypi-publish#trusted-publishing

---

## Step 1 — claim the project name on PyPI

The package is named `panelforge-figures`. As of v3.14.1 it is **not yet
on PyPI**. To reserve the name + activate trusted publishing in one shot:

### 1a. Sign in to PyPI

1. Open https://pypi.org and click **Login** (top right).
2. If you don't have an account: create one with email
   `renato.socodato@gmail.com` (matches `pyproject.toml`'s author email).
3. Enable 2FA if you haven't (PyPI requires it for any maintainer
   action). Use an authenticator app or a hardware key.

### 1b. Add a **pending publisher**

For projects not yet on PyPI, the trusted-publisher is registered as
"pending" — it activates on first upload.

1. Navigate to **https://pypi.org/manage/account/publishing/**
2. Scroll to the section **"Add a new pending publisher"**.
3. Fill **exactly** these values:

   | Field | Value |
   |---|---|
   | PyPI project name | `panelforge-figures` |
   | Owner | `renatosocodato` |
   | Repository name | `panelforge-figures` |
   | Workflow filename | `release.yml` |
   | Environment name | `pypi` |

4. Click **Add**.

The publisher now appears in your "Pending publishers" list. It will
activate automatically on the first successful upload from
`renatosocodato/panelforge-figures` via `release.yml`'s `pypi`
environment.

---

## Step 2 — register the TestPyPI pending publisher

TestPyPI receives pre-release builds (anything with `-rc`/`-beta`/`-alpha`
in the version). Even though v3.14.1 is a stable release, we register
TestPyPI now so future pre-releases work without revisiting the manual
setup.

1. Open **https://test.pypi.org** (note: separate account from PyPI).
2. Sign in or create an account (use the same email).
3. Navigate to **https://test.pypi.org/manage/account/publishing/**.
4. Add a pending publisher with the same fields as Step 1b **EXCEPT**:
   - **Environment name**: `testpypi`

---

## Step 3 — create the GitHub Actions environments

GitHub Actions environments are referenced by the workflow
(`environment: name: pypi` and `environment: name: testpypi`). They
don't need to exist on first publish — GitHub auto-creates them — but
creating them explicitly lets you enforce reviewers + protection rules.

For our use case the defaults are fine. To pre-create them:

1. Open https://github.com/renatosocodato/panelforge-figures/settings/environments
2. Click **New environment**, name it `pypi`, click **Configure environment**.
3. Repeat for an environment named `testpypi`.

No further configuration needed unless you want to require
manual approval before each publish (recommended for production: add
yourself as a required reviewer on the `pypi` environment).

---

## Step 4 — trigger the first publish

Once Steps 1–2 are done, ping the maintainer to re-trigger the v3.14.1
publish. The one-command recipe:

```bash
cd /Users/renatosocodato/panelforge-figures   # or wherever you have the repo
git fetch origin --tags --force
git push --delete origin v3.14.1              # remove the stale GitHub Release trigger
gh release delete v3.14.1 --yes               # remove the placeholder GitHub Release
git push origin v3.14.1                       # re-trigger the workflow
```

Within ~3 minutes the workflow will:
1. Build wheel + sdist (already verified locally — passes `twine check`)
2. Validate metadata + smoke-test wheel install
3. Upload to PyPI via OIDC (no token needed)
4. Create the GitHub Release with the new artifacts attached

Watch progress at https://github.com/renatosocodato/panelforge-figures/actions/workflows/release.yml

After it completes, the package appears at:
- https://pypi.org/project/panelforge-figures/

End users install with:
```bash
pip install panelforge-figures
```

---

## If anything goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Workflow fails at `Publish to PyPI` with `403 Forbidden` | Pending publisher fields don't match exactly | Re-check Step 1b — owner casing matters (`renatosocodato` not `RenatoSocodato`); workflow filename must be `release.yml` not `release.yaml` |
| Workflow fails at `Create GitHub Release` with "release already exists" | Stale v3.14.1 release object | `gh release delete v3.14.1 --yes` then re-push the tag |
| Workflow fails at `twine check` | Package metadata regression | Local build already verified — should not happen at v3.14.1, but if it does after a future bump: `python -m build && twine check --strict dist/*` reproduces locally |
| PyPI shows "Project name already in use" | Someone else claimed the name | Pick a new name (`panelforge` is a soft fallback) and update `pyproject.toml` + this doc |

---

## Maintainer notes — ongoing releases

After v3.14.1 publishes successfully, every future release is:

```bash
# bump version in pyproject.toml + __init__.py to (say) 3.14.2
git commit -am "release(v3.14.2): ..."
git tag -a v3.14.2 -m "v3.14.2"
git push origin main v3.14.2
```

The workflow takes it from there. No further PyPI setup is ever needed
for this project (the trusted-publisher is now permanent).
