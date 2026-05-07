"""CLI tests for the Sprint 1A statistical-contract audit verbs.

Covers the public surface of `figures audit recipe` and `figures audit
shortlist`, plus the `--skip-audit` flag on `figures generate`. Each
test drives the CLI via Click's :class:`CliRunner` so failures present
the user-visible exit codes and output exactly as a real terminal
session would.

Pairs with `tests/test_render_loop.py` (which exercises the audit
integration at the renderer level) and Build-A's
`tests/test_statistical_audit.py` (which exercises the rule
implementations directly).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner
from pydantic import Field

from panelforge_figures.cli import main
from panelforge_figures.core.contract import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from panelforge_figures.core.statistical_contract import StatisticalContract

# ─────────────────────────── registry hygiene ──────────────────────────


@pytest.fixture(autouse=True)
def _scrub_audit_cli_recipes_after_test():
    """Remove every ``test_audit_cli.*`` registration after each test.

    Without this, the synthetic recipes registered by these tests
    leak into ``_REGISTRY`` and trip
    ``test_cli_index.test_figures_index_validate_passes_on_committed_index``
    (which compares the registry against the committed
    ``recipes_index.json``). Scoping the cleanup to test_audit_cli
    keeps the synthetic entries out of every other test's view.
    """
    yield
    # Lazy import so the registry-state assignment is co-located with
    # the cleanup logic (and the conftest's session-scoped
    # ``ensure_all_imported`` has already run).
    from panelforge_figures.core.contract import _REGISTRY
    stale = [k for k in _REGISTRY if k.startswith("test_audit_cli.")]
    for k in stale:
        del _REGISTRY[k]


# ─────────────────────────── fixtures ──────────────────────────────────


class _AuditCLIContract(RecipeContract):
    """Minimal contract: two numeric vectors so the renderer can succeed."""

    xs: list[float] = Field(..., min_length=1)
    ys: list[float] = Field(..., min_length=1)


def _audit_cli_demo() -> _AuditCLIContract:
    return _AuditCLIContract(xs=[0.0, 1.0, 2.0], ys=[0.0, 1.0, 4.0])


def _register_audit_cli_recipe(
    name: str,
    contract: StatisticalContract,
) -> str:
    """Register a fixture recipe with the given statistical contract.

    Recipe names are unique per call so the registry's duplicate check
    doesn't trip across parametrisations.
    """
    metadata = RecipeMetadata(
        name=name,
        modality="test_audit_cli",
        family=RecipeFamily.scatter_collapse,
        answers_question="audit-cli fixture recipe",
        required_fields=("xs", "ys"),
        statistical_contract=contract,
    )

    @register_recipe(
        metadata=metadata,
        contract=_AuditCLIContract,
        demo_contract=_audit_cli_demo,
    )
    def render(contract_obj: _AuditCLIContract, ax=None, **_):  # noqa: ARG001
        if ax is None:
            import matplotlib.pyplot as plt
            _, ax = plt.subplots()
        ax.scatter(contract_obj.xs, contract_obj.ys)
        return ax

    return f"test_audit_cli.{name}"


@pytest.fixture
def well_powered_csv(tmp_path: Path) -> Path:
    """20-row CSV — enough to satisfy a min_n_per_group=6 contract."""
    p = tmp_path / "well_powered.csv"
    pd.DataFrame({
        "value": list(range(20)),
        "group": ["A"] * 10 + ["B"] * 10,
    }).to_csv(p, index=False)
    return p


@pytest.fixture
def underpowered_csv(tmp_path: Path) -> Path:
    """3-row CSV — guaranteed REFUSE for any min_n_per_group >= 4 contract."""
    p = tmp_path / "underpowered.csv"
    pd.DataFrame({"value": [1.0, 2.0, 3.0]}).to_csv(p, index=False)
    return p


@pytest.fixture
def warn_only_csv(tmp_path: Path) -> Path:
    """Heavy-tailed sample — triggers non_normal_with_parametric_test (warn)."""
    import numpy as np
    rng = np.random.default_rng(seed=42)
    # 100 samples from a heavy-tailed lognormal — KS p << 0.01
    values = rng.lognormal(mean=0.0, sigma=1.5, size=100).tolist()
    p = tmp_path / "warn_only.csv"
    pd.DataFrame({"value": values}).to_csv(p, index=False)
    return p


# ─────────────────────────── help discoverability ──────────────────────


def test_audit_group_help_lists_subcommands() -> None:
    """`figures audit --help` must mention both subcommands."""
    r = CliRunner().invoke(main, ["audit", "--help"])
    assert r.exit_code == 0, r.output
    assert "recipe" in r.output
    assert "shortlist" in r.output


def test_audit_recipe_help_describes_options() -> None:
    """`figures audit recipe --help` should advertise --data and --strict."""
    r = CliRunner().invoke(main, ["audit", "recipe", "--help"])
    assert r.exit_code == 0, r.output
    assert "--data" in r.output
    assert "--strict" in r.output


def test_audit_shortlist_help_describes_options() -> None:
    """`figures audit shortlist --help` should advertise --bindings + --data-dir."""
    r = CliRunner().invoke(main, ["audit", "shortlist", "--help"])
    assert r.exit_code == 0, r.output
    assert "--bindings" in r.output
    assert "--data-dir" in r.output


def test_generate_help_describes_skip_audit() -> None:
    """`figures generate --help` should advertise the --skip-audit flag."""
    r = CliRunner().invoke(main, ["generate", "--help"])
    assert r.exit_code == 0, r.output
    assert "--skip-audit" in r.output


# ─────────────────────────── audit recipe (single) ─────────────────────


def test_audit_recipe_returns_zero_on_pass(well_powered_csv: Path) -> None:
    """A well-powered dataset against a permissive contract → exit 0."""
    full_name = _register_audit_cli_recipe(
        "permissive_pass",
        contract=StatisticalContract(),  # all-permissive
    )
    r = CliRunner().invoke(main, [
        "audit", "recipe", full_name,
        "--data", str(well_powered_csv),
    ])
    # Permissive contract → audit driver still returns "pass" overall.
    assert r.exit_code == 0, r.output
    assert "PASS" in r.output.upper() or "pass" in r.output.lower()


def test_audit_recipe_returns_one_on_refuse(underpowered_csv: Path) -> None:
    """A 3-row dataset against min_n_per_group=6 → exit 1 (refuse)."""
    full_name = _register_audit_cli_recipe(
        "underpowered_refuse",
        contract=StatisticalContract(min_n_per_group=6),
    )
    r = CliRunner().invoke(main, [
        "audit", "recipe", full_name,
        "--data", str(underpowered_csv),
    ])
    assert r.exit_code == 1, r.output
    # Verdict + rule_id should both appear.
    assert "REFUSE" in r.output
    assert "underpowered" in r.output


def test_audit_recipe_strict_treats_warn_as_failure(warn_only_csv: Path) -> None:
    """`--strict` lifts a WARN verdict to exit 1; without it, exit 0."""
    full_name = _register_audit_cli_recipe(
        "warn_strict",
        contract=StatisticalContract(distribution_assumption="approximately_gaussian"),
    )
    # Without --strict: WARN is non-fatal → exit 0.
    r1 = CliRunner().invoke(main, [
        "audit", "recipe", full_name,
        "--data", str(warn_only_csv),
    ])
    assert r1.exit_code == 0, r1.output
    assert "WARN" in r1.output

    # With --strict: same WARN escalates to exit 1.
    r2 = CliRunner().invoke(main, [
        "audit", "recipe", full_name,
        "--data", str(warn_only_csv),
        "--strict",
    ])
    assert r2.exit_code == 1, r2.output
    assert "WARN" in r2.output


def test_audit_recipe_unknown_recipe_errors_cleanly(
    well_powered_csv: Path,
) -> None:
    """An unknown recipe name should surface a Click error (non-zero exit)."""
    r = CliRunner().invoke(main, [
        "audit", "recipe", "no.such_recipe",
        "--data", str(well_powered_csv),
    ])
    assert r.exit_code != 0
    assert (
        "no.such_recipe" in r.output
        or "unknown recipe" in r.output.lower()
    )


# ─────────────────────────── audit shortlist ───────────────────────────


def test_audit_shortlist_against_fixture_profile(
    tmp_path: Path,
    well_powered_csv: Path,
    underpowered_csv: Path,
) -> None:
    """End-to-end: a 2-recipe shortlist with one PASS + one REFUSE → exit 1."""
    pass_name = _register_audit_cli_recipe(
        "shortlist_pass",
        contract=StatisticalContract(),
    )
    refuse_name = _register_audit_cli_recipe(
        "shortlist_refuse",
        contract=StatisticalContract(min_n_per_group=6),
    )

    # Build a minimal data_bridge cache JSON. We use the canonical
    # ``write_bindings_cache`` shape so we exercise the same loader path
    # the real CLI uses.
    from panelforge_figures.manifest.data_bridge import (
        FieldBinding,
        RecipeBinding,
        write_bindings_cache,
    )

    cache_path = tmp_path / "cache.json"
    write_bindings_cache(
        [
            RecipeBinding(
                full_name=pass_name,
                bindings=(
                    FieldBinding(
                        contract_field="xs", field_type="list[float]",
                        is_required=True, data_source=well_powered_csv,
                        column_name="value", pass_used="exact", confidence=1.0,
                    ),
                ),
                fully_bound=True, skipped_reason=None,
            ),
            RecipeBinding(
                full_name=refuse_name,
                bindings=(
                    FieldBinding(
                        contract_field="xs", field_type="list[float]",
                        is_required=True, data_source=underpowered_csv,
                        column_name="value", pass_used="exact", confidence=1.0,
                    ),
                ),
                fully_bound=True, skipped_reason=None,
            ),
        ],
        cache_path=cache_path,
    )

    # Stub profile.json — just needs to exist for the path-existence guard.
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"shortlist_size": 2}), encoding="utf-8")

    r = CliRunner().invoke(main, [
        "audit", "shortlist",
        "--profile", str(profile_path),
        "--bindings", str(cache_path),
        "--data-dir", str(tmp_path),
    ])
    # 1 REFUSE in the shortlist → exit 1.
    assert r.exit_code == 1, r.output
    assert pass_name in r.output
    assert refuse_name in r.output
    assert "REFUSE" in r.output
    assert "PASS" in r.output


def test_audit_shortlist_errors_on_missing_profile(tmp_path: Path) -> None:
    """Missing profile.json is a clean ClickException, not a stack trace."""
    nonexistent = tmp_path / "missing_profile.json"
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({"version": 1, "recipes": []}))

    r = CliRunner().invoke(main, [
        "audit", "shortlist",
        "--profile", str(nonexistent),
        "--bindings", str(cache_path),
        "--data-dir", str(tmp_path),
    ])
    # Click validates exists=True on the option → exit code 2 (UsageError).
    assert r.exit_code != 0
    assert "profile" in r.output.lower() or "does not exist" in r.output.lower()


# ─────────────────────────── --skip-audit flag ─────────────────────────


def test_generate_skip_audit_flag_propagates_to_render_loop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`figures generate --skip-audit` must call render_shortlist with skip_audit=True.

    We monkey-patch ``render_shortlist`` so the test does not depend on
    a real figure output; we only assert that the flag is forwarded
    through the CLI surface to the loop.
    """
    captured: dict[str, object] = {}

    def fake_render_shortlist(*, skip_audit: bool = False, **kwargs):
        captured["skip_audit"] = skip_audit
        # Return a minimally-shaped RenderLog so write_render_report works.
        from panelforge_figures.manifest.render_loop import RenderLog
        return RenderLog(
            project_root=tmp_path,
            n_attempted=0, n_success=0, n_skipped=0, n_failed=0,
            outcomes=(),
            started_at="1970-01-01T00:00:00Z",
            finished_at="1970-01-01T00:00:00Z",
        )

    monkeypatch.setattr(
        "panelforge_figures.manifest.render_shortlist",
        fake_render_shortlist,
    )

    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        json.dumps({"version": 1, "recipes": []}),
        encoding="utf-8",
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    out_dir = tmp_path / "figs"

    r = CliRunner().invoke(main, [
        "generate",
        "--bindings", str(cache_path),
        "--data-dir", str(data_dir),
        "--out-dir", str(out_dir),
        "--skip-audit",
    ])
    assert r.exit_code == 0, r.output
    assert captured.get("skip_audit") is True
    # The "AUDIT SKIPPED" banner should also show up.
    assert "AUDIT SKIPPED" in r.output or "skipped" in r.output.lower()


def test_generate_default_does_not_skip_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default `figures generate` invocation propagates skip_audit=False."""
    captured: dict[str, object] = {}

    def fake_render_shortlist(*, skip_audit: bool = False, **kwargs):
        captured["skip_audit"] = skip_audit
        from panelforge_figures.manifest.render_loop import RenderLog
        return RenderLog(
            project_root=tmp_path,
            n_attempted=0, n_success=0, n_skipped=0, n_failed=0,
            outcomes=(),
            started_at="1970-01-01T00:00:00Z",
            finished_at="1970-01-01T00:00:00Z",
        )

    monkeypatch.setattr(
        "panelforge_figures.manifest.render_shortlist",
        fake_render_shortlist,
    )

    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        json.dumps({"version": 1, "recipes": []}),
        encoding="utf-8",
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_dir = tmp_path / "figs"

    r = CliRunner().invoke(main, [
        "generate",
        "--bindings", str(cache_path),
        "--data-dir", str(data_dir),
        "--out-dir", str(out_dir),
    ])
    assert r.exit_code == 0, r.output
    assert captured.get("skip_audit") is False
