"""Tests for the per-recipe render loop and RENDER_REPORT.md writer.

Wave 3 — covers all behaviours documented in
``CLAUDE_CODE_AUTONOMOUS.md`` §6:

* status accounting on a 3-recipe scenario,
* report file structure,
* per-recipe failures do NOT halt the loop,
* environmental failures DO halt the loop,
* both PDF + PNG produced for each successful render,
* traceback excerpting,
* empty-shortlist degenerate case.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from pydantic import Field

from panelforge_figures.core.contract import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    register_recipe,
)
from panelforge_figures.manifest.render_loop import (
    EnvironmentalFailure,
    RenderBinding,
    RenderDataFile,
    RenderLog,
    _excerpt_traceback,
    render_shortlist,
    write_render_report,
)

# ─────────────────────────── test fixtures ──────────────────────────────


@pytest.fixture(autouse=True)
def _scrub_render_loop_recipes_after_test():
    """Remove every ``test_render_loop.*`` registration after each test.

    ``_make_test_recipe`` injects synthetic recipes into the global
    ``_REGISTRY``; without this cleanup they leak and inflate
    ``list_recipes()``, tripping the index-drift / count assertions in
    ``test_cli_index`` and ``figures index validate`` depending on test
    ordering. Scoping the cleanup to this module's prefix keeps the
    synthetic entries out of every other test's view.
    """
    yield
    from panelforge_figures.core.contract import _REGISTRY
    stale = [k for k in _REGISTRY if k.startswith("test_render_loop.")]
    for k in stale:
        del _REGISTRY[k]


class _FixtureContract(RecipeContract):
    """Minimal contract for synthetic test recipes."""

    xs: list[float] = Field(..., min_length=1)
    ys: list[float] = Field(..., min_length=1)


def _fixture_demo() -> _FixtureContract:
    return _FixtureContract(xs=[0.0, 1.0, 2.0], ys=[0.0, 1.0, 4.0])


def _make_test_recipe(
    name: str,
    *,
    raise_during_render: type[BaseException] | None = None,
):
    """Register a synthetic recipe under modality ``test_render_loop``.

    The function is idempotent thanks to the ``_REGISTRY`` duplicate
    check — we therefore always use a unique ``name``.
    """

    metadata = RecipeMetadata(
        name=name,
        modality="test_render_loop",
        family=RecipeFamily.scatter_collapse,
        answers_question="test recipe",
        required_fields=("xs", "ys"),
    )

    @register_recipe(
        metadata=metadata,
        contract=_FixtureContract,
        demo_contract=_fixture_demo,
    )
    def render(contract: _FixtureContract, ax=None, **_):
        if raise_during_render is not None:
            raise raise_during_render(f"intentional {name} failure")
        if ax is None:
            import matplotlib.pyplot as plt

            _, ax = plt.subplots()
        ax.scatter(contract.xs, contract.ys)
        return ax

    return f"test_render_loop.{name}"


@pytest.fixture
def _csv_data(tmp_path: Path) -> RenderDataFile:
    """A small CSV with two numeric columns."""
    csv_path = tmp_path / "fixture.csv"
    pd.DataFrame({"col_x": [0.0, 1.0, 2.0], "col_y": [0.0, 1.0, 4.0]}).to_csv(
        csv_path, index=False
    )
    return RenderDataFile(file_id="fx", path=csv_path)


# ─────────────────────────── tests ──────────────────────────────────────


def test_3_recipe_scenario_counts(tmp_path: Path, _csv_data: RenderDataFile):
    """1 success + 1 skipped + 1 fail → counts add up."""
    ok_name = _make_test_recipe("ok_three_scn")
    fail_name = _make_test_recipe(
        "fail_three_scn", raise_during_render=ValueError
    )

    bindings = [
        RenderBinding(
            full_name=ok_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
        RenderBinding(
            full_name="test_render_loop.skipped_one",
            fully_bound=False,
            unbound_reason="missing column 'foo'",
        ),
        RenderBinding(
            full_name=fail_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]

    log = render_shortlist(
        bindings=bindings,
        data_files=[_csv_data],
        out_dir=tmp_path / "figs",
    )

    assert isinstance(log, RenderLog)
    assert log.n_attempted == 3
    assert log.n_success == 1
    assert log.n_skipped == 1
    assert log.n_failed == 1
    statuses = [o.status for o in log.outcomes]
    assert statuses == ["success", "skipped_unbound", "error_render"]


def test_report_writes_correct_structure(
    tmp_path: Path, _csv_data: RenderDataFile
):
    """The Markdown report contains all section headers and per-recipe rows."""
    ok_name = _make_test_recipe("ok_report")
    fail_name = _make_test_recipe(
        "fail_report", raise_during_render=RuntimeError
    )

    bindings = [
        RenderBinding(
            full_name=ok_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
        RenderBinding(
            full_name="test_render_loop.skipped_report",
            fully_bound=False,
            unbound_reason="data file absent",
        ),
        RenderBinding(
            full_name=fail_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]

    out_dir = tmp_path / "figs"
    log = render_shortlist(
        bindings=bindings,
        data_files=[_csv_data],
        out_dir=out_dir,
    )
    report_path = write_render_report(log, out_dir / "RENDER_REPORT.md")
    text = report_path.read_text(encoding="utf-8")

    assert report_path.name == "RENDER_REPORT.md"
    assert "# Render Report" in text
    assert "**panelforge version:**" in text
    assert "**Total recipes attempted:** 3" in text
    assert "**Rendered:** 1" in text
    assert "**Skipped (unbound):** 1" in text
    assert "**Failed (render error):** 1" in text
    assert "## Successful (1)" in text
    assert "## Skipped (1)" in text
    assert "## Failed (1)" in text
    assert "## Next steps" in text
    # Each per-recipe row should appear at least once.
    assert ok_name in text
    assert fail_name in text
    assert "test_render_loop.skipped_report" in text
    assert "data file absent" in text


def test_per_recipe_failure_does_not_halt_loop(
    tmp_path: Path, _csv_data: RenderDataFile
):
    """A ValueError in one recipe must not prevent the next from rendering."""
    fail_name = _make_test_recipe(
        "fail_no_halt", raise_during_render=ValueError
    )
    after_name = _make_test_recipe("after_no_halt")

    bindings = [
        RenderBinding(
            full_name=fail_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
        RenderBinding(
            full_name=after_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]

    log = render_shortlist(
        bindings=bindings,
        data_files=[_csv_data],
        out_dir=tmp_path / "figs",
    )

    assert log.n_attempted == 2
    assert log.n_failed == 1
    assert log.n_success == 1
    assert log.outcomes[0].status == "error_render"
    assert log.outcomes[1].status == "success"
    # Subsequent render produced both files.
    assert log.outcomes[1].pdf_path is not None
    assert log.outcomes[1].pdf_path.exists()


def test_environmental_failure_halts(tmp_path: Path, _csv_data: RenderDataFile):
    """An OSError during render must halt the loop with EnvironmentalFailure."""
    bad_name = _make_test_recipe(
        "fail_env_halt", raise_during_render=OSError
    )
    after_name = _make_test_recipe("after_env_halt")

    bindings = [
        RenderBinding(
            full_name=bad_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
        RenderBinding(
            full_name=after_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]

    out_dir = tmp_path / "figs"
    with pytest.raises(EnvironmentalFailure):
        render_shortlist(
            bindings=bindings,
            data_files=[_csv_data],
            out_dir=out_dir,
        )

    # The "after" recipe must NOT have produced any artefacts.
    after_pdf = out_dir / "test_render_loop.after_env_halt.pdf"
    assert not after_pdf.exists()


def test_environmental_failure_on_importerror(
    tmp_path: Path, _csv_data: RenderDataFile
):
    """An ImportError during render must halt with EnvironmentalFailure."""
    bad_name = _make_test_recipe(
        "fail_import_halt", raise_during_render=ImportError
    )
    bindings = [
        RenderBinding(
            full_name=bad_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]
    with pytest.raises(EnvironmentalFailure):
        render_shortlist(
            bindings=bindings,
            data_files=[_csv_data],
            out_dir=tmp_path / "figs",
        )


def test_pdf_and_png_produced(tmp_path: Path, _csv_data: RenderDataFile):
    """A successful render writes both PDF and PNG with non-zero size."""
    ok_name = _make_test_recipe("ok_artifacts")
    bindings = [
        RenderBinding(
            full_name=ok_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]

    out_dir = tmp_path / "figs"
    log = render_shortlist(
        bindings=bindings,
        data_files=[_csv_data],
        out_dir=out_dir,
    )
    o = log.outcomes[0]
    assert o.status == "success"
    assert o.pdf_path is not None and o.pdf_path.exists()
    assert o.png_path is not None and o.png_path.exists()
    assert o.pdf_path.stat().st_size > 0
    assert o.png_path.stat().st_size > 0
    assert o.pdf_path.suffix == ".pdf"
    assert o.png_path.suffix == ".png"


def test_excerpt_traceback_returns_last_n_lines():
    """`_excerpt_traceback` keeps the trailing few lines of the formatted tb."""
    try:
        raise ValueError("boom")
    except ValueError as exc:
        excerpt = _excerpt_traceback(exc, n_lines=5)
    lines = excerpt.splitlines()
    assert 1 <= len(lines) <= 5
    assert "ValueError" in excerpt
    assert "boom" in excerpt


def test_failed_outcome_contains_traceback_excerpt(
    tmp_path: Path, _csv_data: RenderDataFile
):
    """Failed-recipe outcome should include a non-empty traceback excerpt."""
    fail_name = _make_test_recipe(
        "fail_excerpt", raise_during_render=RuntimeError
    )
    bindings = [
        RenderBinding(
            full_name=fail_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]
    log = render_shortlist(
        bindings=bindings,
        data_files=[_csv_data],
        out_dir=tmp_path / "figs",
    )
    o = log.outcomes[0]
    assert o.status == "error_render"
    assert o.traceback_excerpt is not None
    excerpt_lines = o.traceback_excerpt.splitlines()
    assert 1 <= len(excerpt_lines) <= 5


def test_empty_bindings_yield_empty_log(tmp_path: Path):
    """Empty shortlist → counts all zero, outcomes empty, report still writes."""
    log = render_shortlist(
        bindings=[],
        data_files=[],
        out_dir=tmp_path / "figs",
    )
    assert log.n_attempted == 0
    assert log.n_success == 0
    assert log.n_skipped == 0
    assert log.n_failed == 0
    assert log.outcomes == ()

    report_path = write_render_report(log, tmp_path / "figs" / "RENDER_REPORT.md")
    text = report_path.read_text(encoding="utf-8")
    assert "**Total recipes attempted:** 0" in text
    assert "## Successful (0)" in text
    assert "## Skipped (0)" in text
    assert "## Failed (0)" in text


def test_contract_validation_error_classifies_as_error_contract(
    tmp_path: Path, _csv_data: RenderDataFile
):
    """Pydantic ValidationError must produce status `error_contract`."""
    ok_name = _make_test_recipe("contract_failure")
    # Map only xs — `ys` will be missing → ValidationError.
    bindings = [
        RenderBinding(
            full_name=ok_name,
            fully_bound=True,
            column_mapping={"xs": "col_x"},  # ys intentionally absent
            data_file_id="fx",
        ),
    ]
    log = render_shortlist(
        bindings=bindings,
        data_files=[_csv_data],
        out_dir=tmp_path / "figs",
    )
    assert log.n_failed == 1
    o = log.outcomes[0]
    assert o.status == "error_contract"
    assert o.error_class == "ContractValidationError"


def test_environmental_failure_on_unwritable_dir(tmp_path: Path):
    """Failing to create the output directory raises EnvironmentalFailure."""
    # Pre-create a *file* at the target out_dir path so mkdir(parents=...) fails.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir", encoding="utf-8")

    with pytest.raises(EnvironmentalFailure):
        render_shortlist(
            bindings=[],
            data_files=[],
            out_dir=blocker,  # This path exists but is a file, not a dir.
        )


def test_oserror_during_data_load_halts(tmp_path: Path):
    """An OSError raised while loading data is treated as environmental."""
    ok_name = _make_test_recipe("ok_data_load_halts")
    bindings = [
        RenderBinding(
            full_name=ok_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]
    bad_data = RenderDataFile(file_id="fx", path=tmp_path / "does_not_exist.csv")

    with pytest.raises(EnvironmentalFailure):
        render_shortlist(
            bindings=bindings,
            data_files=[bad_data],
            out_dir=tmp_path / "figs",
        )


def test_keyboard_interrupt_propagates(tmp_path: Path, _csv_data: RenderDataFile):
    """KeyboardInterrupt must NOT be wrapped — it propagates unchanged."""
    ok_name = _make_test_recipe("ok_kbd_interrupt")
    bindings = [
        RenderBinding(
            full_name=ok_name,
            fully_bound=True,
            column_mapping={"xs": "col_x", "ys": "col_y"},
            data_file_id="fx",
        ),
    ]

    # Patch the renderer (looked up via the registry) to raise KeyboardInterrupt.
    from panelforge_figures.core.contract import get_recipe

    entry = get_recipe(ok_name)

    def _interrupt(contract, ax=None, **_):
        raise KeyboardInterrupt

    with patch.object(entry, "render", _interrupt):
        with pytest.raises(KeyboardInterrupt):
            render_shortlist(
                bindings=bindings,
                data_files=[_csv_data],
                out_dir=tmp_path / "figs",
            )


# ─────────────────────── multi-source binding (A6/A7) ───────────────────


def test_multi_source_render_binding_preserves_all_files(tmp_path: Path) -> None:
    """`to_render_binding` must populate ``data_file_per_field`` with the
    per-field source paths so multi-file recipes survive the conversion.

    Regression test for DEFECT-A6: previously, when a recipe pulled
    fields from 2+ files, ``data_file_id`` collapsed to ``None`` and the
    render loop loaded nothing — every multi-source recipe failed
    silently with an ``error_contract`` outcome.
    """
    from panelforge_figures.manifest.data_bridge import (
        FieldBinding,
        RecipeBinding,
        to_render_binding,
    )

    csv_a = tmp_path / "a.csv"
    csv_b = tmp_path / "b.csv"
    csv_a.write_text("col_x\n1.0\n", encoding="utf-8")
    csv_b.write_text("col_y\n2.0\n", encoding="utf-8")

    rb = RecipeBinding(
        full_name="multi.example",
        bindings=(
            FieldBinding(
                contract_field="xs", field_type="list[float]", is_required=True,
                data_source=csv_a, column_name="col_x",
                pass_used="exact", confidence=1.0,
            ),
            FieldBinding(
                contract_field="ys", field_type="list[float]", is_required=True,
                data_source=csv_b, column_name="col_y",
                pass_used="exact", confidence=1.0,
            ),
        ),
        fully_bound=True,
        skipped_reason=None,
    )
    rendered = to_render_binding(rb)
    assert rendered.data_file_per_field == {"xs": csv_a, "ys": csv_b}
    # data_file_id collapses to None when sources differ — the render loop
    # uses data_file_per_field instead, so this is correct behaviour.
    assert rendered.data_file_id is None


def test_multi_source_recipe_renders_without_error_contract(tmp_path: Path) -> None:
    """A recipe whose contract pulls columns from two different CSVs must
    render successfully end-to-end via the render loop's multi-source
    code path.
    """
    ok_name = _make_test_recipe("ok_multi_source")
    csv_x = tmp_path / "x.csv"
    csv_y = tmp_path / "y.csv"
    pd.DataFrame({"col_x": [0.0, 1.0, 2.0]}).to_csv(csv_x, index=False)
    pd.DataFrame({"col_y": [0.0, 1.0, 4.0]}).to_csv(csv_y, index=False)

    binding = RenderBinding(
        full_name=ok_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_per_field={"xs": csv_x, "ys": csv_y},
    )

    log = render_shortlist(
        bindings=[binding],
        data_files=[],  # The loop reads paths directly from data_file_per_field.
        out_dir=tmp_path / "figs",
    )
    assert log.n_attempted == 1
    assert log.n_success == 1
    assert log.outcomes[0].status == "success"


def test_multi_source_via_to_render_binding_e2e(tmp_path: Path) -> None:
    """End-to-end: build a `RecipeBinding` (canonical shape) with fields
    in two files, convert via ``to_render_binding``, render — must succeed.
    """
    from panelforge_figures.manifest.data_bridge import (
        FieldBinding,
        RecipeBinding,
        to_render_binding,
    )

    ok_name = _make_test_recipe("ok_multi_e2e")
    csv_x = tmp_path / "fx.csv"
    csv_y = tmp_path / "fy.csv"
    pd.DataFrame({"col_x": [0.0, 1.0]}).to_csv(csv_x, index=False)
    pd.DataFrame({"col_y": [0.0, 1.0]}).to_csv(csv_y, index=False)

    canonical = RecipeBinding(
        full_name=ok_name,
        bindings=(
            FieldBinding(
                contract_field="xs", field_type="list[float]", is_required=True,
                data_source=csv_x, column_name="col_x",
                pass_used="exact", confidence=1.0,
            ),
            FieldBinding(
                contract_field="ys", field_type="list[float]", is_required=True,
                data_source=csv_y, column_name="col_y",
                pass_used="exact", confidence=1.0,
            ),
        ),
        fully_bound=True,
        skipped_reason=None,
    )
    flat = to_render_binding(canonical)
    log = render_shortlist(
        bindings=[flat],
        data_files=[],
        out_dir=tmp_path / "figs",
    )
    assert log.n_success == 1
    assert log.outcomes[0].status == "success"


def test_unified_fully_bound_definition(tmp_path: Path) -> None:
    """The CLI's reconstruction logic must match `bind_recipe_to_data`'s
    fully_bound output — both call into ``compute_fully_bound``.

    Fixture: 3 required fields, only 2 bound → both code paths must
    return ``False``.  This is the regression test for DEFECT-A7's
    inconsistency between the CLI and the canonical predicate.
    """
    from panelforge_figures.manifest.data_bridge import (
        FieldBinding,
        compute_fully_bound,
    )

    fbs = [
        FieldBinding(
            contract_field="a", field_type="list[float]", is_required=True,
            data_source=tmp_path / "a.csv", column_name="a",
            pass_used="exact", confidence=1.0,
        ),
        FieldBinding(
            contract_field="b", field_type="list[float]", is_required=True,
            data_source=tmp_path / "b.csv", column_name="b",
            pass_used="exact", confidence=1.0,
        ),
        FieldBinding(
            contract_field="c", field_type="list[float]", is_required=True,
            data_source=None, column_name=None,
            pass_used="unbound", confidence=0.0,
        ),
    ]
    # 1 of 3 required is unbound → must be False.
    assert compute_fully_bound(fbs) is False
    # Old CLI definition (column_name-based) would have agreed here, but
    # they could diverge for cases where column_name is set but
    # data_source is not — the helper guarantees a single answer.
    column_based = all(fb.column_name is not None for fb in fbs)
    source_based = compute_fully_bound(fbs)
    assert column_based == source_based  # they agree in this case
    # And when fully bound:
    fbs_bound = [
        FieldBinding(
            contract_field="a", field_type="list[float]", is_required=True,
            data_source=tmp_path / "a.csv", column_name="a",
            pass_used="exact", confidence=1.0,
        ),
        FieldBinding(
            contract_field="b", field_type="list[float]", is_required=True,
            data_source=tmp_path / "b.csv", column_name="b",
            pass_used="exact", confidence=1.0,
        ),
    ]
    assert compute_fully_bound(fbs_bound) is True


def test_data_file_id_back_compat_still_works(
    tmp_path: Path, _csv_data: RenderDataFile
) -> None:
    """Bindings using only the legacy ``data_file_id`` (no
    ``data_file_per_field``) must still load data correctly via
    the single-source fallback path."""
    ok_name = _make_test_recipe("ok_data_file_id_back_compat")
    binding = RenderBinding(
        full_name=ok_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_id="fx",  # legacy field — no data_file_per_field set.
    )
    log = render_shortlist(
        bindings=[binding],
        data_files=[_csv_data],
        out_dir=tmp_path / "figs",
    )
    assert log.n_success == 1
    assert log.outcomes[0].status == "success"


# ─────────────────────── audit integration (Sprint 1A) ──────────────────


def _make_audited_recipe(
    name: str,
    *,
    statistical_contract,  # noqa: ANN001 — late-binding to avoid spec churn
):
    """Register a synthetic recipe carrying an explicit StatisticalContract.

    Mirrors ``_make_test_recipe`` but threads the audit-layer contract
    through ``RecipeMetadata`` so the render loop's audit step has
    something to evaluate.
    """
    metadata = RecipeMetadata(
        name=name,
        modality="test_render_loop",
        family=RecipeFamily.scatter_collapse,
        answers_question="audit fixture recipe",
        required_fields=("xs", "ys"),
        statistical_contract=statistical_contract,
    )

    @register_recipe(
        metadata=metadata,
        contract=_FixtureContract,
        demo_contract=_fixture_demo,
    )
    def render(contract: _FixtureContract, ax=None, **_):
        if ax is None:
            import matplotlib.pyplot as plt
            _, ax = plt.subplots()
        ax.scatter(contract.xs, contract.ys)
        return ax

    return f"test_render_loop.{name}"


def test_audit_refused_recipe_produces_error_audit_refuse(tmp_path: Path) -> None:
    """A recipe with min_n_per_group=6 against 3-row CSV → status `error_audit_refuse`.

    The render must NOT be attempted; no PDF/PNG should land on disk.
    """
    from panelforge_figures.core.statistical_contract import StatisticalContract

    csv_path = tmp_path / "tiny.csv"
    pd.DataFrame({"col_x": [0.0, 1.0, 2.0], "col_y": [0.0, 1.0, 4.0]}).to_csv(
        csv_path, index=False
    )
    full_name = _make_audited_recipe(
        "audit_refuse_strict",
        statistical_contract=StatisticalContract(min_n_per_group=6),
    )
    binding = RenderBinding(
        full_name=full_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_id="fx_audit",
    )
    log = render_shortlist(
        bindings=[binding],
        data_files=[RenderDataFile(file_id="fx_audit", path=csv_path)],
        out_dir=tmp_path / "figs",
    )
    assert log.n_attempted == 1
    assert log.n_failed == 1
    assert log.n_success == 0
    o = log.outcomes[0]
    assert o.status == "error_audit_refuse"
    assert o.error_class == "StatisticalContractViolation"
    assert o.error_message and "underpowered" in o.error_message
    assert o.pdf_path is None and o.png_path is None
    # No render artefacts on disk — the audit short-circuited before mpl was used.
    expected_pdf = (tmp_path / "figs" / f"{full_name}.pdf")
    assert not expected_pdf.exists()
    # The audit findings should be carried on the outcome.
    assert len(o.audit_findings) >= 1


def test_audit_skip_flag_bypasses_audit_step(tmp_path: Path) -> None:
    """Same refusal-grade contract + data, but with ``skip_audit=True`` → render runs.

    Reverts to pre-Sprint-1A behaviour: the figure is produced even
    though the contract would normally refuse.
    """
    from panelforge_figures.core.statistical_contract import StatisticalContract

    csv_path = tmp_path / "tiny_skip.csv"
    pd.DataFrame({"col_x": [0.0, 1.0, 2.0], "col_y": [0.0, 1.0, 4.0]}).to_csv(
        csv_path, index=False
    )
    full_name = _make_audited_recipe(
        "audit_skip_bypass",
        statistical_contract=StatisticalContract(min_n_per_group=6),
    )
    binding = RenderBinding(
        full_name=full_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_id="fx_skip",
    )
    log = render_shortlist(
        bindings=[binding],
        data_files=[RenderDataFile(file_id="fx_skip", path=csv_path)],
        out_dir=tmp_path / "figs",
        skip_audit=True,
    )
    assert log.n_success == 1
    o = log.outcomes[0]
    assert o.status == "success"
    assert o.pdf_path is not None and o.pdf_path.exists()
    # When the audit is skipped we don't carry findings on the outcome.
    assert o.audit_findings == ()


def test_permissive_contract_audit_is_no_op(
    tmp_path: Path, _csv_data: RenderDataFile,
) -> None:
    """A recipe carrying the default permissive contract renders silently.

    The audit step short-circuits (``_is_permissive`` returns True) so
    the outcome carries no findings and the render proceeds normally —
    this is the backwards-compat guarantee for the 392 untagged recipes.
    """
    full_name = _make_test_recipe("audit_permissive_passthrough")
    binding = RenderBinding(
        full_name=full_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_id="fx",
    )
    log = render_shortlist(
        bindings=[binding],
        data_files=[_csv_data],
        out_dir=tmp_path / "figs",
    )
    assert log.n_success == 1
    o = log.outcomes[0]
    assert o.status == "success"
    # Permissive contract → audit early-returns → no findings recorded.
    assert o.audit_findings == ()


def test_audit_warn_outcome_renders_and_records_findings(tmp_path: Path) -> None:
    """A WARN-class audit verdict produces a successful render and carries the findings.

    Heavy-tailed data + ``approximately_gaussian`` assumption triggers
    ``non_normal_with_parametric_test`` (default verdict ``warn``); the
    figure renders, and the warning rides along on the outcome so the
    report writer can surface it.
    """
    import numpy as np

    from panelforge_figures.core.statistical_contract import StatisticalContract

    rng = np.random.default_rng(seed=7)
    # Two independent draws so the design matrix is full-rank — otherwise
    # ``singular_design`` would also fire and escalate to refuse.
    xs = rng.lognormal(mean=0.0, sigma=1.5, size=120)
    ys = rng.lognormal(mean=0.0, sigma=1.5, size=120)
    csv_path = tmp_path / "warn.csv"
    pd.DataFrame({
        "col_x": xs.tolist(),
        "col_y": ys.tolist(),
    }).to_csv(csv_path, index=False)

    full_name = _make_audited_recipe(
        "audit_warn_render_continues",
        statistical_contract=StatisticalContract(
            distribution_assumption="approximately_gaussian",
        ),
    )
    binding = RenderBinding(
        full_name=full_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_id="fx_warn",
    )
    log = render_shortlist(
        bindings=[binding],
        data_files=[RenderDataFile(file_id="fx_warn", path=csv_path)],
        out_dir=tmp_path / "figs",
    )
    assert log.n_success == 1
    o = log.outcomes[0]
    assert o.status == "success"
    # The warning is carried on the outcome.
    severities = {str(getattr(f, "severity", "")).lower() for f in o.audit_findings}
    assert "warn" in severities


def test_render_report_contains_statistical_warnings_section(
    tmp_path: Path,
) -> None:
    """`write_render_report` emits a `## Statistical warnings` section.

    Even when the run produces zero warnings, the section header must
    still appear so consumers can rely on the report shape.
    """
    log = render_shortlist(
        bindings=[],
        data_files=[],
        out_dir=tmp_path / "figs",
    )
    report_path = write_render_report(log, tmp_path / "figs" / "RENDER_REPORT.md")
    text = report_path.read_text(encoding="utf-8")
    assert "## Statistical warnings" in text
    assert "## Audit refused" in text


def test_render_report_audit_refused_section_lists_recipe(
    tmp_path: Path,
) -> None:
    """A refused recipe must appear in the `## Audit refused` table."""
    from panelforge_figures.core.statistical_contract import StatisticalContract

    csv_path = tmp_path / "tiny_report.csv"
    pd.DataFrame({"col_x": [0.0, 1.0, 2.0], "col_y": [0.0, 1.0, 4.0]}).to_csv(
        csv_path, index=False
    )
    full_name = _make_audited_recipe(
        "audit_report_refuse_listed",
        statistical_contract=StatisticalContract(min_n_per_group=6),
    )
    binding = RenderBinding(
        full_name=full_name,
        fully_bound=True,
        column_mapping={"xs": "col_x", "ys": "col_y"},
        data_file_id="fx_report",
    )
    log = render_shortlist(
        bindings=[binding],
        data_files=[RenderDataFile(file_id="fx_report", path=csv_path)],
        out_dir=tmp_path / "figs",
    )
    report_path = write_render_report(log, tmp_path / "figs" / "RENDER_REPORT.md")
    text = report_path.read_text(encoding="utf-8")
    assert "## Audit refused (1)" in text
    assert full_name in text
    assert "underpowered" in text
