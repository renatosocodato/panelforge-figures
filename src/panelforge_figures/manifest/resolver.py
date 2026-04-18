"""Manifest resolver: validate → load data → build contracts → render.

The resolver is the one-and-only bridge between a manifest file and the
modality recipes. It does not contain any domain logic — it dispatches.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from ..adapters import get_adapter, load_local_adapter
from ..core import (
    apply_base_style,
    export_figure,
    make_figure,
    make_panel_grid,
)
from ..core.contract import ensure_all_imported, get_recipe, registry_counts
from ..core.layout import panel_tag, suptitle_with_subtitle
from ..themes import apply_theme
from ..transforms import get_transform
from .schema import DataSpec, Manifest, PanelSpec, load_manifest

log = logging.getLogger(__name__)


# ─────────────────────────── data resolution ────────────────────────────

def resolve_panel_data(spec: DataSpec, search_root: str | Path = ".") -> Any:
    """Execute a panel's data pipeline: adapter → transforms → return object."""
    if spec.adapter.startswith("local."):
        adapter = load_local_adapter(spec.adapter[len("local."):], search_root=search_root)
    else:
        adapter = get_adapter(spec.adapter)

    adapter_kwargs: dict[str, Any] = dict(spec.options)
    if spec.columns is not None:
        adapter_kwargs.setdefault("columns", spec.columns)
    if spec.select is not None:
        adapter_kwargs.setdefault("select", spec.select)

    data = adapter(spec.source, **adapter_kwargs)
    for t in spec.transforms:
        name = t["name"]
        args = {k: v for k, v in t.items() if k != "name"}
        data = get_transform(name)(data, **args)
    return data


# ─────────────────────────── rendering ──────────────────────────────────

def _choose_grid(n: int) -> tuple[int, int]:
    if n <= 1:
        return 1, 1
    if n == 2:
        return 1, 2
    if n == 3:
        return 1, 3
    if n == 4:
        return 2, 2
    if n <= 6:
        return 2, 3
    if n <= 9:
        return 3, 3
    raise ValueError(f"more than 9 panels in a figure is not supported (got {n})")


def _call_recipe_on_ax(panel: PanelSpec, data: Any, ax) -> None:
    entry = get_recipe(panel.recipe)
    # Recipes accept either a pydantic contract or positional data; prefer contract.
    try:
        contract = entry.contract.model_validate(data) if hasattr(entry.contract, "model_validate") else data
    except Exception:
        # If validation fails (e.g., contract expects structured fields and we
        # have a DataFrame), pass the raw data; the recipe itself may coerce.
        contract = data
    entry.render(contract, ax=ax, **panel.options)


def render_manifest(
    manifest: Manifest | str | Path,
    *,
    search_root: str | Path = ".",
    dry_run: bool = False,
) -> list[Path]:
    """Render every figure in the manifest; return output paths.

    `dry_run=True` skips the filesystem write and returns a list of the paths
    that *would* be written (useful for validation).
    """
    ensure_all_imported()
    m = manifest if isinstance(manifest, Manifest) else load_manifest(manifest)
    apply_base_style()
    apply_theme(m.theme)

    produced: list[Path] = []
    for fig_spec in m.figures:
        nrows, ncols = _choose_grid(len(fig_spec.panels))
        fig = make_figure(size=fig_spec.size)
        gs = make_panel_grid(fig, nrows, ncols)
        for i, panel in enumerate(fig_spec.panels):
            r, c = divmod(i, ncols)
            ax = fig.add_subplot(gs[r, c])
            if panel.title:
                ax.set_title(panel.title)
            data = resolve_panel_data(panel.data, search_root=search_root)
            _call_recipe_on_ax(panel, data, ax)
            panel_tag(ax, panel.id)
        if fig_spec.suptitle:
            suptitle_with_subtitle(fig, fig_spec.suptitle, fig_spec.subtitle)
        export = fig_spec.export or m.export
        if dry_run:
            produced.append(Path(export.outdir) / f"{fig_spec.id}.pdf")
            plt.close(fig)
            continue
        saved = export_figure(
            fig,
            stem=fig_spec.id,
            formats=export.formats,
            dpi=export.dpi,
            outdir=export.outdir,
        )
        produced.extend(saved)
        plt.close(fig)
    log.info(
        "render_manifest: produced %d files; registry=%s",
        len(produced),
        registry_counts(),
    )
    return produced


def validate_manifest(
    manifest: Manifest | str | Path,
    *,
    search_root: str | Path = ".",
    check_data: bool = True,
) -> list[str]:
    """Validate a manifest: schema + recipes exist + (optional) data loads.

    Returns a list of human-readable problems. Empty list == all-good.
    """
    ensure_all_imported()
    m = manifest if isinstance(manifest, Manifest) else load_manifest(manifest)
    problems: list[str] = []
    for fig in m.figures:
        for panel in fig.panels:
            try:
                get_recipe(panel.recipe)
            except KeyError:
                problems.append(f"[{fig.id}:{panel.id}] unknown recipe: {panel.recipe}")
                continue
            if check_data:
                try:
                    resolve_panel_data(panel.data, search_root=search_root)
                except Exception as exc:
                    problems.append(f"[{fig.id}:{panel.id}] data load failed: {exc}")
    return problems
