"""CLI smoke tests via Click's runner."""

import json

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main


def test_cli_version():
    r = CliRunner().invoke(main, ["--version"])
    assert r.exit_code == 0
    assert "figures" in r.output


def test_cli_list_themes_contains_defaults():
    r = CliRunner().invoke(main, ["list-themes"])
    assert r.exit_code == 0
    out = r.output.splitlines()
    for t in ("default", "pnas", "cell", "nature", "trends", "horizon"):
        assert t in out


def test_cli_list_recipes_prints_all_registered():
    r = CliRunner().invoke(main, ["list-recipes"])
    assert r.exit_code == 0
    names = r.output.strip().splitlines()
    assert any(n.startswith("sensitivity_analysis.") for n in names)
    assert any(n.startswith("grant_and_conceptual.") for n in names)
    assert any(n.startswith("meta_and_diagnostic.") for n in names)


def test_cli_catalog_json_parses():
    r = CliRunner().invoke(main, ["catalog", "--json"])
    assert r.exit_code == 0
    data = json.loads(r.output)
    assert data["modalities"]
    total = sum(len(m["recipes"]) for m in data["modalities"])
    assert total >= 18


def test_cli_stats_reports_recipes_and_modalities():
    r = CliRunner().invoke(main, ["stats"])
    assert r.exit_code == 0
    assert "recipes" in r.output
    assert "modalities" in r.output


def test_cli_show_recipe_prints_metadata():
    r = CliRunner().invoke(main, ["show-recipe", "sensitivity_analysis.sobol_first_total_pair"])
    assert r.exit_code == 0
    assert "sobol_first_total_pair" in r.output
    assert "question" in r.output


# ─────────────────────────── Wave 1/2/3 --help coverage ──────────────────
#
# Every subcommand's `--help` happy path must exit with code 0.  This is
# the soak test for Click's dispatch surface: a missing/renamed command
# fails this single parametrised case.

_HELP_INVOCATIONS: tuple[tuple[str, ...], ...] = (
    # Wave 1 — recipes_index.json
    ("index", "emit", "--help"),
    ("index", "validate", "--help"),
    # Wave 2 — interactive intake
    ("intake", "--help"),
    # Wave 3 — autonomous flow (profile group + scan + bridge + generate)
    ("profile", "--help"),
    ("profile", "scan", "--help"),
    ("bridge", "--help"),
    ("generate", "--help"),
)


@pytest.mark.parametrize("argv", _HELP_INVOCATIONS, ids=lambda a: " ".join(a))
def test_cli_subcommand_help_exits_clean(argv: tuple[str, ...]) -> None:
    """`figures <subcommand> --help` is the safest happy-path probe."""
    r = CliRunner().invoke(main, list(argv))
    assert r.exit_code == 0, (
        f"`figures {' '.join(argv)}` exited with {r.exit_code}\n"
        f"output:\n{r.output}"
    )
    # `--help` always echoes a usage banner.
    assert "Usage:" in r.output


def test_cli_index_group_help_lists_emit_and_validate() -> None:
    """The `index` group's help should mention both subcommands."""
    r = CliRunner().invoke(main, ["index", "--help"])
    assert r.exit_code == 0, r.output
    assert "emit" in r.output
    assert "validate" in r.output


def test_cli_profile_group_help_lists_scan() -> None:
    """The `profile` group's help should list the `scan` subcommand."""
    r = CliRunner().invoke(main, ["profile", "--help"])
    assert r.exit_code == 0, r.output
    assert "scan" in r.output
