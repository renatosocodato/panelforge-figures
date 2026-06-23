# Setup — mint a Zenodo DOI for panelforge-figures

> **STATUS — v3.14.1 is already minted.** Published to Zenodo on 2026-06-23
> via the REST API.
> - Concept DOI (latest): [`10.5281/zenodo.20811170`](https://doi.org/10.5281/zenodo.20811170)
> - Version DOI (v3.14.1): [`10.5281/zenodo.20811171`](https://doi.org/10.5281/zenodo.20811171)
> - Record: https://zenodo.org/record/20811171
>
> The steps below remain the reference for (a) future releases and (b)
> enabling the automatic GitHub-Release→Zenodo webhook so you don't have to
> use the API path again. Two metadata polish items (ORCID, affiliation) are
> still recommended — see the "Before you publish" section.

This document covers the **one-time manual step** to mint a permanent,
citable Zenodo DOI for a panelforge-figures release. After it's done, every
future GitHub Release is automatically archived + DOI-minted by Zenodo.

The repo already ships the two metadata files Zenodo reads:
- [`.zenodo.json`](.zenodo.json) — controls the archived record's metadata
  (title, creators, description, license, keywords).
- [`CITATION.cff`](CITATION.cff) — GitHub's "Cite this repository" button +
  the slot where the minted DOI gets pasted.

Total time: ~5 minutes in the browser.

---

## Why a Zenodo DOI

A Zenodo DOI is the citable, permanent, indexer-respected form of a software
release. Unlike a GitHub tag (which can be force-pushed or deleted), a Zenodo
archive is immutable and resolvable forever. Reviewers, journals, and citation
indexers (Crossref, DataCite, Google Scholar) treat it as a first-class
research output.

Zenodo mints **two** DOIs per project:
- **Concept DOI** — version-agnostic; always resolves to the latest archived
  release. Put this in `CITATION.cff`.
- **Version DOI** — specific to one release (e.g. v3.14.1). Use this when you
  need to cite an exact version.

---

## Step 1 — link GitHub to Zenodo

1. Go to https://zenodo.org and sign in (or register — you can sign in *with*
   your GitHub account, which also performs the link in one step).
2. Click the **profile menu** (top-right) → **GitHub**
   (equivalently: profile menu → **Linked accounts** → **Connect** next to GitHub).
3. Authorize Zenodo on the GitHub OAuth screen. You'll be returned to Zenodo
   with a green check next to GitHub.

---

## Step 2 — enable the repository

1. On the Zenodo **GitHub** page (profile menu → GitHub), click
   **Sync now** in the header. This pulls your repository list from GitHub.
2. Find **`renatosocodato/panelforge-figures`** in the list.
3. **Toggle the slider to ON** next to it.
4. Refresh the page to confirm it now appears under enabled repositories.

> The toggle only arms the webhook for releases created **from now on**. It
> does **not** retroactively archive releases that already exist (v3.14.1,
> v3.15.0). Step 3 handles archiving the existing v3.14.1.

---

## Step 3 — archive v3.14.1 (the release that predates the toggle)

The git **tag** `v3.14.1` stays untouched. We only re-create the GitHub
**Release** object, which re-fires the Zenodo webhook.

```bash
cd ~/panelforge-figures
git fetch origin --tags

# Re-create the GitHub Release for the existing tag (the tag is NOT deleted).
gh release delete v3.14.1 --yes --cleanup-tag=false
gh release create v3.14.1 \
    --title "v3.14.1 — security-hardened baseline" \
    --notes "Security patch release. See CHANGELOG.md [3.14.1]. Archived to Zenodo for citation."
```

The moment the new Release publishes, Zenodo receives the webhook, downloads
the v3.14.1 source archive, applies `.zenodo.json` metadata, and mints both
the concept DOI and the v3.14.1 version DOI.

> **Alternative (simpler, forward-only):** if you'd rather cite the *latest*
> release instead of v3.14.1, skip the delete/recreate. Just cut your next
> release (e.g. v3.15.1) normally — with the toggle ON, Zenodo archives it
> automatically. Update the version in `CITATION.cff` to match.

---

## Step 4 — collect the DOIs

1. Go to your Zenodo dashboard → **Uploads** (or the GitHub page → click the
   newly created `panelforge-figures` badge).
2. Open the v3.14.1 record. You'll see two DOIs:
   - **"Cite all versions?"** → the **concept DOI** (e.g. `10.5281/zenodo.1234567`)
   - The record's own DOI → the **version DOI** (e.g. `10.5281/zenodo.1234568`)
3. Copy both.

---

## Step 5 — backfill the DOI into the repo

Run this from the repo root, substituting the **concept DOI** number:

```bash
cd ~/panelforge-figures
CONCEPT_DOI="10.5281/zenodo.XXXXXXX"     # <-- paste the concept DOI here

# 1) Activate the identifiers block in CITATION.cff
python3 - "$CONCEPT_DOI" <<'PY'
import sys, pathlib
doi = sys.argv[1]
p = pathlib.Path("CITATION.cff")
text = p.read_text()
text = text.replace(
    '# identifiers:\n'
    '#   - type: doi\n'
    '#     value: "10.5281/zenodo.XXXXXXX"\n'
    '#     description: "Concept DOI — resolves to the latest archived version on Zenodo."',
    'identifiers:\n'
    '  - type: doi\n'
    f'    value: "{doi}"\n'
    '    description: "Concept DOI — resolves to the latest archived version on Zenodo."',
)
p.write_text(text)
print("CITATION.cff updated with concept DOI", doi)
PY

# 2) Replace the placeholder in README.md
sed -i '' "s|10.5281/zenodo.XXXXXXX|${CONCEPT_DOI#10.5281/zenodo.}|; s|doi:10.5281/zenodo.[A-Za-z0-9]*|doi:${CONCEPT_DOI}|" README.md

# 3) Commit
git add CITATION.cff README.md
git commit -m "docs: add minted Zenodo concept DOI ${CONCEPT_DOI}"
git push origin main
```

(Optionally also add a Zenodo DOI badge to the top of README:
`[![DOI](https://zenodo.org/badge/DOI/<concept-doi>.svg)](https://doi.org/<concept-doi>)`)

---

## The resulting citation

After Step 5, the canonical citable form is:

> Socodato, R. *panelforge-figures* (v3.14.1). Zenodo (2026).
> doi:10.5281/zenodo.XXXXXXX

BibTeX:

```bibtex
@software{socodato_panelforge_figures_2026,
  author    = {Socodato, Renato},
  title     = {panelforge-figures},
  version   = {3.14.1},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.XXXXXXX},
  url       = {https://doi.org/10.5281/zenodo.XXXXXXX}
}
```

---

## Before you publish — two TODOs in the metadata

1. **ORCID** — `CITATION.cff` and `.zenodo.json` currently omit your ORCID iD
   (none was found in the repo, and a fabricated one would mis-resolve). Add it:
   - In `CITATION.cff`: uncomment the `orcid:` line under your author block and
     paste your full `https://orcid.org/XXXX-XXXX-XXXX-XXXX` URL.
   - In `.zenodo.json`: add `"orcid": "XXXX-XXXX-XXXX-XXXX"` (no URL prefix) to
     your `creators[0]` object.
   If you don't have an ORCID, create one free at https://orcid.org/register —
   it's the standard persistent researcher identifier and indexers use it to
   disambiguate authorship.

2. **Affiliation** (optional but recommended) — add
   `"affiliation": "<your institution>"` to `creators[0]` in `.zenodo.json` and
   an `affiliation:` line under the author in `CITATION.cff`.

---

## Maintainer notes — ongoing releases

After Step 2's toggle is ON, every future GitHub Release is archived
automatically — no further Zenodo setup is ever needed. The concept DOI in
`CITATION.cff` keeps resolving to the latest; bump the `version:` and
`date-released:` fields in `CITATION.cff` as part of each release commit so the
"Cite this repository" metadata stays current.
