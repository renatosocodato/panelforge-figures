"""Sprint 1C composition layer — schema + engine tests.

Pairs with ``manifest/figure_schema.py`` (Pydantic models) and
``manifest/figure_composition.py`` (engine).  CLI surface tests live in
``tests/test_compose_cli.py``.

The tests intentionally exercise the public API surface advertised by
``docs/spec_composition_layer.md`` — schema round-trips, layout
dispatch, panel placement, axis-linking, recipe-existence checks — and
avoid pinning down internal helpers that may move during follow-up
patches.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from panelforge_figures.manifest import (
    CompositionPanelSpec,
    FigureCompositionSpec,
    FreeformLayout,
    GridLayout,
    GridspecLayout,
    PartitionedPanelSpec,
    compose_figure,
    render_figure_yaml,
    validate_figure_yaml,
)

# Where the curated fixtures live.
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "figure_specs"


# ─────────────────────────── schema round-trips ─────────────────────────


def test_figurespec_round_trips_through_pydantic_dict() -> None:
    """A fully-specified FigureSpec survives ``model_dump()`` + reconstruction."""
    spec = FigureCompositionSpec(
        figure_id="rt_demo",
        title="Roundtrip demo",
        caption="caption text",
        layout=GridLayout(rows=2, cols=3),
        panels=[
            CompositionPanelSpec(id="A", recipe="mod.alpha"),
            CompositionPanelSpec(id="B", recipe="mod.beta", caption="B caption"),
        ],
    )
    dump = spec.model_dump()
    reconstructed = FigureCompositionSpec(**dump)
    assert reconstructed == spec
    assert reconstructed.figure_id == "rt_demo"
    assert reconstructed.layout.type == "grid"
    assert reconstructed.layout.rows == 2
    assert reconstructed.layout.cols == 3
    assert len(reconstructed.panels) == 2


def test_grid_layout_parses_correctly() -> None:
    """GridLayout accepts row/col bounds and ratio overrides."""
    layout = GridLayout(
        rows=3, cols=2,
        height_ratios=(1.0, 0.5, 1.0),
        width_ratios=(1.0, 1.5),
        hspace=0.4, wspace=0.2,
    )
    assert layout.type == "grid"
    assert layout.rows == 3
    assert layout.cols == 2
    assert layout.height_ratios == (1.0, 0.5, 1.0)
    assert layout.width_ratios == (1.0, 1.5)


def test_gridspec_layout_parses_correctly() -> None:
    """GridspecLayout discriminator + dimensions parse cleanly."""
    layout = GridspecLayout(rows=4, cols=4, hspace=0.5, wspace=0.5)
    assert layout.type == "gridspec"
    assert layout.rows == 4
    assert layout.cols == 4


def test_freeform_layout_parses_correctly() -> None:
    """FreeformLayout has no dimension constraints — panels carry the bbox."""
    layout = FreeformLayout()
    assert layout.type == "freeform"


def test_layout_discriminator_picks_correct_class() -> None:
    """The Layout union dispatches on the ``type`` literal field."""
    spec = FigureCompositionSpec(
        figure_id="disp",
        layout={"type": "freeform"},  # type: ignore[arg-type]
        panels=[
            CompositionPanelSpec(
                id="A",
                recipe="mod.foo",
                freeform_bbox=(0.1, 0.1, 0.8, 0.8),
            ),
        ],
    )
    assert isinstance(spec.layout, FreeformLayout)


# ─────────────────────────── PanelSpec validation ───────────────────────


@pytest.mark.parametrize("ident", ["A", "B", "AB", "ABC", "1234"])
def test_panel_id_accepts_short_strings(ident: str) -> None:
    """PanelSpec.id allows 1-4 char identifiers."""
    panel = CompositionPanelSpec(id=ident, recipe="mod.r")
    assert panel.id == ident


@pytest.mark.parametrize("ident", ["", "ABCDE", "TOO_LONG", "F-CKO"])
def test_panel_id_rejects_out_of_range(ident: str) -> None:
    """PanelSpec.id rejects empty and >4 char identifiers (per Sprint 1C scaffold)."""
    with pytest.raises(ValidationError):
        CompositionPanelSpec(id=ident, recipe="mod.r")


def test_panels_list_min_length() -> None:
    """FigureSpec requires at least one panel."""
    with pytest.raises(ValidationError):
        FigureCompositionSpec(
            figure_id="empty",
            layout=GridLayout(rows=1, cols=1),
            panels=[],
        )


def test_partitioned_panel_spec_parses() -> None:
    """PartitionedPanelSpec is a forward-compat marker (not yet rendered)."""
    p = PartitionedPanelSpec(
        base_id="C-F",
        recipe="mixed_effects_models.two_way_anova_summary_plot",
        partition_by="tags.genotype",
    )
    assert p.base_id == "C-F"
    assert p.partition_by == "tags.genotype"
    assert p.caption_template == "{partition_value}"


# ─────────────────────────── compose_figure — fixtures ──────────────────


def test_compose_figure_example_fixture_creates_pdf(tmp_path: Path) -> None:
    """Composing the example fixture produces a non-empty PDF on disk."""
    out = render_figure_yaml(
        _FIXTURES / "example_figure_3.yaml",
        out_dir=tmp_path,
    )
    out_path = Path(out)
    assert out_path.parent == tmp_path, (
        f"output should land under tmp_path; got {out_path.parent!s}"
    )
    assert out_path.exists(), f"PDF not written: {out_path}"
    assert out_path.stat().st_size > 0
    assert out_path.suffix == ".pdf"


def test_compose_figure_factorial_fixture_creates_pdf(tmp_path: Path) -> None:
    """The 2x2 factorial fixture renders without error."""
    out = render_figure_yaml(
        _FIXTURES / "example_factorial_2x2.yaml",
        out_dir=tmp_path,
    )
    out_path = Path(out)
    assert out_path.parent == tmp_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_compose_figure_freeform_fixture_creates_pdf(tmp_path: Path) -> None:
    """The freeform graphical-abstract fixture renders without error."""
    out = render_figure_yaml(
        _FIXTURES / "freeform_graphical_abstract.yaml",
        out_dir=tmp_path,
    )
    out_path = Path(out)
    assert out_path.parent == tmp_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


# ─────────────────────────── compose_figure — direct API ────────────────


def test_compose_figure_uses_explicit_output_path(tmp_path: Path) -> None:
    """When output_path is set, the engine writes there (not out_dir/<id>.pdf)."""
    target = tmp_path / "deep" / "nested" / "out.pdf"
    spec = FigureCompositionSpec(
        figure_id="explicit_out",
        layout=GridLayout(rows=1, cols=2),
        output_path=target,
        panels=[
            CompositionPanelSpec(
                id="A",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
            ),
            CompositionPanelSpec(
                id="B",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
            ),
        ],
    )
    out = compose_figure(spec)
    assert Path(out) == target
    assert target.exists()
    assert target.stat().st_size > 0


def test_compose_figure_links_shared_y_axis(tmp_path: Path) -> None:
    """A panel with shared_axis_with shares its y-axis with the target."""
    target = tmp_path / "linked.pdf"
    spec = FigureCompositionSpec(
        figure_id="linked",
        layout=GridLayout(rows=1, cols=2),
        output_path=target,
        panels=[
            CompositionPanelSpec(
                id="A",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
            ),
            CompositionPanelSpec(
                id="B",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
                shared_axis_with="A",
            ),
        ],
    )
    # Capture axes by patching plt.figure inside the compose call so we
    # can inspect the linkage state without re-rendering.
    import matplotlib.pyplot as plt

    captured: list = []
    real_figure = plt.figure

    def _capture(*args, **kwargs):
        f = real_figure(*args, **kwargs)
        captured.append(f)
        return f

    plt.figure = _capture  # type: ignore[assignment]
    try:
        out = compose_figure(spec)
    finally:
        plt.figure = real_figure  # type: ignore[assignment]

    assert Path(out).exists()
    # The figure is closed by compose_figure but its axes object survives.
    fig = captured[0]
    axes = fig.axes
    assert len(axes) == 2
    # matplotlib's ax.sharey wires both axes to a shared sibling group;
    # asking either one for its sibling list returns the other plus self.
    siblings_a = set(axes[0].get_shared_y_axes().get_siblings(axes[0]))
    assert axes[1] in siblings_a, (
        "panel B's y-axis should be linked to panel A's"
    )


def test_compose_figure_writes_panel_labels(tmp_path: Path) -> None:
    """Each panel gets an A/B/C/... overlay placed via ``ax.text``."""
    target = tmp_path / "labels.pdf"
    spec = FigureCompositionSpec(
        figure_id="labels",
        layout=GridLayout(rows=1, cols=3),
        output_path=target,
        panels=[
            CompositionPanelSpec(id=ident, recipe="meta_and_diagnostic.bayes_factor_arrow_plot")
            for ident in ("A", "B", "C")
        ],
    )

    import matplotlib.pyplot as plt

    captured: list = []
    real_figure = plt.figure

    def _capture(*args, **kwargs):
        f = real_figure(*args, **kwargs)
        captured.append(f)
        return f

    plt.figure = _capture  # type: ignore[assignment]
    try:
        compose_figure(spec)
    finally:
        plt.figure = real_figure  # type: ignore[assignment]

    fig = captured[0]
    # Each axes should carry exactly one Text object whose body is the
    # panel id letter at the configured label_position.
    found_labels = set()
    for ax in fig.axes:
        for txt in ax.texts:
            body = txt.get_text()
            if body in {"A", "B", "C"}:
                found_labels.add(body)
    assert found_labels == {"A", "B", "C"}


def test_compose_figure_panel_label_style_none_skips(tmp_path: Path) -> None:
    """``panel_label_style='none'`` suppresses the A/B/C overlay."""
    target = tmp_path / "no_labels.pdf"
    spec = FigureCompositionSpec(
        figure_id="nolabels",
        layout=GridLayout(rows=1, cols=2),
        output_path=target,
        panel_label_style="none",
        panels=[
            CompositionPanelSpec(id="A", recipe="meta_and_diagnostic.bayes_factor_arrow_plot"),
            CompositionPanelSpec(id="B", recipe="meta_and_diagnostic.bayes_factor_arrow_plot"),
        ],
    )

    import matplotlib.pyplot as plt

    captured: list = []
    real_figure = plt.figure

    def _capture(*args, **kwargs):
        f = real_figure(*args, **kwargs)
        captured.append(f)
        return f

    plt.figure = _capture  # type: ignore[assignment]
    try:
        compose_figure(spec)
    finally:
        plt.figure = real_figure  # type: ignore[assignment]

    fig = captured[0]
    for ax in fig.axes:
        for txt in ax.texts:
            assert txt.get_text() not in {"A", "B"}, (
                "panel-label overlay should not be drawn when style='none'"
            )


def test_compose_figure_gridspec_requires_grid_position(tmp_path: Path) -> None:
    """GridspecLayout panels must declare grid_position."""
    spec = FigureCompositionSpec(
        figure_id="bad_gs",
        layout=GridspecLayout(rows=2, cols=2),
        output_path=tmp_path / "bad.pdf",
        panels=[
            CompositionPanelSpec(
                id="A",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
            ),
        ],
    )
    with pytest.raises(ValueError, match="grid_position"):
        compose_figure(spec)


def test_compose_figure_freeform_requires_bbox(tmp_path: Path) -> None:
    """FreeformLayout panels must declare freeform_bbox."""
    spec = FigureCompositionSpec(
        figure_id="bad_ff",
        layout=FreeformLayout(),
        output_path=tmp_path / "bad.pdf",
        panels=[
            CompositionPanelSpec(
                id="A",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
            ),
        ],
    )
    with pytest.raises(ValueError, match="freeform_bbox"):
        compose_figure(spec)


def test_compose_figure_partitioned_panel_not_implemented(tmp_path: Path) -> None:
    """PartitionedPanelSpec raises NotImplementedError until expansion lands."""
    spec = FigureCompositionSpec(
        figure_id="part",
        layout=GridLayout(rows=1, cols=2),
        output_path=tmp_path / "part.pdf",
        panels=[
            PartitionedPanelSpec(
                base_id="P",
                recipe="meta_and_diagnostic.bayes_factor_arrow_plot",
                partition_by="tags.sex",
            ),
        ],
    )
    with pytest.raises(NotImplementedError):
        compose_figure(spec)


# ─────────────────────────── validate_figure_yaml ───────────────────────


def test_validate_figure_yaml_passes_for_valid_fixture() -> None:
    """A real fixture with real recipes returns an empty problems list."""
    problems = validate_figure_yaml(_FIXTURES / "example_figure_3.yaml")
    assert problems == [], (
        f"example fixture should validate cleanly; got: {problems}"
    )


def test_validate_figure_yaml_catches_yaml_syntax_errors(tmp_path: Path) -> None:
    """Malformed YAML returns a single 'YAML parse error' problem."""
    bad = tmp_path / "broken.figure.yaml"
    bad.write_text("figure_id: x\nlayout: [unclosed\n", encoding="utf-8")
    problems = validate_figure_yaml(bad)
    assert problems
    assert any("YAML parse error" in p for p in problems)


def test_validate_figure_yaml_catches_unknown_recipe(tmp_path: Path) -> None:
    """A panel pointing at a non-existent recipe surfaces a problem."""
    bad = tmp_path / "unknown_recipe.figure.yaml"
    bad.write_text(
        yaml.safe_dump({
            "figure_id": "unknown_recipe",
            "layout": {"type": "grid", "rows": 1, "cols": 1},
            "panels": [
                {"id": "A", "recipe": "nonexistent_modality.this_recipe_does_not_exist"},
            ],
        }),
        encoding="utf-8",
    )
    problems = validate_figure_yaml(bad)
    assert any(
        "unknown recipe" in p and "this_recipe_does_not_exist" in p
        for p in problems
    ), problems


def test_validate_figure_yaml_catches_dangling_shared_axis(tmp_path: Path) -> None:
    """shared_axis_with referencing a missing panel id is flagged."""
    bad = tmp_path / "dangling_link.figure.yaml"
    bad.write_text(
        yaml.safe_dump({
            "figure_id": "dangling",
            "layout": {"type": "grid", "rows": 1, "cols": 2},
            "panels": [
                {"id": "A", "recipe": "meta_and_diagnostic.bayes_factor_arrow_plot"},
                {
                    "id": "B",
                    "recipe": "meta_and_diagnostic.bayes_factor_arrow_plot",
                    "shared_axis_with": "Z",
                },
            ],
        }),
        encoding="utf-8",
    )
    problems = validate_figure_yaml(bad)
    assert any("shared_axis_with" in p and "Z" in p for p in problems), problems


def test_validate_figure_yaml_catches_schema_error(tmp_path: Path) -> None:
    """A missing required field surfaces as a schema error."""
    bad = tmp_path / "no_layout.figure.yaml"
    bad.write_text(
        yaml.safe_dump({
            "figure_id": "no_layout",
            "panels": [
                {"id": "A", "recipe": "meta_and_diagnostic.bayes_factor_arrow_plot"},
            ],
        }),
        encoding="utf-8",
    )
    problems = validate_figure_yaml(bad)
    assert any("schema error" in p for p in problems)
