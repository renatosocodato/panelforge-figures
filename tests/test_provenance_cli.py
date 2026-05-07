"""CLI tests for the Sprint 1B provenance verbs.

Covers the public surface of `figures provenance {show,verify,bundle,diff}`
and the `--no-provenance` flag on `figures generate`. Each test drives
the CLI via Click's :class:`CliRunner` so failures present the
user-visible exit codes and output exactly as a real terminal session
would.

Pairs with Build-A's `tests/test_provenance.py` (which exercises the
hashing + sidecar writer + verifier directly). To avoid a hard
dependency on Build-A landing first, these tests inject a fake
``panelforge_figures.manifest.provenance`` module via ``sys.modules``
when needed; that surface mirrors the public API documented in
``docs/spec_provenance_chain.md`` §8.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from click.testing import CliRunner

from panelforge_figures.cli import main

# ─────────────────────────── fake provenance module ────────────────────


@dataclass
class _FakeVerificationResult:
    """Mirrors Build-A's ``VerificationResult`` minimal surface."""

    overall: str  # "match" | "drift_data" | "drift_recipe" | "drift_env" | …
    findings: list[str] = field(default_factory=list)


def _install_fake_provenance(
    monkeypatch: pytest.MonkeyPatch,
    *,
    verify_result: _FakeVerificationResult | None = None,
    diff_payload: dict[str, list[str]] | None = None,
    bundle_target: Path | None = None,
) -> types.ModuleType:
    """Inject a fake ``panelforge_figures.manifest.provenance`` module.

    The CLI imports lazily inside each subcommand, so we install the
    module before invoking the runner. The fake honours the public API
    documented in ``docs/spec_provenance_chain.md`` §8.
    """
    fake = types.ModuleType("panelforge_figures.manifest.provenance")

    def verify_provenance(provenance_path: Path):
        if verify_result is not None:
            return verify_result
        return _FakeVerificationResult(overall="match", findings=[])

    def diff_provenance(a_path: Path, b_path: Path):
        if diff_payload is not None:
            return diff_payload
        # Build-A's actual return-shape: per-dimension lists keyed by
        # figure / recipe / data / scorer / environment.
        return {
            "figure": [], "recipe": [], "data": [], "scorer": [],
            "environment": [],
        }

    def bundle_provenance(figure_path: Path, *, out_path: Path | None = None):
        if bundle_target is not None:
            bundle_target.write_bytes(b"fake-tarball")
            return bundle_target
        target = (
            out_path
            if out_path is not None
            else figure_path.with_suffix(figure_path.suffix + ".tar.gz")
        )
        target.write_bytes(b"fake-tarball")
        return target

    fake.verify_provenance = verify_provenance  # type: ignore[attr-defined]
    fake.diff_provenance = diff_provenance  # type: ignore[attr-defined]
    fake.bundle_provenance = bundle_provenance  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules, "panelforge_figures.manifest.provenance", fake,
    )
    return fake


# ─────────────────────────── canonical sidecar fixtures ────────────────


_CANONICAL_SIDECAR: dict = {
    "schema_version": "1.0.0",
    "figure_path": "figures/figure_03_panel_A.pdf",
    "figure_sha256": "f7a9c32be1d4e7b9aa31f80c8b1f2c9aaaaabbbbccccddddeeeeffff00001111",
    "rendered_at": "2026-05-04T15:32:00Z",
    "recipe": {
        "full_name": (
            "actin_microtubule_morphometry."
            "compartment_paired_delta_scatter"
        ),
        "module_sha": "8b1f2c9addddeeeeffff000011112222",
        "panelforge_version": "2.0.0",
        "panelforge_git_commit": "aa31f80c",
        "module_path": (
            "src/panelforge_figures/recipes/"
            "actin_microtubule_morphometry/"
            "compartment_paired_delta_scatter.py"
        ),
    },
    "data": {
        "sources": [
            {
                "path": "data/effect_sizes.csv",
                "sha256": "11d4e7b9aa31f80c8b1f2c9addddeeeeffff000011112222",
                "n_rows": 30,
                "format": "csv",
                "size_bytes": 4096,
            },
        ],
        "column_mapping": {"feature": "feature_name", "d": "cohen_d"},
    },
    "scorer": {
        "version": "1.0.0",
        "weights": {"factorial": 0.30, "anchor": 0.20},
        "score": 0.565,
        "tied_with": [],
        "profile": {"manuscript_anchor": "DISC1"},
    },
    "audit": {"overall": "pass", "rules_passed": ["n_at_least_10"]},
    "rendering_environment": {
        "python_version": "3.12.4",
        "matplotlib_version": "3.9.0",
        "numpy_version": "2.0.1",
        "panelforge_version": "2.0.0",
        "platform": "darwin",
        "rng_seed": 42,
        "deterministic": True,
    },
}


def _make_figure_with_sidecar(
    tmp_path: Path,
    *,
    name: str = "fig_a.pdf",
    sidecar: dict | None = None,
) -> Path:
    """Create a fake PDF + matching ``.provenance.json`` sidecar."""
    pdf_path = tmp_path / name
    pdf_path.write_bytes(b"%PDF-1.4\nfake content for tests\n")
    payload = sidecar if sidecar is not None else _CANONICAL_SIDECAR
    sidecar_path = pdf_path.with_suffix(pdf_path.suffix + ".provenance.json")
    sidecar_path.write_text(json.dumps(payload), encoding="utf-8")
    return pdf_path


# ─────────────────────────── help discoverability ──────────────────────


def test_provenance_group_help_lists_subcommands() -> None:
    """`figures provenance --help` lists all four subcommands."""
    r = CliRunner().invoke(main, ["provenance", "--help"])
    assert r.exit_code == 0, r.output
    for sub in ("show", "verify", "bundle", "diff"):
        assert sub in r.output, f"missing '{sub}' in help: {r.output}"


def test_provenance_verify_help_describes_argument() -> None:
    """`figures provenance verify --help` advertises its FIGURE_PATH arg."""
    r = CliRunner().invoke(main, ["provenance", "verify", "--help"])
    assert r.exit_code == 0, r.output
    assert "FIGURE_PATH" in r.output.upper() or "figure" in r.output.lower()


def test_provenance_bundle_help_describes_out_option() -> None:
    """`figures provenance bundle --help` advertises the --out option."""
    r = CliRunner().invoke(main, ["provenance", "bundle", "--help"])
    assert r.exit_code == 0, r.output
    assert "--out" in r.output


def test_generate_help_describes_no_provenance() -> None:
    """`figures generate --help` advertises the --no-provenance flag."""
    r = CliRunner().invoke(main, ["generate", "--help"])
    assert r.exit_code == 0, r.output
    assert "--no-provenance" in r.output


# ─────────────────────────── show ──────────────────────────────────────


def test_provenance_show_prints_expected_fields(tmp_path: Path) -> None:
    """`provenance show <pdf>` prints recipe, hash, env summary."""
    pdf = _make_figure_with_sidecar(tmp_path)
    r = CliRunner().invoke(main, ["provenance", "show", str(pdf)])
    assert r.exit_code == 0, r.output
    # Section header + key fields.
    assert pdf.name in r.output
    assert "1.0.0" in r.output  # schema_version
    assert "compartment_paired_delta_scatter" in r.output
    assert "f7a9c32b" in r.output  # truncated figure sha
    assert "effect_sizes.csv" in r.output
    assert "matplotlib" in r.output


def test_provenance_show_missing_sidecar_exits_one(tmp_path: Path) -> None:
    """Missing sidecar produces a clear error + exit 1."""
    pdf = tmp_path / "naked.pdf"
    pdf.write_bytes(b"%PDF-1.4\nno sidecar here\n")
    r = CliRunner().invoke(main, ["provenance", "show", str(pdf)])
    assert r.exit_code == 1, r.output
    assert "not found" in r.output
    # Remediation hint should mention figures generate.
    assert "figures generate" in r.output


# ─────────────────────────── verify ────────────────────────────────────


def test_provenance_verify_passes_on_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hash match → exit 0 + ✓ verified message."""
    _install_fake_provenance(
        monkeypatch,
        verify_result=_FakeVerificationResult(
            overall="match", findings=[],
        ),
    )
    pdf = _make_figure_with_sidecar(tmp_path)
    r = CliRunner().invoke(main, ["provenance", "verify", str(pdf)])
    assert r.exit_code == 0, r.output
    assert "verified" in r.output.lower()
    assert "bit-identical" in r.output.lower()


def test_provenance_verify_flags_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drift detected → exit 1 + drift class + finding lines."""
    _install_fake_provenance(
        monkeypatch,
        verify_result=_FakeVerificationResult(
            overall="drift_data",
            findings=[
                "data/effect_sizes.csv: sha256 11d4e7b9 → 22e5f8c0",
                "n_rows 30 → 31",
            ],
        ),
    )
    pdf = _make_figure_with_sidecar(tmp_path)
    r = CliRunner().invoke(main, ["provenance", "verify", str(pdf)])
    assert r.exit_code == 1, r.output
    assert "drift" in r.output.lower()
    assert "drift_data" in r.output
    assert "effect_sizes.csv" in r.output
    assert "n_rows 30" in r.output


def test_provenance_verify_missing_sidecar_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing sidecar at verify time exits 1 with a clear error."""
    _install_fake_provenance(monkeypatch)
    pdf = tmp_path / "naked.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    r = CliRunner().invoke(main, ["provenance", "verify", str(pdf)])
    assert r.exit_code == 1, r.output
    assert "not found" in r.output


# ─────────────────────────── bundle ────────────────────────────────────


def test_provenance_bundle_writes_tarball(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`provenance bundle <pdf>` writes a tar.gz at the default location."""
    target = tmp_path / "fig_a.pdf.provenance.tar.gz"
    _install_fake_provenance(monkeypatch, bundle_target=target)
    pdf = _make_figure_with_sidecar(tmp_path)
    r = CliRunner().invoke(main, ["provenance", "bundle", str(pdf)])
    assert r.exit_code == 0, r.output
    assert target.is_file(), "bundle target was not written"
    assert "wrote" in r.output.lower()
    assert "KB" in r.output  # human-readable size


def test_provenance_bundle_honours_out_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--out` redirects the tarball to the specified path."""
    custom = tmp_path / "supp_figure_03A.tar.gz"
    _install_fake_provenance(monkeypatch, bundle_target=custom)
    pdf = _make_figure_with_sidecar(tmp_path)
    r = CliRunner().invoke(main, [
        "provenance", "bundle", str(pdf), "--out", str(custom),
    ])
    assert r.exit_code == 0, r.output
    assert custom.is_file()
    assert str(custom) in r.output or custom.name in r.output


# ─────────────────────────── diff ──────────────────────────────────────


def test_provenance_diff_reports_no_difference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identical sidecars → exit 0 + 'no differences' message."""
    _install_fake_provenance(
        monkeypatch,
        diff_payload={
            "figure": [], "recipe": [], "data": [], "scorer": [],
            "environment": [],
        },
    )
    a = _make_figure_with_sidecar(tmp_path, name="fig_a.pdf")
    b = _make_figure_with_sidecar(tmp_path, name="fig_b.pdf")
    r = CliRunner().invoke(
        main, ["provenance", "diff", str(a), str(b)],
    )
    assert r.exit_code == 0, r.output
    assert "no differences" in r.output.lower()


def test_provenance_diff_lists_changes_per_dimension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diff payload with entries → exit 0 + per-dimension change lines."""
    _install_fake_provenance(
        monkeypatch,
        diff_payload={
            "figure": [],
            "recipe": [],
            "data": ["effect_sizes.csv: 11d4e7b9 → 22e5f8c0"],
            "scorer": ["weights.anchor: 0.20 → 0.25"],
            "environment": ["matplotlib_version: 3.9.0 → 3.10.1"],
        },
    )
    a = _make_figure_with_sidecar(tmp_path, name="fig_a.pdf")
    b = _make_figure_with_sidecar(tmp_path, name="fig_b.pdf")
    r = CliRunner().invoke(
        main, ["provenance", "diff", str(a), str(b)],
    )
    # Diff is reportorial, not error-bearing — exit 0 by design.
    assert r.exit_code == 0, r.output
    assert "Differences" in r.output
    assert "data" in r.output
    assert "effect_sizes.csv" in r.output
    assert "scorer" in r.output
    assert "weights.anchor: 0.20 → 0.25" in r.output
    assert "environment" in r.output


def test_provenance_diff_missing_sidecar_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If either sidecar is missing → exit 1 with a clear error."""
    _install_fake_provenance(monkeypatch)
    a = _make_figure_with_sidecar(tmp_path, name="fig_a.pdf")
    b = tmp_path / "fig_b.pdf"
    b.write_bytes(b"%PDF-1.4\n")  # no sidecar for fig_b
    r = CliRunner().invoke(
        main, ["provenance", "diff", str(a), str(b)],
    )
    assert r.exit_code == 1, r.output
    assert "not found" in r.output
