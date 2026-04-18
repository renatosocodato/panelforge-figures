"""Pydantic schema for `figures.manifest.yaml`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class DataSpec(BaseModel):
    """How a panel sources its data."""

    source: str | Any                          # path string or in-memory object
    adapter: str = "tabular"                   # registry name, or "local.<name>"
    options: dict[str, Any] = Field(default_factory=dict)
    columns: dict[str, str] | None = None      # adapter-level rename
    select: list[str] | None = None
    transforms: list[dict[str, Any]] = Field(default_factory=list)


class PanelSpec(BaseModel):
    id: str                                    # e.g. "A", "B"
    recipe: str                                # e.g. "rhogtpase_dynamics.phase_portrait_tristable"
    data: DataSpec
    title: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("recipe")
    @classmethod
    def _recipe_has_modality(cls, v: str) -> str:
        if "." not in v:
            raise ValueError(
                f"recipe {v!r} must be fully qualified as 'modality.recipe' "
                "(e.g. 'sensitivity_analysis.sobol_first_total_pair')"
            )
        return v


class ExportSpec(BaseModel):
    formats: list[Literal["pdf", "png", "svg"]] = ["pdf", "png"]
    outdir: str = "figures/outputs"
    dpi: int = 600


class FigureSpec(BaseModel):
    id: str
    recipe_family: str | None = None
    size: str = "single"
    suptitle: str | None = None
    subtitle: str | None = None
    panels: list[PanelSpec]
    export: ExportSpec | None = None


class Manifest(BaseModel):
    version: int = 1
    theme: str = "default"
    palette: str = "journal_neutral"
    catalog_fingerprint: str | None = None
    figures: list[FigureSpec]
    export: ExportSpec = Field(default_factory=ExportSpec)


def load_manifest(path: str | Path) -> Manifest:
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        raise ValueError(f"empty manifest: {path}")
    return Manifest.model_validate(data)
