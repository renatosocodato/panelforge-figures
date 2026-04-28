"""Shared sub-contracts for the `grant_and_conceptual` modality.

Pioneered by the `cytoskeletal_morphometry_companion` Wave 4 pack. The
sub-contracts here cover **narrative cascades** (synthesis-figure
primitives that integrate multi-stage causal stories with figure
cross-references and inline statistics).

Future packs that add conceptual / synthesis figures can extend
this module.
"""

from __future__ import annotations

from ...core import RecipeContract


class CascadeStage(RecipeContract):
    """One stage in a multi-stage narrative cascade.

    Used by `narrative_cascade_river_with_xrefs` (W4.2 of the
    cytoskeletal_morphometry_companion pack). Each stage carries an
    inline figure cross-reference (`Fig 2A`, `Fig 4C`, ...) and
    an optional p-value summary.
    """
    label: str                                   # e.g. "territory reorganization"
    figure_xref: str | None = None               # e.g. "Fig 2A"
    p_value: float | None = None
    summary: str | None = None                   # short claim text


class CascadeTransition(RecipeContract):
    """Edge from one cascade stage to the next.

    Used by `narrative_cascade_river_with_xrefs` (W4.2). Allows
    branch-points where the cascade splits (e.g. into 'buffered'
    vs 'confinement-facing' regimes).
    """
    from_stage: str
    to_stage: str
    weight: float = 1.0                          # ribbon thickness
    label: str | None = None                     # optional edge annotation
