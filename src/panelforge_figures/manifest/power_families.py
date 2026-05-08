"""Family-specific power-analysis formulas — Elevation 4 (v2.3.0).

Each panelforge ``RecipeFamily`` maps to one or more closed-form
(parametric) or simulation (nonparametric) power formulas.  This module
hides the math so :mod:`manifest.power` can expose a clean
``compute_power`` / ``compute_required_n`` API to the rest of the
codebase and the CLI.

Design notes
------------

* Heavy numerical dependencies (``statsmodels``, ``scipy``, ``numpy``)
  are **lazy-imported inside method bodies**.  Many panelforge users
  never touch power analysis; we refuse to drag those installs into the
  base distribution.
* Each formula advertises its native ``default_effect_size_units`` so
  the manifest layer can label result tables correctly (Cohen's d, f,
  w, Pearson r, or generic standardized effect).
* ``MonteCarloBootstrapFormula`` is the catch-all for nonparametric
  families (equivalence, concordance, distribution, permutation).  It
  uses a Mann-Whitney-U test against a planted location shift as the
  canonical reference; downstream callers can substitute family-tuned
  generators in a future sprint.
* :func:`resolve_family_method` returns ``(PowerMethod, PowerFormula)``.
  Build-A's ``manifest.power`` defines the :class:`PowerMethod` enum;
  we soft-import it so this module still parses if Build-A's file has
  not landed yet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "PowerFormula",
    "TTestFormula",
    "OneWayANOVAFormula",
    "TwoWayANOVAFormula",
    "CorrelationFormula",
    "ChiSquareFormula",
    "MonteCarloBootstrapFormula",
    "FAMILY_TO_FORMULA",
    "resolve_family_method",
]


# ───────────────────────── Base class ─────────────────────────


@dataclass(frozen=True)
class PowerFormula:
    """Abstract base — subclasses provide ``compute_power`` + ``required_n``.

    Subclasses are frozen dataclasses so they are cheap to instantiate
    and hashable for cache keys.  The ``default_effect_size_units``
    field labels the natural effect-size scale of the formula (e.g.
    ``"cohens_d"`` for the t-test); the manifest layer surfaces this
    string in result tables so downstream readers know which scale a
    numerical effect size is on.
    """

    default_effect_size_units: str

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None,
        df_den: int | None,
        n_groups: int,
    ) -> float:
        raise NotImplementedError

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None,
        df_den: int | None,
        n_groups: int,
        montecarlo_iterations: int,
    ) -> int:
        raise NotImplementedError


# ─────────────────────── Parametric formulas ───────────────────────


@dataclass(frozen=True)
class TTestFormula(PowerFormula):
    """Two-sample independent t-test power.

    Uses :func:`statsmodels.stats.power.tt_ind_solve_power` when
    ``statsmodels`` is installed; falls back to the standard
    normal-approximation otherwise.

    Effect size: Cohen's d.
    """

    default_effect_size_units: str = "cohens_d"

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 2,
    ) -> float:
        try:
            from statsmodels.stats.power import tt_ind_solve_power

            return float(
                tt_ind_solve_power(
                    effect_size=effect_size,
                    nobs1=n_per_group,
                    alpha=alpha,
                    ratio=1.0,
                    alternative="two-sided",
                )
            )
        except ImportError:
            # Normal approximation: power ≈ Φ(d·√(n/2) − z_{α/2}).
            from math import sqrt
            from statistics import NormalDist

            z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
            ncp = effect_size * sqrt(n_per_group / 2.0)
            return float(NormalDist().cdf(ncp - z_alpha))

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 2,
        montecarlo_iterations: int = 0,
    ) -> int:
        try:
            from statsmodels.stats.power import tt_ind_solve_power

            n = tt_ind_solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=power_target,
                ratio=1.0,
                alternative="two-sided",
                nobs1=None,
            )
            return int(math.ceil(n))
        except ImportError:
            # Normal approximation: n_per_group = 2·((z_{α/2} + z_β) / d)².
            from math import ceil
            from statistics import NormalDist

            z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
            z_beta = NormalDist().inv_cdf(power_target)
            n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
            return int(ceil(n))


@dataclass(frozen=True)
class OneWayANOVAFormula(PowerFormula):
    """One-way ANOVA power.

    Uses :class:`statsmodels.stats.power.FTestAnovaPower` with
    ``df_num = n_groups − 1``.  Closed-form fallback is *not* available
    — if ``statsmodels`` is missing we raise a clear instruction.

    Effect size: Cohen's f.
    """

    default_effect_size_units: str = "cohens_f"

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 2,
    ) -> float:
        try:
            from statsmodels.stats.power import FTestAnovaPower

            n_total = n_per_group * n_groups
            return float(
                FTestAnovaPower().power(
                    effect_size=effect_size,
                    nobs=n_total,
                    alpha=alpha,
                    k_groups=n_groups,
                )
            )
        except ImportError as exc:
            raise RuntimeError(
                "statsmodels required for ANOVA power; "
                "install with `pip install statsmodels`"
            ) from exc

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 2,
        montecarlo_iterations: int = 0,
    ) -> int:
        try:
            from statsmodels.stats.power import FTestAnovaPower

            n_total = FTestAnovaPower().solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=power_target,
                k_groups=n_groups,
            )
            return int(math.ceil(n_total / n_groups))
        except ImportError as exc:
            raise RuntimeError(
                "statsmodels required for ANOVA power"
            ) from exc


@dataclass(frozen=True)
class TwoWayANOVAFormula(PowerFormula):
    """Two-way (factorial) ANOVA power.

    For a 2×2 factorial there are 4 cells, ``df_num = 1`` for each main
    effect and the interaction, and ``df_den = n_total − 4``.  The
    interaction shares the F formula with the main effects but uses
    different degrees of freedom — callers can override ``df_num`` /
    ``df_den`` for non-2×2 designs.

    Effect size: Cohen's f for the term of interest.
    """

    default_effect_size_units: str = "cohens_f"

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None = 1,
        df_den: int | None = None,
        n_groups: int = 4,
    ) -> float:
        try:
            from statsmodels.stats.power import FTestPower

            n_total = n_per_group * 4
            df_num_eff = df_num if df_num is not None else 1
            df_den_eff = df_den if df_den is not None else max(n_total - 4, 1)
            return float(
                FTestPower().power(
                    effect_size=effect_size,
                    df_num=df_num_eff,
                    df_denom=df_den_eff,
                    alpha=alpha,
                )
            )
        except ImportError as exc:
            raise RuntimeError(
                "statsmodels required for two-way ANOVA power"
            ) from exc

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None = 1,
        df_den: int | None = None,
        n_groups: int = 4,
        montecarlo_iterations: int = 0,
    ) -> int:
        try:
            from statsmodels.stats.power import FTestPower
        except ImportError as exc:
            raise RuntimeError(
                "statsmodels required for two-way ANOVA power"
            ) from exc

        df_num_eff = df_num if df_num is not None else 1

        def _power_at_n(n_per_cell: float) -> float:
            n_total = n_per_cell * 4
            return float(
                FTestPower().power(
                    effect_size=effect_size,
                    df_num=df_num_eff,
                    df_denom=max(n_total - 4, 1),
                    alpha=alpha,
                )
            )

        # Bracketed root-find first; fall back to linear scan if the
        # solver fails (e.g. effect_size below detectable threshold).
        try:
            from scipy.optimize import brentq

            root = brentq(
                lambda n: _power_at_n(n) - power_target, 2.0, 10000.0
            )
            return int(math.ceil(root))
        except (ImportError, ValueError):
            for n in range(2, 10000):
                if _power_at_n(n) >= power_target:
                    return n
            return 10000


@dataclass(frozen=True)
class CorrelationFormula(PowerFormula):
    """Power for Pearson correlation via Fisher's z-transformation.

    Closed-form: ``n − 3 = ((z_{α/2} + z_β) / atanh(r))²``.  No external
    dependency required.

    Effect size: Pearson r.
    """

    default_effect_size_units: str = "pearson_r"

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 1,
    ) -> float:
        from math import atanh, sqrt
        from statistics import NormalDist

        if n_per_group <= 3:
            return 0.0
        z_r = atanh(effect_size)
        se = 1.0 / sqrt(n_per_group - 3)
        z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
        return float(NormalDist().cdf((z_r / se) - z_alpha))

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 1,
        montecarlo_iterations: int = 0,
    ) -> int:
        from math import atanh, ceil
        from statistics import NormalDist

        z_r = atanh(effect_size)
        z_alpha = NormalDist().inv_cdf(1 - alpha / 2)
        z_beta = NormalDist().inv_cdf(power_target)
        # n − 3 = ((z_{α/2} + z_β) / z_r)²
        n = ((z_alpha + z_beta) / z_r) ** 2 + 3
        return int(ceil(n))


@dataclass(frozen=True)
class ChiSquareFormula(PowerFormula):
    """Chi-square goodness-of-fit / independence power.

    Uses :class:`statsmodels.stats.power.GofChisquarePower`.  Number of
    bins is derived from ``df_num + 1`` (1 d.f. → 2×2 table, etc.).

    Effect size: Cohen's w.
    """

    default_effect_size_units: str = "cohens_w"

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None = 1,
        df_den: int | None = None,
        n_groups: int = 2,
    ) -> float:
        try:
            from statsmodels.stats.power import GofChisquarePower

            n_total = n_per_group * n_groups
            df_num_eff = df_num if df_num is not None else 1
            return float(
                GofChisquarePower().power(
                    effect_size=effect_size,
                    nobs=n_total,
                    alpha=alpha,
                    n_bins=df_num_eff + 1,
                )
            )
        except ImportError as exc:
            raise RuntimeError(
                "statsmodels required for chi-square power"
            ) from exc

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None = 1,
        df_den: int | None = None,
        n_groups: int = 2,
        montecarlo_iterations: int = 0,
    ) -> int:
        try:
            from statsmodels.stats.power import GofChisquarePower

            df_num_eff = df_num if df_num is not None else 1
            n_total = GofChisquarePower().solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=power_target,
                n_bins=df_num_eff + 1,
            )
            return int(math.ceil(n_total / max(n_groups, 1)))
        except ImportError as exc:
            raise RuntimeError(
                "statsmodels required for chi-square power"
            ) from exc


# ─────────────────────── Nonparametric formula ───────────────────────


@dataclass(frozen=True)
class MonteCarloBootstrapFormula(PowerFormula):
    """Generic nonparametric Monte-Carlo power simulation.

    Procedure: for each candidate ``n``, run ``montecarlo_iterations``
    synthetic two-sample experiments with the planted effect size,
    apply a Mann-Whitney-U test, and count the fraction that achieve
    ``p < alpha``.  That fraction *is* the estimated power.

    For the headline ``compute_power`` API we use a fixed 1000-iter
    budget for snappy CLI output; ``required_n`` exposes the full
    ``montecarlo_iterations`` knob so callers who care about Monte-Carlo
    error can crank it up.

    Effect size: standardized location shift (interpretable on the same
    scale as Cohen's d for unit-variance Normal samples).
    """

    default_effect_size_units: str = "standardized"

    def compute_power(
        self,
        *,
        effect_size: float,
        alpha: float,
        n_per_group: int,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 2,
    ) -> float:
        try:
            import numpy as np
            from scipy import stats as scipy_stats
        except ImportError as exc:
            raise RuntimeError(
                "numpy + scipy required for Monte-Carlo bootstrap power"
            ) from exc

        rng = np.random.default_rng(0)
        n_iter = 1000  # default for compute_power; required_n bumps this
        n_sig = 0
        for _ in range(n_iter):
            x = rng.normal(0.0, 1.0, n_per_group)
            y = rng.normal(effect_size, 1.0, n_per_group)
            _, p = scipy_stats.mannwhitneyu(x, y, alternative="two-sided")
            if p < alpha:
                n_sig += 1
        return n_sig / n_iter

    def required_n(
        self,
        *,
        effect_size: float,
        alpha: float,
        power_target: float,
        df_num: int | None = None,
        df_den: int | None = None,
        n_groups: int = 2,
        montecarlo_iterations: int = 1000,
    ) -> int:
        try:
            import numpy as np
            from scipy import stats as scipy_stats
        except ImportError as exc:
            raise RuntimeError(
                "numpy + scipy required for Monte-Carlo bootstrap power"
            ) from exc

        def _achieved_power(n: int) -> float:
            rng = np.random.default_rng(0)
            n_sig = 0
            for _ in range(montecarlo_iterations):
                x = rng.normal(0.0, 1.0, n)
                y = rng.normal(effect_size, 1.0, n)
                _, p = scipy_stats.mannwhitneyu(
                    x, y, alternative="two-sided"
                )
                if p < alpha:
                    n_sig += 1
            return n_sig / montecarlo_iterations

        # Binary search for smallest n with achieved power ≥ target.
        lo, hi = 2, 5000
        while lo < hi:
            mid = (lo + hi) // 2
            if _achieved_power(mid) >= power_target:
                hi = mid
            else:
                lo = mid + 1
        return lo


# ─────────────────── Family → Formula mapping ───────────────────


# Maps a panelforge ``RecipeFamily`` slug to the canonical
# ``(PowerMethod-string, PowerFormula-class)`` pair.  The string side
# matches Build-A's :class:`PowerMethod` enum values verbatim.
FAMILY_TO_FORMULA: dict[str, tuple[str, type[PowerFormula]]] = {
    # parametric
    "comparison": ("closed_form_t_test", TTestFormula),
    "factorial": ("closed_form_two_way_anova", TwoWayANOVAFormula),
    "coef_forest": ("closed_form_two_way_anova", TwoWayANOVAFormula),
    "correlation": ("closed_form_correlation", CorrelationFormula),
    "proportion": ("closed_form_chi_square", ChiSquareFormula),
    # nonparametric
    "equivalence": ("monte_carlo_bootstrap", MonteCarloBootstrapFormula),
    "concordance": ("monte_carlo_bootstrap", MonteCarloBootstrapFormula),
    "distribution": ("monte_carlo_bootstrap", MonteCarloBootstrapFormula),
    "permutation": ("monte_carlo_bootstrap", MonteCarloBootstrapFormula),
}


def resolve_family_method(family: str, *, n_groups: int = 2):
    """Return ``(PowerMethod, PowerFormula)`` for a recipe family.

    Special cases
    -------------
    * ``coef_forest`` with ``n_groups == 2`` is a t-test, not an ANOVA
      (a 2-cell forest reduces to pairwise comparison).

    Raises
    ------
    KeyError
        If the family has no registered formula.  The caller (typically
        :mod:`manifest.power`) should catch this and re-raise as a
        ``PowerError`` with user-facing context.
    """
    if family == "coef_forest" and n_groups == 2:
        method_str: str = "closed_form_t_test"
        cls: type[PowerFormula] = TTestFormula
    elif family in FAMILY_TO_FORMULA:
        method_str, cls = FAMILY_TO_FORMULA[family]
    else:
        raise KeyError(f"family {family!r} has no power formula")

    # Soft-import Build-A's PowerMethod enum for type consistency; if
    # power.py has not landed yet (or fails to import for any reason)
    # we fall back to the raw string so this module still parses.
    try:
        from .power import PowerMethod

        return PowerMethod(method_str), cls()
    except (ImportError, AttributeError):
        return method_str, cls()
