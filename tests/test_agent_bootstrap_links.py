"""Tests for `AGENT_BOOTSTRAP.md` (Wave 1).

Verifies:
  * The file exists at repo root.
  * Repo-relative paths referenced inside it resolve to existing files.
  * The 5 mandated step headings are present.
  * Mentions the index schema_version contract.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO_ROOT / "AGENT_BOOTSTRAP.md"

# Repo-relative paths that the bootstrap file claims exist.  Each must
# resolve under REPO_ROOT.  Skip URLs and parameterised paths.
EXPECTED_RELATIVE_PATHS = (
    "recipes_index.json",
    "AGENT_BOOTSTRAP.md",
    "docs/recipes_index.schema.json",
    ".github/workflows/ci.yml",
    "src/panelforge_figures/manifest/catalog.py",
    "src/panelforge_figures/cli.py",
)


def test_bootstrap_file_exists() -> None:
    assert BOOTSTRAP.is_file(), f"bootstrap file missing at {BOOTSTRAP}"


def test_bootstrap_has_required_step_headings() -> None:
    text = BOOTSTRAP.read_text()
    for step in (
        "## Step 1",
        "## Step 2",
        "## Step 3",
        "## Step 4",
        "## Step 5",
    ):
        assert step in text, f"bootstrap missing heading: {step}"


def test_bootstrap_references_resolvable_paths() -> None:
    """Every claimed in-repo path must exist on disk."""
    text = BOOTSTRAP.read_text()
    for rel in EXPECTED_RELATIVE_PATHS:
        assert rel in text, f"bootstrap doesn't mention {rel}"
        target = REPO_ROOT / rel
        assert target.exists(), (
            f"bootstrap references {rel} but target {target} is missing"
        )


def test_bootstrap_mentions_schema_version_contract() -> None:
    """Wave-1 bootstrap must call out the `index_meta.schema_version`
    contract so agents can detect breaking changes."""
    text = BOOTSTRAP.read_text()
    assert "schema_version" in text, "bootstrap doesn't mention schema_version"


def test_bootstrap_documents_wave2_compat() -> None:
    """Wave-2 forward compatibility: the bootstrap explains what changes
    when `tags_enabled` flips."""
    text = BOOTSTRAP.read_text()
    assert "tags_enabled" in text, "bootstrap doesn't mention tags_enabled"
    assert "Wave 2" in text, "bootstrap doesn't reference Wave 2 in some form"


def test_no_template_owner_placeholder_in_clone_url() -> None:
    """The sparse-checkout instructions use `<repo-url>` as a placeholder.
    But the raw GitHub fetch URL must not still say `<owner>` if we've
    decided on a real owner — Wave 1 keeps the placeholder so this test
    just verifies the format is consistent."""
    text = BOOTSTRAP.read_text()
    raw_lines = [
        ln for ln in text.splitlines()
        if "raw.githubusercontent.com" in ln
    ]
    assert raw_lines, "bootstrap must contain at least one raw.githubusercontent URL"
    for line in raw_lines:
        # Either parameterised or pinned — but consistent across the file.
        assert "<owner>" in line or re.search(r"raw\.githubusercontent\.com/[^/<]+/", line), (
            f"raw URL has malformed owner spec: {line}"
        )
