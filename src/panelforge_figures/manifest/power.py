"""Adaptive power analysis for panelforge recipes.

Given a recipe's :class:`StatisticalContract` plus a target effect size,
alpha, and desired power, compute the required sample size per group or
per cell.

Parametric recipes (t-test, ANOVA, correlation, chi-square, proportion)
use closed-form formulas via :mod:`statsmodels.stats.power`. Nonparametric
recipes (TOST equivalence, KS / AD / MWU distribution tests, concordance,
explicit permutation) use Monte Carlo simulation with binary search over
``n``.

The ``compute_power`` and ``compute_required_n`` entrypoints are stable
public APIs; family-specific formulas live in :mod:`.power_families`
(written by Build-B in the same Elevation 4 swarm) and are imported lazily
so this module loads cleanly even before that sibling module exists.

CLI integration is provided by :mod:`.cli` (Build-C in the same swarm) via
``figures power <recipe> --effect-size 0.3 --alpha 0.05 --power 0.8``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "PARAMETRIC_FAMILIES",
    "NONPARAMETRIC_FAMILIES",
    "PowerEstimate",
    "PowerError",
    "PowerMethod",
    "compute_power",
    "compute_required_n",
]


class PowerMethod(StrEnum):
    """How power was computed.

    Closed-form methods come from :mod:`statsmodels.stats.power` and
    return power exactly given the standard test assumptions. Monte Carlo
    methods simulate the test under the alternative and report empirical
    rejection rate; their reported power has roughly +/- 0.02 sampling
    uncertainty at 1000 iterations.
    """

    closed_form_t_test = "closed_form_t_test"
    closed_form_one_way_anova = "closed_form_one_way_anova"
    closed_form_two_way_anova = "closed_form_two_way_anova"
    closed_form_correlation = "closed_form_correlation"
    closed_form_chi_square = "closed_form_chi_square"
    closed_form_proportion = "closed_form_proportion"
    monte_carlo_bootstrap = "monte_carlo_bootstrap"
    monte_carlo_permutation = "monte_carlo_permutation"
    refused_no_method = "refused_no_method"


class PowerError(RuntimeError):
    """Raised when power analysis cannot be completed.

    Common causes:

    * The recipe family has no registered closed-form or Monte Carlo
      method (i.e. it is not in ``PARAMETRIC_FAMILIES`` or
      ``NONPARAMETRIC_FAMILIES``).
    * Effect-size, alpha, or power_target arguments are out of range.
    * The Monte Carlo binary search failed to bracket the target power
      within the configured iteration budget.
    """


@dataclass(frozen=True)
class PowerEstimate:
    """Result of a power analysis.

    All fields are JSON-serializable via :meth:`to_dict`. ``method`` is a
    :class:`PowerMethod` member (its ``.value`` is the string id used by
    the CLI). ``required_n_per_group`` is rounded *up* so that achieved
    power is guaranteed to be at least ``power_target``.

    For ANOVA-family methods, ``df_num`` and ``df_den`` carry the
    numerator / denominator degrees of freedom used by the F distribution
    in the closed-form computation; they are ``None`` for t-tests,
    correlations, proportions, and Monte Carlo paths.
    """

    recipe_full_name: str
    family: str
    method: PowerMethod
    effect_size: float
    effect_size_units: str
    alpha: float
    power_target: float
    required_n_per_group: int
    required_n_total: int
    df_num: int | None
    df_den: int | None
    notes: tuple[str, ...]
    montecarlo_iterations: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of all fields.

        ``method`` is converted to its string value so the result can
        round-trip through ``json.dumps`` / ``json.loads`` without a
        custom encoder. ``notes`` is converted from a tuple to a list
        for the same reason.
        """
        return {
            "recipe_full_name": self.recipe_full_name,
            "family": self.family,
            "method": self.method.value,
            "effect_size": self.effect_size,
            "effect_size_units": self.effect_size_units,
            "alpha": self.alpha,
            "power_target": self.power_target,
            "required_n_per_group": self.required_n_per_group,
            "required_n_total": self.required_n_total,
            "df_num": self.df_num,
            "df_den": self.df_den,
            "notes": list(self.notes),
            "montecarlo_iterations": self.montecarlo_iterations,
        }


# Family classifications: which *analysis* family uses which power method.
#
# IMPORTANT: these are *analysis*-vocabulary names (``comparison``,
# ``factorial``, ``correlation``, ``proportion``, ``equivalence`` …), which
# name an inferential test — they are deliberately distinct from the
# rendered ``RecipeFamily`` enum (``coef_forest``, ``split_violin``,
# ``volcano`` …) that recipes carry as ``RecipeMetadata.family``. The two
# vocabularies are reconciled in :mod:`.family_bridge`; callers holding a
# rendered ``RecipeFamily`` (e.g. the ``figures power`` CLI) must translate
# via ``family_bridge.analysis_family_for_recipe_family`` *before* calling
# into this module. ``coef_forest`` is the single slug that appears in both
# vocabularies. The classification is used by ``compute_required_n`` to
# decide between closed-form lookup and Monte Carlo simulation, and to
# decide whether to attach the +/- 0.02 uncertainty caveat to the returned
# PowerEstimate's ``notes`` tuple.
PARAMETRIC_FAMILIES: tuple[str, ...] = (
    "comparison",          # 2-group t-test family
    "factorial",           # 2x2 ANOVA family
    "coef_forest",         # one-way / two-way ANOVA marker plots
    "correlation",         # Pearson / Spearman scatter family
    "proportion",          # binomial / chi-square family
)

NONPARAMETRIC_FAMILIES: tuple[str, ...] = (
    "equivalence",         # TOST family --- bootstrap simulation
    "concordance",         # Kendall's W, ICC --- simulation
    "distribution",        # KS, AD, MWU --- simulation
    "permutation",         # explicit permutation-test family
)


def _validate_alpha_power(alpha: float, power_target: float) -> None:
    """Validate alpha and power_target are in their open unit intervals."""
    if not 0.0 < alpha < 1.0:
        raise PowerError(
            f"alpha={alpha!r} must be in the open interval (0, 1)"
        )
    if not 0.0 < power_target < 1.0:
        raise PowerError(
            f"power_target={power_target!r} must be in the open "
            "interval (0, 1)"
        )


def _validate_effect_size(effect_size: float) -> None:
    """Validate the effect size is finite and nonzero.

    Zero effect size implies infinite required ``n``; negative effect
    sizes are silently treated as their absolute value at the formula
    layer (Cohen's d, f, r, w are all conventionally non-negative for
    power analysis).
    """
    if not math.isfinite(effect_size):
        raise PowerError(
            f"effect_size={effect_size!r} must be finite"
        )
    if effect_size == 0.0:
        raise PowerError(
            "effect_size=0 implies infinite n; no power analysis possible"
        )


def compute_power(
    *,
    family: str,
    effect_size: float,
    alpha: float,
    n_per_group: int,
    df_num: int | None = None,
    df_den: int | None = None,
    n_groups: int = 2,
) -> float:
    """Compute the achieved power for a fixed sample size.

    Parameters
    ----------
    family
        A recipe family name; must be a member of either
        :data:`PARAMETRIC_FAMILIES` or :data:`NONPARAMETRIC_FAMILIES`.
    effect_size
        Standardized effect size in the units appropriate to the family
        (Cohen's d for comparison, Cohen's f for factorial / ANOVA,
        Pearson r for correlation, Cohen's w for chi-square, h for
        proportion, raw effect for nonparametric simulation).
    alpha
        Significance level, in the open interval (0, 1).
    n_per_group
        Sample size per group (or per cell, for factorial designs).
        Must be a positive integer.
    df_num, df_den
        Numerator / denominator degrees of freedom for ANOVA-family
        formulas; ignored otherwise.
    n_groups
        Number of groups (2 for t-test; ``len(levels)`` for one-way
        ANOVA; product of factor levels for factorial).

    Returns
    -------
    float
        Achieved power in [0, 1].

    Raises
    ------
    PowerError
        If ``family`` has no registered method or ``n_per_group`` is
        non-positive.
    """
    if n_per_group <= 0:
        raise PowerError(
            f"n_per_group={n_per_group!r} must be a positive integer"
        )
    _validate_alpha_power(alpha, power_target=0.5)  # power_target unused here
    _validate_effect_size(effect_size)

    # Lazy import: Build-B's module fills in the concrete formulas. We
    # want this module importable on its own so the type surface is
    # available before the family layer lands.
    from .power_families import resolve_family_method

    _method, formula = resolve_family_method(family, n_groups=n_groups)
    return formula.compute_power(
        effect_size=effect_size,
        alpha=alpha,
        n_per_group=n_per_group,
        df_num=df_num,
        df_den=df_den,
        n_groups=n_groups,
    )


def compute_required_n(
    *,
    recipe_full_name: str,
    family: str,
    effect_size: float,
    alpha: float = 0.05,
    power_target: float = 0.80,
    df_num: int | None = None,
    df_den: int | None = None,
    n_groups: int = 2,
    montecarlo_iterations: int = 1000,
    effect_size_units: str | None = None,
) -> PowerEstimate:
    """Compute the smallest ``n_per_group`` achieving ``power_target``.

    Parameters
    ----------
    recipe_full_name
        The dotted ``modality.recipe`` name; recorded on the returned
        :class:`PowerEstimate` for provenance and CLI display.
    family
        Recipe family. Must be in :data:`PARAMETRIC_FAMILIES` or
        :data:`NONPARAMETRIC_FAMILIES`; otherwise
        :class:`PowerError` is raised.
    effect_size
        Target effect size (units depend on family --- see
        :func:`compute_power`).
    alpha
        Significance level. Default 0.05.
    power_target
        Desired statistical power. Default 0.80.
    df_num, df_den
        Degrees of freedom for ANOVA-family computations.
    n_groups
        Number of groups / cells. Used both for total-N reporting and
        to dispatch within a family (e.g. factorial vs one-way).
    montecarlo_iterations
        Iteration budget for nonparametric Monte Carlo. Ignored for
        parametric families. Default 1000 yields roughly +/- 0.02 power
        uncertainty.
    effect_size_units
        Override the default effect-size unit string. If ``None``, the
        family formula's ``default_effect_size_units`` is used.

    Returns
    -------
    PowerEstimate
        With ``required_n_per_group`` rounded up to an integer.

    Algorithm
    ---------
    1. Validate alpha, power_target, effect_size.
    2. Confirm the family is known (parametric or nonparametric);
       raise :class:`PowerError` otherwise.
    3. Lazy-import the Build-B family formulas and resolve the method.
    4. Delegate the per-group ``n`` search to ``formula.required_n``
       (closed-form inversion for parametric, Monte Carlo binary search
       for nonparametric).
    5. Round up to integer and assemble the PowerEstimate, attaching a
       Monte Carlo uncertainty caveat if applicable.
    """
    _validate_alpha_power(alpha, power_target)
    _validate_effect_size(effect_size)

    is_parametric = family in PARAMETRIC_FAMILIES
    is_nonparametric = family in NONPARAMETRIC_FAMILIES
    if not (is_parametric or is_nonparametric):
        raise PowerError(
            f"family {family!r} not in PARAMETRIC_FAMILIES or "
            "NONPARAMETRIC_FAMILIES; no power method available"
        )

    notes: list[str] = []
    if is_nonparametric:
        notes.append(
            f"Monte Carlo simulation with {montecarlo_iterations} "
            "iterations; results have +/- 0.02 power uncertainty."
        )

    # Lazy import keeps this module loadable even if Build-B's
    # power_families module is not yet present at import time. The
    # families module is required at *call* time, however --- there is
    # no way to satisfy a power request without the formula layer.
    from .power_families import resolve_family_method

    method, formula = resolve_family_method(family, n_groups=n_groups)

    # The formula layer raises a bare RuntimeError when an optional
    # dependency (statsmodels/scipy, the `[power]` extra) is missing —
    # e.g. closed-form ANOVA / chi-square power. Translate it into the
    # documented PowerError so callers that follow the contract (the CLI
    # `power` command, library consumers) get a clean, catchable error
    # with an actionable install hint instead of an uncaught stacktrace.
    try:
        n = formula.required_n(
            effect_size=effect_size,
            alpha=alpha,
            power_target=power_target,
            df_num=df_num,
            df_den=df_den,
            n_groups=n_groups,
            montecarlo_iterations=montecarlo_iterations,
        )
    except PowerError:
        raise
    except RuntimeError as exc:
        raise PowerError(
            f"power analysis for family {family!r} is unavailable: {exc}. "
            f"Install the optional dependencies with: "
            f"pip install panelforge-figures[power]"
        ) from exc

    if not math.isfinite(n) or n <= 0:
        raise PowerError(
            f"required_n returned non-finite/non-positive value {n!r} "
            f"for family={family!r}, effect_size={effect_size!r}, "
            f"alpha={alpha!r}, power_target={power_target!r}"
        )

    units = effect_size_units or formula.default_effect_size_units
    n_per_group_int = int(math.ceil(n))
    n_total = n_per_group_int * max(n_groups, 1)
    mc_iters = montecarlo_iterations if is_nonparametric else 0

    return PowerEstimate(
        recipe_full_name=recipe_full_name,
        family=family,
        method=method,
        effect_size=effect_size,
        effect_size_units=units,
        alpha=alpha,
        power_target=power_target,
        required_n_per_group=n_per_group_int,
        required_n_total=n_total,
        df_num=df_num,
        df_den=df_den,
        notes=tuple(notes),
        montecarlo_iterations=mc_iters,
    )
