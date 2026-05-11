"""Sanity-check the E18 CI action assets parse + reference well-formed inputs.

Covers:

1. action.yml parses as YAML.
2. action.yml has all advertised inputs.
3. action.yml has all advertised outputs.
4. action.yml branding/icon/color is valid.
5. workflow template parses as YAML.
6. workflow template references the action by its repo path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ACTION_YML = REPO_ROOT / "action.yml"
WORKFLOW_TEMPLATE = REPO_ROOT / ".github" / "workflows" / "panelforge-ci.yml.template"


# --------------------------------------------------------------------------- #
# 1. action.yml exists and parses                                              #
# --------------------------------------------------------------------------- #


def test_action_yml_exists() -> None:
    assert ACTION_YML.is_file(), f"{ACTION_YML} not found"


def test_action_yml_parses() -> None:
    """action.yml is well-formed YAML."""
    data = yaml.safe_load(ACTION_YML.read_text())
    assert isinstance(data, dict)
    assert data.get("name") == "panelforge-figures audit"
    assert isinstance(data.get("description"), str)
    assert data.get("description")


# --------------------------------------------------------------------------- #
# 2. all advertised inputs are present                                         #
# --------------------------------------------------------------------------- #


EXPECTED_INPUTS = (
    "project-root",
    "manuscript",
    "figures-dir",
    "plan-path",
    "venue",
    "steps",
    "fail-on-warning",
    "panelforge-version",
    "python-version",
    "comment-on-pr",
)


@pytest.mark.parametrize("name", EXPECTED_INPUTS)
def test_action_yml_input_exists(name: str) -> None:
    data = yaml.safe_load(ACTION_YML.read_text())
    inputs = data.get("inputs", {})
    assert isinstance(inputs, dict)
    assert name in inputs, f"missing input: {name}"
    spec = inputs[name]
    assert isinstance(spec, dict)
    assert "description" in spec
    assert isinstance(spec["description"], str)


# --------------------------------------------------------------------------- #
# 3. all advertised outputs are present                                        #
# --------------------------------------------------------------------------- #


EXPECTED_OUTPUTS = ("status", "n-errors", "n-warnings", "report-path")


@pytest.mark.parametrize("name", EXPECTED_OUTPUTS)
def test_action_yml_output_exists(name: str) -> None:
    data = yaml.safe_load(ACTION_YML.read_text())
    outputs = data.get("outputs", {})
    assert isinstance(outputs, dict)
    assert name in outputs, f"missing output: {name}"
    spec = outputs[name]
    assert isinstance(spec, dict)
    assert "description" in spec


# --------------------------------------------------------------------------- #
# 4. branding/icon/color                                                       #
# --------------------------------------------------------------------------- #


# GitHub-accepted branding colors (per https://docs.github.com/en/actions/...
# /metadata-syntax-for-github-actions#brandingcolor)
_VALID_COLORS = {
    "white", "yellow", "blue", "green", "orange", "red", "purple", "gray-dark",
}


def test_action_yml_branding_present() -> None:
    data = yaml.safe_load(ACTION_YML.read_text())
    branding = data.get("branding")
    assert isinstance(branding, dict)
    assert "icon" in branding
    assert "color" in branding
    assert branding["color"] in _VALID_COLORS, (
        f"branding color must be one of {_VALID_COLORS!r}, got {branding['color']!r}"
    )
    # Feather icon names are 3-30 chars of lowercase + dash; not a hard rule
    # but we sanity-check the type at least.
    assert isinstance(branding["icon"], str)
    assert branding["icon"]


# --------------------------------------------------------------------------- #
# 5. action.yml is a composite action with required steps                      #
# --------------------------------------------------------------------------- #


def test_action_yml_runs_is_composite() -> None:
    data = yaml.safe_load(ACTION_YML.read_text())
    runs = data.get("runs", {})
    assert runs.get("using") == "composite"
    steps = runs.get("steps")
    assert isinstance(steps, list)
    assert len(steps) >= 3
    names = [s.get("name") for s in steps if isinstance(s, dict)]
    assert "setup-python" in names
    assert "install-panelforge" in names
    assert "run-audit" in names


# --------------------------------------------------------------------------- #
# 6. workflow template                                                         #
# --------------------------------------------------------------------------- #


def test_workflow_template_exists() -> None:
    assert WORKFLOW_TEMPLATE.is_file(), f"{WORKFLOW_TEMPLATE} not found"


def test_workflow_template_parses() -> None:
    """Workflow template is well-formed YAML."""
    data = yaml.safe_load(WORKFLOW_TEMPLATE.read_text())
    assert isinstance(data, dict)
    assert data.get("name") == "panelforge-figures audit"
    # ``on`` is reserved in YAML 1.1 (parsed to bool ``True`` by PyYAML);
    # accept either key.
    on = data.get("on") if "on" in data else data.get(True)
    assert isinstance(on, dict)
    assert "pull_request" in on or "push" in on


def test_workflow_template_references_action() -> None:
    """The workflow references the action via the repo-rooted path."""
    text = WORKFLOW_TEMPLATE.read_text()
    assert "renatosocodato/panelforge-figures@v3.13.0" in text


def test_workflow_template_has_pull_request_permissions() -> None:
    """The PR-comment step needs pull-requests: write."""
    data = yaml.safe_load(WORKFLOW_TEMPLATE.read_text())
    audit_job = data["jobs"]["audit"]
    perms = audit_job.get("permissions", {})
    assert perms.get("pull-requests") == "write"


# --------------------------------------------------------------------------- #
# 7. cross-check: action.yml default 'steps' matches CLI default               #
# --------------------------------------------------------------------------- #


def test_action_yml_default_steps_match_cli_default() -> None:
    """The 'steps' input default mirrors the CLI's recommended chain."""
    data = yaml.safe_load(ACTION_YML.read_text())
    steps_input = data["inputs"]["steps"]
    default = steps_input["default"]
    parts = [s.strip() for s in default.split(",")]
    # Should be exactly the four-step default chain advertised in the runner.
    assert parts == ["scout", "verify-claims", "lint-xrefs", "checklist-arrive"]


def test_action_yml_version_matches_repo_version() -> None:
    """The workflow template's pinned version matches the package version."""
    from panelforge_figures import __version__

    text = WORKFLOW_TEMPLATE.read_text()
    assert f"v{__version__}" in text
    assert f"panelforge-version: {__version__}" in text
