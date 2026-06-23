"""Multi-panel composition engine — turn a :class:`FigureSpec` into a PDF.

Sprint 1C / v1.7.0 — see ``docs/spec_composition_layer.md``.

This module is the **engine** half of the composition layer:

* :class:`compose_figure` — given a validated :class:`FigureSpec` plus an
  optional registry/data-files map, builds a matplotlib ``Figure``,
  dispatches one axes per panel, calls each recipe's ``render(contract,
  ax)``, and saves the output PDF.
* :func:`render_figure_yaml` — convenience wrapper that loads a YAML file
  off disk, parses it through :class:`FigureSpec`, and composes.
* :func:`validate_figure_yaml` — schema + recipe-existence check that
  *does not render*.  Used by ``figures compose-validate`` (CLI surface,
  Build-B).

The module deliberately avoids touching the existing per-panel render
loop (``manifest/render_loop.py``).  Composition is a strict superset:
each panel still flows through the same ``get_recipe(name).render(...)``
call, just into a shared figure rather than its own file.

The schema dataclasses live in :mod:`figure_schema`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from .figure_schema import (
    FigureSpec,
    FreeformLayout,
    GridLayout,
    GridspecLayout,
    PanelSpec,
    PartitionedPanelSpec,
)

log = logging.getLogger(__name__)


# ─────────────────────────── public API ─────────────────────────────────


def compose_figure(
    spec: FigureSpec,
    *,
    registry: dict[str, Any] | None = None,
    data_files: dict[str, Path] | None = None,
) -> Path:
    """Render a multi-panel figure per ``spec``; return the saved PDF path.

    Parameters
    ----------
    spec
        The validated :class:`FigureSpec`.  Layout dispatch is driven by
        ``spec.layout`` and panels are placed in declaration order.
    registry
        Reserved for future use — passing ``None`` (the default) lets the
        engine resolve recipes through the global registry via
        ``core.contract.get_recipe``.  Tests use this hook to inject a
        synthetic registry without touching the package singleton.
    data_files
        Reserved for the future data adapter.  No panel currently consumes
        ``data`` (supplying ``panel.data`` raises ``NotImplementedError``),
        so this mapping is accepted but unused today.  Panels render from
        the recipe's ``demo_contract()``.

    Returns
    -------
    Path
        Absolute path to the rendered PDF.

    Notes
    -----
    Per-panel exceptions are NOT swallowed by this function — composition
    is intended to either succeed wholly or raise.  The render loop's
    permissive per-recipe error handling lives in
    ``manifest/render_loop.py`` for single-panel batch use.
    """
    # Lazy import — keeps the schema-only path (e.g. ``validate_figure_yaml``)
    # free of recipe-tree side effects when no actual render is needed.
    from ..core.contract import ensure_all_imported, get_recipe

    if registry is None:
        ensure_all_imported()
        resolver = get_recipe
    else:
        resolver = lambda name: registry[name]  # noqa: E731

    # Reserved-but-not-consumed guard (figure scope).  ``shared_aesthetic``
    # parses cleanly today but no aesthetic adapter consumes it yet; rather
    # than silently render with the recipe's own palette (a lie — the author
    # asked for a different aesthetic), fail loudly.  Mirrors the
    # PartitionedPanelSpec deferral below.  See docs/architecture_deep_dive.md
    # §7 item #6.
    if spec.shared_aesthetic is not None:
        raise NotImplementedError(
            "FigureSpec.shared_aesthetic is accepted by the schema but not "
            "yet consumed by the composition engine; supplying it would "
            "silently render the recipe's own aesthetic instead. Remove it "
            "until the aesthetic adapter lands (docs/spec_composition_layer.md "
            "§3.1)."
        )

    fig: Figure = plt.figure(figsize=spec.figsize, dpi=spec.dpi)
    axes_by_id: dict[str, Axes] = _build_axes(fig, spec)

    # First pass: render every panel into its assigned axes.
    for panel in spec.panels:
        if isinstance(panel, PartitionedPanelSpec):
            # Partition expansion is deferred to Sprint 1C-bis (see
            # docs/spec_composition_layer.md §2.5).  YAMLs that declare
            # partitions parse cleanly today but raise here so callers
            # get a deterministic NotImplementedError rather than a
            # silent skip.
            raise NotImplementedError(
                "PartitionedPanelSpec expansion is not yet implemented; "
                "use explicit PanelSpec entries for now."
            )
        ax = axes_by_id[panel.id]
        _render_panel(ax, panel, spec, resolver, data_files=data_files)

    # Second pass: link shared axes after every panel has data on it,
    # so matplotlib can compute consistent autoscale limits.
    _link_shared_axes(spec, axes_by_id)

    # Third pass: panel-letter overlay (A/B/C/...).
    _draw_panel_labels(spec, axes_by_id)

    # Suptitle.
    if spec.title:
        # 9.4 / 9.6 are part of the approved fontsize scale (style ratchet).
        fig.suptitle(spec.title, fontsize=9.4, y=0.995)

    out_path = Path(spec.output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    log.info("composed figure → %s", out_path)
    return out_path


def render_figure_yaml(
    yaml_path: str | Path,
    *,
    out_dir: Path = Path("figures"),
    registry: dict[str, Any] | None = None,
    data_files: dict[str, Path] | None = None,
) -> Path:
    """Load ``yaml_path`` and compose the resulting figure.

    If ``output_path`` is left at the schema default, the engine substitutes
    ``out_dir / f"{figure_id}.pdf"`` so the user can supply a single
    YAML file without also rewriting the output path.
    """
    import yaml

    yaml_path = Path(yaml_path)
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if data is None:
        raise ValueError(f"empty figure YAML: {yaml_path}")
    spec = FigureSpec(**data)

    if spec.output_path == Path("figures/figure_unnamed.pdf"):
        spec_dict = spec.model_dump()
        spec_dict["output_path"] = out_dir / f"{spec.figure_id}.pdf"
        spec = FigureSpec(**spec_dict)

    return compose_figure(spec, registry=registry, data_files=data_files)


def validate_figure_yaml(yaml_path: str | Path) -> list[str]:
    """Schema check + recipe-existence check.  Does NOT render.

    Returns a list of human-readable problem descriptions; an empty list
    means the spec is structurally valid and every panel's recipe can be
    resolved against the global registry.
    """
    import yaml

    from ..core.contract import ensure_all_imported, get_recipe

    ensure_all_imported()

    yaml_path = Path(yaml_path)
    problems: list[str] = []
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read YAML file: {exc}"]
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"YAML parse error: {exc}"]
    if data is None:
        return [f"empty figure YAML: {yaml_path}"]

    try:
        spec = FigureSpec(**data)
    except Exception as exc:  # noqa: BLE001 — pydantic ValidationError
        return [f"schema error: {exc}"]

    panel_ids = {
        p.id if isinstance(p, PanelSpec) else p.base_id
        for p in spec.panels
    }

    for panel in spec.panels:
        if isinstance(panel, PartitionedPanelSpec):
            try:
                get_recipe(panel.recipe)
            except KeyError:
                problems.append(
                    f"Panel {panel.base_id}: unknown recipe '{panel.recipe}'"
                )
            continue
        try:
            get_recipe(panel.recipe)
        except KeyError:
            problems.append(
                f"Panel {panel.id}: unknown recipe '{panel.recipe}'"
            )
        if panel.shared_axis_with and panel.shared_axis_with not in panel_ids:
            problems.append(
                f"Panel {panel.id}: shared_axis_with references unknown panel "
                f"'{panel.shared_axis_with}'"
            )

    return problems


# ─────────────────────────── private helpers ────────────────────────────


def _build_axes(fig: Figure, spec: FigureSpec) -> dict[str, Axes]:
    """Dispatch on ``spec.layout`` and build one axes per panel id."""
    layout = spec.layout
    axes_by_id: dict[str, Axes] = {}

    if isinstance(layout, GridLayout):
        gs = GridSpec(
            layout.rows,
            layout.cols,
            figure=fig,
            height_ratios=layout.height_ratios,
            width_ratios=layout.width_ratios,
            hspace=layout.hspace,
            wspace=layout.wspace,
        )
        # Auto-place panels in row-major order.
        for i, panel in enumerate(spec.panels):
            if isinstance(panel, PartitionedPanelSpec):
                continue
            r = i // layout.cols
            c = i % layout.cols
            if r >= layout.rows:
                raise ValueError(
                    f"GridLayout overflow: panel {panel.id!r} would be at "
                    f"row {r}, but layout has only {layout.rows} rows."
                )
            ax = fig.add_subplot(gs[r, c])
            axes_by_id[panel.id] = ax
        return axes_by_id

    if isinstance(layout, GridspecLayout):
        gs = GridSpec(
            layout.rows,
            layout.cols,
            figure=fig,
            hspace=layout.hspace,
            wspace=layout.wspace,
        )
        for panel in spec.panels:
            if isinstance(panel, PartitionedPanelSpec):
                continue
            if panel.grid_position is None:
                raise ValueError(
                    f"Panel {panel.id!r} in gridspec layout requires "
                    "grid_position=(row, col, row_span, col_span)."
                )
            r, c, rspan, cspan = panel.grid_position
            ax = fig.add_subplot(gs[r:r + rspan, c:c + cspan])
            axes_by_id[panel.id] = ax
        return axes_by_id

    if isinstance(layout, FreeformLayout):
        for panel in spec.panels:
            if isinstance(panel, PartitionedPanelSpec):
                continue
            if panel.freeform_bbox is None:
                raise ValueError(
                    f"Panel {panel.id!r} in freeform layout requires "
                    "freeform_bbox=(x, y, w, h)."
                )
            x, y, w, h = panel.freeform_bbox
            ax = fig.add_axes((x, y, w, h))
            axes_by_id[panel.id] = ax
        return axes_by_id

    raise TypeError(f"unsupported layout type: {type(layout).__name__}")


def _render_panel(
    ax: Axes,
    panel: PanelSpec,
    spec: FigureSpec,
    resolver: Any,
    *,
    data_files: dict[str, Path] | None,
) -> None:
    """Run the recipe's ``render(contract, ax=ax)`` on ``ax``.

    Data resolution today: only ``panel.data is None`` is supported, in
    which case the recipe's ``demo_contract()`` is rendered.  ``panel.data``
    and ``panel.aesthetic_overrides`` are accepted by the schema but the
    data-adapter / aesthetic-merge wiring (spec §2.3 ``DataSpec`` reuse and
    §3.1 aesthetic merge) is NOT yet implemented.  Supplying either field
    therefore raises ``NotImplementedError`` instead of silently rendering
    demo data with the recipe's default aesthetic — putting DEMO data into a
    published figure is the worst kind of silent-wrong-result.  Mirrors the
    PartitionedPanelSpec deferral in :func:`compose_figure`.  See
    docs/architecture_deep_dive.md §7 item #6.
    """
    if panel.data is not None:
        raise NotImplementedError(
            f"Panel {panel.id!r}: PanelSpec.data is accepted by the schema "
            "but not yet consumed by the composition engine; the recipe's "
            "demo_contract() would be rendered instead, silently substituting "
            "DEMO data for the file you supplied. Remove `data` until the "
            "data adapter lands (docs/spec_composition_layer.md §2.3)."
        )
    if panel.aesthetic_overrides:
        raise NotImplementedError(
            f"Panel {panel.id!r}: PanelSpec.aesthetic_overrides is accepted by "
            "the schema but not yet consumed by the composition engine; the "
            "overrides would be silently ignored. Remove `aesthetic_overrides` "
            "until the aesthetic-merge adapter lands "
            "(docs/spec_composition_layer.md §3.1)."
        )

    entry = resolver(panel.recipe)
    contract = entry.demo_contract()
    entry.render(contract, ax=ax)

    if panel.caption:
        existing = ax.get_xlabel()
        # 6.4 is part of the approved fontsize scale.
        ax.set_xlabel(
            f"{existing}\n{panel.caption}" if existing else panel.caption,
            fontsize=6.4,
        )


def _link_shared_axes(
    spec: FigureSpec,
    axes_by_id: dict[str, Axes],
) -> None:
    """Walk panel.shared_axis_with edges and call ``ax.sharey``."""
    for panel in spec.panels:
        if isinstance(panel, PartitionedPanelSpec):
            continue
        if panel.shared_axis_with is None:
            continue
        target_id = panel.shared_axis_with
        if target_id not in axes_by_id:
            log.warning(
                "panel %s: shared_axis_with refers to unknown panel %s; "
                "skipping link",
                panel.id, target_id,
            )
            continue
        if panel.id == target_id:
            log.warning("panel %s: shared_axis_with self-reference; skipping",
                        panel.id)
            continue
        target_ax = axes_by_id[target_id]
        ax = axes_by_id[panel.id]
        # Use sharey by default; the spec leaves x/y/both as a future
        # PanelSpec field, so we stick with y here (the most common case
        # documented in §3.1 of spec_composition_layer.md).
        ax.sharey(target_ax)


def _draw_panel_labels(
    spec: FigureSpec,
    axes_by_id: dict[str, Axes],
) -> None:
    """Place an A/B/C marker in the upper-left corner of each axes."""
    style = spec.panel_label_style
    if style == "none":
        return
    # Honour the only style we currently support; extensions plug in here.
    # 9.6 is part of the approved fontsize scale (style ratchet).
    weight = "bold" if "bold" in style else "normal"
    for panel in spec.panels:
        if isinstance(panel, PartitionedPanelSpec):
            continue
        ax = axes_by_id.get(panel.id)
        if ax is None:
            continue
        lx, ly = panel.label_position
        ax.text(
            lx,
            ly,
            panel.id,
            transform=ax.transAxes,
            fontsize=9.6,
            fontweight=weight,
            verticalalignment="top",
            horizontalalignment="left",
        )


__all__ = [
    "compose_figure",
    "render_figure_yaml",
    "validate_figure_yaml",
]
