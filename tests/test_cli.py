"""CLI smoke tests via Click's runner."""

import json

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
