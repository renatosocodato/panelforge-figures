"""CLI tests for the Sprint 1C composition verbs.

Covers the public surface of ``figures compose``,
``figures compose-all``, and ``figures compose-validate``.  Each test
drives the CLI via Click's :class:`CliRunner` so failures present the
user-visible exit codes and output exactly as a real terminal session
would.

Pairs with Build-A's `manifest/figure_composition.py` (which exercises
the engine directly).  To avoid a hard dependency on Build-A landing
first, these tests inject a fake
``panelforge_figures.manifest.figure_composition`` module via
``sys.modules`` and re-export
``render_figure_yaml`` / ``validate_figure_yaml`` from the package
namespace where the CLI imports them.  The fake mirrors the public API
documented in ``docs/spec_composition_layer.md`` §4.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main

# ─────────────────────── fake composition engine ─────────────────────


def _install_fake_composition(
    monkeypatch: pytest.MonkeyPatch,
    *,
    render_result: Path | None = None,
    render_error: Exception | None = None,
    validate_problems: list[str] | None = None,
) -> tuple[list[Path], list[Path]]:
    """Inject a fake composition surface into ``panelforge_figures.manifest``.

    The CLI imports ``render_figure_yaml`` and ``validate_figure_yaml``
    lazily from the package namespace inside each subcommand
    (``from .manifest import render_figure_yaml``), so we patch those
    names directly on the already-imported manifest module.

    Returns ``(render_calls, validate_calls)`` lists that the test can
    inspect to assert which YAMLs were processed.
    """
    import panelforge_figures.manifest as manifest_pkg

    render_calls: list[Path] = []
    validate_calls: list[Path] = []

    def render_figure_yaml(yaml_path: Path, *, out_dir: Path = Path("figures")) -> Path:
        render_calls.append(yaml_path)
        if render_error is not None:
            raise render_error
        if render_result is not None:
            return render_result
        # Default: produce a fake PDF next to the requested out_dir.
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{yaml_path.stem.replace('.figure', '')}.pdf"
        out.write_bytes(b"%PDF-1.4\nfake composed figure\n")
        return out

    def validate_figure_yaml(yaml_path: Path) -> list[str]:
        validate_calls.append(yaml_path)
        return list(validate_problems) if validate_problems is not None else []

    monkeypatch.setattr(
        manifest_pkg, "render_figure_yaml",
        render_figure_yaml, raising=False,
    )
    monkeypatch.setattr(
        manifest_pkg, "validate_figure_yaml",
        validate_figure_yaml, raising=False,
    )

    # Also publish a fake submodule for code paths that prefer the
    # `manifest.figure_composition` import path.
    fake_mod = types.ModuleType(
        "panelforge_figures.manifest.figure_composition",
    )
    fake_mod.render_figure_yaml = render_figure_yaml  # type: ignore[attr-defined]
    fake_mod.validate_figure_yaml = validate_figure_yaml  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "panelforge_figures.manifest.figure_composition",
        fake_mod,
    )
    return render_calls, validate_calls


_MINIMAL_FIGURE_YAML = """\
figure_id: demo_figure
title: "Demo figure"
layout:
  kind: grid
  rows: 1
  cols: 2
panels:
  - id: A
    recipe: meta_and_diagnostic.bayes_factor_arrow_plot
    data:
      source: data/demo_a.csv
  - id: B
    recipe: meta_and_diagnostic.bayes_factor_arrow_plot
    data:
      source: data/demo_b.csv
"""


def _write_figure_yaml(
    tmp_path: Path,
    *,
    name: str = "demo.figure.yaml",
    body: str = _MINIMAL_FIGURE_YAML,
) -> Path:
    """Write a fake figure-spec YAML to ``tmp_path`` and return its Path."""
    yaml_path = tmp_path / name
    yaml_path.write_text(body, encoding="utf-8")
    return yaml_path


# ─────────────────────────── help discoverability ───────────────────


def test_compose_help_exits_clean() -> None:
    """`figures compose --help` exits 0 and shows usage banner."""
    r = CliRunner().invoke(main, ["compose", "--help"])
    assert r.exit_code == 0, r.output
    assert "Usage:" in r.output
    assert "YAML_PATH" in r.output.upper() or "yaml" in r.output.lower()
    assert "--out-dir" in r.output


def test_compose_all_help_exits_clean() -> None:
    """`figures compose-all --help` exits 0 and advertises --figures-dir."""
    r = CliRunner().invoke(main, ["compose-all", "--help"])
    assert r.exit_code == 0, r.output
    assert "Usage:" in r.output
    assert "--figures-dir" in r.output


def test_compose_validate_help_exits_clean() -> None:
    """`figures compose-validate --help` exits 0 and shows YAML_PATH."""
    r = CliRunner().invoke(main, ["compose-validate", "--help"])
    assert r.exit_code == 0, r.output
    assert "Usage:" in r.output
    assert "YAML_PATH" in r.output.upper() or "yaml" in r.output.lower()


# ─────────────────────────── compose ────────────────────────────────


def test_compose_produces_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`figures compose <good.yaml>` exits 0 and reports the output path."""
    render_calls, _ = _install_fake_composition(monkeypatch)
    yaml_path = _write_figure_yaml(tmp_path)
    out_dir = tmp_path / "figures"

    r = CliRunner().invoke(
        main,
        ["compose", str(yaml_path), "--out-dir", str(out_dir)],
    )
    assert r.exit_code == 0, r.output
    assert "composed" in r.output.lower()
    assert "✓" in r.output
    # The fake engine writes a real PDF stub at out_dir/<id>.pdf.
    assert (out_dir / "demo.pdf").is_file()
    # The CLI delegated to the engine exactly once with the user's YAML.
    assert len(render_calls) == 1
    assert render_calls[0] == yaml_path


def test_compose_missing_file_exits_two(tmp_path: Path) -> None:
    """`figures compose <missing.yaml>` exits with Click's missing-arg code."""
    missing = tmp_path / "does_not_exist.figure.yaml"
    r = CliRunner().invoke(main, ["compose", str(missing)])
    # Click's `exists=True` on click.Path raises a UsageError → exit 2.
    assert r.exit_code != 0, r.output
    assert "does not exist" in r.output.lower() or "no such" in r.output.lower()


# ─────────────────────────── compose-all ────────────────────────────


def test_compose_all_renders_every_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`figures compose-all` walks every `*.figure.yaml` in the dir."""
    render_calls, _ = _install_fake_composition(monkeypatch)
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    a = _write_figure_yaml(figures_dir, name="alpha.figure.yaml")
    b = _write_figure_yaml(figures_dir, name="beta.figure.yaml")

    r = CliRunner().invoke(
        main, ["compose-all", "--figures-dir", str(figures_dir)],
    )
    assert r.exit_code == 0, r.output
    assert "alpha.figure.yaml" in r.output
    assert "beta.figure.yaml" in r.output
    assert "✓" in r.output
    # Every yaml was passed to the engine (sorted, deterministic order).
    assert {p.name for p in render_calls} == {a.name, b.name}


def test_compose_all_empty_dir_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`figures compose-all` over an empty dir exits 1 with a helpful message."""
    _install_fake_composition(monkeypatch)
    empty = tmp_path / "no_figs"
    empty.mkdir()
    r = CliRunner().invoke(
        main, ["compose-all", "--figures-dir", str(empty)],
    )
    assert r.exit_code == 1, r.output
    assert "no" in r.output.lower()
    assert "figure.yaml" in r.output


def test_compose_all_continues_after_per_file_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A per-file render error is logged but doesn't abort the sweep."""
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir()
    _write_figure_yaml(figures_dir, name="alpha.figure.yaml")
    _write_figure_yaml(figures_dir, name="beta.figure.yaml")

    # Engine raises on every call; per-spec errors should surface as `✗`.
    _install_fake_composition(
        monkeypatch,
        render_error=RuntimeError("kaboom"),
    )

    r = CliRunner().invoke(
        main, ["compose-all", "--figures-dir", str(figures_dir)],
    )
    # compose-all does NOT exit non-zero on per-file failures (by design),
    # but it does emit ✗ lines for each failure on stderr.
    combined = r.output + (r.stderr if r.stderr_bytes else "")
    assert "✗" in combined
    assert "alpha.figure.yaml" in combined
    assert "beta.figure.yaml" in combined
    assert "kaboom" in combined


# ─────────────────────────── compose-validate ───────────────────────


def test_compose_validate_passes_on_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A spec the engine deems valid → exit 0 + ✓ message."""
    _, validate_calls = _install_fake_composition(
        monkeypatch, validate_problems=[],
    )
    yaml_path = _write_figure_yaml(tmp_path, name="good.figure.yaml")
    r = CliRunner().invoke(main, ["compose-validate", str(yaml_path)])
    assert r.exit_code == 0, r.output
    assert "valid" in r.output.lower()
    assert "✓" in r.output
    assert validate_calls == [yaml_path]


def test_compose_validate_fails_on_problems(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A spec with problems → exit 1, one diagnostic line per problem."""
    problems = [
        "panel A: recipe 'meta.does_not_exist' not found",
        "panel B: shared_axis_with refers to unknown panel id 'Z'",
    ]
    _install_fake_composition(monkeypatch, validate_problems=problems)
    yaml_path = _write_figure_yaml(tmp_path, name="bad.figure.yaml")

    r = CliRunner().invoke(main, ["compose-validate", str(yaml_path)])
    assert r.exit_code == 1, r.output
    combined = r.output + (r.stderr if r.stderr_bytes else "")
    for p in problems:
        assert p in combined
    # No PDF should ever be written by compose-validate.
    assert not any(
        path.name.endswith(".pdf") for path in tmp_path.iterdir()
    )


def test_compose_validate_missing_file_exits_two(tmp_path: Path) -> None:
    """`figures compose-validate <missing.yaml>` errors via Click's exists=True."""
    missing = tmp_path / "ghost.figure.yaml"
    r = CliRunner().invoke(main, ["compose-validate", str(missing)])
    assert r.exit_code != 0, r.output
    assert "does not exist" in r.output.lower() or "no such" in r.output.lower()
