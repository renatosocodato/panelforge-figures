"""Canonical bridge between two family vocabularies.

panelforge has two parallel notions of "family":

* The **rendered** :class:`~panelforge_figures.core.contract.RecipeFamily`
  enum — the geometry/quality-gate tag every registered recipe carries
  (``coef_forest``, ``split_violin``, ``volcano``, ``heatmap`` …). This is
  the value of ``RecipeMetadata.family``.
* The **analysis** vocabulary used by the power layer
  (:mod:`.power_families` / :mod:`.power`) and the data-driven recommender
  (:mod:`.family_recommender`): ``comparison``, ``factorial``,
  ``correlation``, ``proportion``, ``equivalence``, ``concordance``,
  ``distribution``, ``permutation``. These name an *inferential test*, not
  a plot geometry, and are what ``power_families.FAMILY_TO_FORMULA`` keys on.

Historically these vocabularies were almost entirely disjoint — only
``coef_forest`` appeared in both. As a result:

* ``figures power <recipe>`` passed the *rendered* ``RecipeFamily`` straight
  into :func:`power.compute_required_n`, which only understands *analysis*
  families, so it raised ``PowerError`` for ~18/19 families.
* :func:`family_recommender.recommend_families` emitted *analysis* family
  strings that ``find_matching_recipes`` (string-matching the rendered
  ``RecipeFamily``) could never match, producing phantom "recipe gaps".

This module is the single source of truth reconciling the two. Keep the two
dicts below in sync; everything else derives from them.
"""

from __future__ import annotations

__all__ = [
    "ANALYSIS_FAMILIES",
    "ANALYSIS_TO_RECIPE_FAMILIES",
    "RECIPE_FAMILY_TO_ANALYSIS",
    "analysis_family_for_recipe_family",
    "recipe_families_for_analysis_family",
]


# Analysis families that have a registered power method in
# :data:`power_families.FAMILY_TO_FORMULA`. Kept here (rather than imported)
# so this module has no import-time dependency on the heavy power layer.
ANALYSIS_FAMILIES: tuple[str, ...] = (
    "comparison",
    "factorial",
    "coef_forest",
    "correlation",
    "proportion",
    "equivalence",
    "concordance",
    "distribution",
    "permutation",
)


# ── analysis family → rendered RecipeFamily values ───────────────────────
#
# Maps each *analysis* family to the tuple of rendered ``RecipeFamily`` slug
# strings whose recipes operationalise that analysis. Used by the recommender
# so ``find_matching_recipes("comparison", …)`` can resolve to real recipes
# instead of always returning an empty list.
#
# ``RecipeFamily`` slugs are spelled as plain strings (rather than importing
# the enum) so this module stays cheap to import; a unit test asserts every
# slug here is a real ``RecipeFamily`` member.
ANALYSIS_TO_RECIPE_FAMILIES: dict[str, tuple[str, ...]] = {
    # two-group / multi-group mean comparison
    "comparison": ("split_violin", "ridge_by_group", "timecourse_hierarchical_ci"),
    # factorial / interaction designs → coefficient-forest summaries
    "factorial": ("coef_forest",),
    # regression / ANOVA coefficient summaries (already a RecipeFamily)
    "coef_forest": ("coef_forest",),
    # bivariate association
    "correlation": ("scatter_collapse", "heatmap"),
    # binary / categorical outcome modelling
    "proportion": ("diagnostic_curve",),
    # differential-expression style many-comparison plots
    "distribution": ("volcano",),
    # the remaining nonparametric analysis families have power methods but
    # no dedicated rendered family yet — they are intentionally gap-only.
    "equivalence": (),
    "concordance": (),
    "permutation": (),
}


# ── rendered RecipeFamily value → analysis family ────────────────────────
#
# The reverse direction, used by the power CLI to translate a recipe's
# rendered ``RecipeFamily`` into the analysis family whose power formula
# applies. Rendered families absent from this dict (decorative / conceptual
# geometries such as ``conceptual``, ``flow``, ``gantt``, ``matrix``,
# ``contour``, ``radar``, ``phase_portrait``, ``bifurcation``,
# ``hysteresis_loop``, ``sobol_bar``, ``ladder``) have **no** defined power
# analysis; the CLI reports that cleanly instead of crashing.
RECIPE_FAMILY_TO_ANALYSIS: dict[str, str] = {
    "coef_forest": "coef_forest",
    "split_violin": "comparison",
    "ridge_by_group": "comparison",
    "timecourse_hierarchical_ci": "comparison",
    "scatter_collapse": "correlation",
    "heatmap": "correlation",
    "diagnostic_curve": "proportion",
    "volcano": "distribution",
}


def analysis_family_for_recipe_family(recipe_family: str) -> str | None:
    """Return the analysis family for a rendered ``RecipeFamily`` slug.

    Returns ``None`` when the rendered family has no defined power analysis
    (decorative / conceptual geometries). Callers should surface a clear
    "power analysis is not defined for family <X>" message rather than
    attempting a power computation.
    """
    return RECIPE_FAMILY_TO_ANALYSIS.get(recipe_family)


def recipe_families_for_analysis_family(analysis_family: str) -> tuple[str, ...]:
    """Return rendered ``RecipeFamily`` slugs for an analysis family.

    If ``analysis_family`` is already a rendered ``RecipeFamily`` slug (e.g.
    ``coef_forest``, ``volcano``), it resolves to itself plus any siblings.
    Unknown families resolve to a single-element tuple containing the input,
    so existing string-equality matching still works for any rendered family
    not enumerated here.
    """
    if analysis_family in ANALYSIS_TO_RECIPE_FAMILIES:
        return ANALYSIS_TO_RECIPE_FAMILIES[analysis_family]
    return (analysis_family,)
