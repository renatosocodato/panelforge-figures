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
