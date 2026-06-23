"""Statistical-contract audit pipeline.

This module is the AUDIT layer of the spec
(``docs/spec_statistical_contract.md``). Given a
:class:`~panelforge_figures.core.StatisticalContract` and a bound
:class:`pandas.DataFrame`, the public function
:func:`audit_recipe_against_data` walks the **13 rule functions** and
returns an :class:`AuditReport`.

The audit *never* raises; the caller decides what to do based on the
report's ``overall`` severity:

* ``"pass"``   — silent.
* ``"warn"``   — render proceeds; the report sidecar (``RENDER_REPORT.md``)
  carries a ``STATISTICAL WARNING`` block. (See Build-B for CLI surface.)
* ``"refuse"`` — the binding is dropped from the shortlist; downstream
  callers may raise :class:`StatisticalContractViolation` themselves.

Rule taxonomy
-------------
Each rule is a private function that returns ``AuditFinding | None``
(``None`` when the rule does not apply). The ``contract.refuses_when``
tuple lets per-recipe contracts **escalate** an otherwise-warn-class
finding into a refusal — used e.g. for the ``underpowered`` rule in the
``mixed_effects_models.two_way_anova_summary_plot`` worked example. Every
name in ``refuses_when`` must be one of the 13 rule ids below; that is
enforced at contract-construction time
(:class:`~panelforge_figures.core.StatisticalContract.__post_init__`
against :data:`~panelforge_figures.core.KNOWN_REFUSAL_RULES`), and this
module asserts at import time that its own registry matches that taxonomy
so the two cannot drift.

Rule names (the keys for ``refuses_when``):

============================== ===========
``underpowered``               default refuse
``non_normal_with_parametric_test``  default warn
``uncorrected_multiple_comparisons`` default refuse
``missing_paired_structure``    default refuse
``singular_design``             default refuse
``negative_in_non_negative``    default refuse
``unit_interval_violation``     default refuse
``non_integer_in_count``        default refuse
``excessive_missingness``       default warn
``tied_zero_inflated``          default warn
``cluster_imbalance``           default warn
``n_below_visualization_floor`` default refuse
``effect_size_units_undeclared`` default warn
============================== ===========
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from ..core import KNOWN_REFUSAL_RULES, StatisticalContract

__all__ = [
    "ALL_RULE_NAMES",
    "AuditFinding",
    "AuditReport",
    "Severity",
    "StatisticalContractViolation",
    "audit_recipe_against_data",
]


Severity = Literal["pass", "warn", "refuse"]
_SEVERITY_ORDER: dict[Severity, int] = {"pass": 0, "warn": 1, "refuse": 2}


# Default verdicts per rule (see spec §3 table).
_DEFAULT_VERDICT: dict[str, Severity] = {
    "underpowered": "refuse",
    "non_normal_with_parametric_test": "warn",
    "uncorrected_multiple_comparisons": "refuse",
    "missing_paired_structure": "refuse",
    "singular_design": "refuse",
    "negative_in_non_negative": "refuse",
    "unit_interval_violation": "refuse",
    "non_integer_in_count": "refuse",
    "excessive_missingness": "warn",
    "tied_zero_inflated": "warn",
    "cluster_imbalance": "warn",
    "n_below_visualization_floor": "refuse",
    "effect_size_units_undeclared": "warn",
}

ALL_RULE_NAMES: tuple[str, ...] = tuple(_DEFAULT_VERDICT)

# The contract layer (``core.statistical_contract``) validates every
# ``refuses_when`` entry against its own copy of this taxonomy
# (``KNOWN_REFUSAL_RULES``). Assert at import time that the two agree, so a
# rule added here but not mirrored there (or vice versa) fails loudly rather
# than letting contracts silently accept an id this module would never honour.
assert set(ALL_RULE_NAMES) == set(KNOWN_REFUSAL_RULES), (
    "statistical_audit rule registry has drifted from "
    "core.KNOWN_REFUSAL_RULES: "
    f"{set(ALL_RULE_NAMES) ^ set(KNOWN_REFUSAL_RULES)}"
)

# Tunable thresholds (centralised so tests can adjust if v2.1 makes them
# contract fields, per the risks/mitigations table in the spec).
_KS_P_THRESHOLD = 0.01
_DEFAULT_MISSINGNESS_THRESHOLD = 0.30
_ZERO_INFLATION_THRESHOLD = 0.40
_CLUSTER_IMBALANCE_RATIO = 5.0


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuditFinding:
    """One audit observation produced by a single rule."""

    rule_id: str
    severity: Severity
    message: str
    n_observed: int | None = None
    threshold: int | float | None = None


@dataclass(frozen=True)
class AuditReport:
    """Aggregate of every rule's verdict for a single (contract, data) pair."""

    recipe_full_name: str
    findings: tuple[AuditFinding, ...]
    overall: Severity  # max severity across findings


class StatisticalContractViolation(RuntimeError):
    """Raised when audit findings reach the ``refuse`` severity.

    This module never raises it itself — :func:`audit_recipe_against_data`
    always returns an :class:`AuditReport`. Callers (the render loop, the
    CLI verb) decide whether and when to lift a refused report to an
    exception.
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _numeric_columns(data: pd.DataFrame) -> list[str]:
    """Columns the rules treat as the substantive observation vector(s)."""
    return [
        c
        for c in data.columns
        if pd.api.types.is_numeric_dtype(data[c])
        and c not in {"subject_id", "cluster_id"}
    ]


def _all_numeric_values(data: pd.DataFrame) -> np.ndarray:
    """Concatenated 1-D float view of every numeric column. Drops NaNs."""
    cols = _numeric_columns(data)
    if not cols:
        return np.array([], dtype=float)
    arr = data[cols].to_numpy(dtype=float, copy=False).ravel()
    return arr[~np.isnan(arr)]


def _per_group_sizes(
    data: pd.DataFrame, group_column: str | None
) -> dict[str, int]:
    if group_column is None or group_column not in data.columns:
        # treat all rows as one synthetic group named "<all>"
        return {"<all>": len(data)}
    return {str(k): int(v) for k, v in data[group_column].value_counts().items()}


def _per_group_arrays(
    data: pd.DataFrame, group_column: str | None
) -> dict[str, np.ndarray]:
    """Per-group concatenated numeric values (NaNs removed)."""
    if group_column is None or group_column not in data.columns:
        return {"<all>": _all_numeric_values(data)}
    out: dict[str, np.ndarray] = {}
    for key, sub in data.groupby(group_column, dropna=False):
        cols = _numeric_columns(sub)
        if not cols:
            out[str(key)] = np.array([], dtype=float)
            continue
        arr = sub[cols].to_numpy(dtype=float, copy=False).ravel()
        out[str(key)] = arr[~np.isnan(arr)]
    return out


# ---------------------------------------------------------------------------
# Rule 1 — underpowered
# ---------------------------------------------------------------------------


def _rule_underpowered(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.min_n_per_group is None:
        return None
    sizes = _per_group_sizes(data, group_column)
    if not sizes:
        return None
    smallest_group, smallest_n = min(sizes.items(), key=lambda kv: kv[1])
    if smallest_n >= contract.min_n_per_group:
        return None
    return AuditFinding(
        rule_id="underpowered",
        severity=_DEFAULT_VERDICT["underpowered"],
        message=(
            f"smallest group '{smallest_group}' has n={smallest_n}, "
            f"below min_n_per_group={contract.min_n_per_group}"
        ),
        n_observed=smallest_n,
        threshold=contract.min_n_per_group,
    )


# ---------------------------------------------------------------------------
# Rule 2 — non_normal_with_parametric_test
# ---------------------------------------------------------------------------


def _rule_non_normal_with_parametric_test(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.distribution_assumption != "approximately_gaussian":
        return None
    groups = _per_group_arrays(data, group_column)
    worst_p = 1.0
    worst_group = None
    worst_d = 0.0
    for key, arr in groups.items():
        if arr.size < 5:
            continue
        std = float(np.std(arr, ddof=0))
        if std == 0.0:
            continue
        # Test against the standard normal of the same mean/std.
        standardised = (arr - float(np.mean(arr))) / std
        result = stats.kstest(standardised, "norm")
        d_stat = float(result.statistic)
        p_val = float(result.pvalue)
        if p_val < worst_p:
            worst_p = p_val
            worst_group = key
            worst_d = d_stat
    if worst_group is None or worst_p >= _KS_P_THRESHOLD:
        return None
    return AuditFinding(
        rule_id="non_normal_with_parametric_test",
        severity=_DEFAULT_VERDICT["non_normal_with_parametric_test"],
        message=(
            f"group '{worst_group}': KS D={worst_d:.3f}, p={worst_p:.2e} "
            f"violates approximately_gaussian assumption"
        ),
        threshold=_KS_P_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Rule 3 — uncorrected_multiple_comparisons
# ---------------------------------------------------------------------------


def _rule_uncorrected_multiple_comparisons(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.multiple_comparisons != "any_correction_required":
        return None
    accepted = {"corrected_p", "q_value", "p_adj"}
    if any(c in data.columns for c in accepted):
        return None
    return AuditFinding(
        rule_id="uncorrected_multiple_comparisons",
        severity=_DEFAULT_VERDICT["uncorrected_multiple_comparisons"],
        message=(
            "contract requires multiple-comparison correction; data lacks any "
            f"of {sorted(accepted)} columns"
        ),
    )


# ---------------------------------------------------------------------------
# Rule 4 — missing_paired_structure
# ---------------------------------------------------------------------------


def _rule_missing_paired_structure(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.independence != "paired":
        return None
    if "subject_id" not in data.columns:
        return AuditFinding(
            rule_id="missing_paired_structure",
            severity=_DEFAULT_VERDICT["missing_paired_structure"],
            message="paired design declared but no 'subject_id' column found",
        )
    counts = data["subject_id"].value_counts()
    if (counts < 2).any():
        unpaired = int((counts < 2).sum())
        return AuditFinding(
            rule_id="missing_paired_structure",
            severity=_DEFAULT_VERDICT["missing_paired_structure"],
            message=(
                f"paired design declared but {unpaired} subject(s) have only "
                "one observation"
            ),
            n_observed=unpaired,
        )
    return None


# ---------------------------------------------------------------------------
# Rule 5 — singular_design
# ---------------------------------------------------------------------------


def _rule_singular_design(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    cols = _numeric_columns(data)
    if len(cols) < 2:
        return None
    matrix = data[cols].to_numpy(dtype=float, copy=False)
    matrix = matrix[~np.any(np.isnan(matrix), axis=1)]
    if matrix.size == 0 or matrix.shape[0] < matrix.shape[1]:
        return None
    rank = int(np.linalg.matrix_rank(matrix))
    if rank >= matrix.shape[1]:
        return None
    return AuditFinding(
        rule_id="singular_design",
        severity=_DEFAULT_VERDICT["singular_design"],
        message=(
            f"covariate matrix is rank-deficient: rank={rank} < ncols="
            f"{matrix.shape[1]}"
        ),
        n_observed=rank,
        threshold=matrix.shape[1],
    )


# ---------------------------------------------------------------------------
# Rule 6 — negative_in_non_negative
# ---------------------------------------------------------------------------


def _rule_negative_in_non_negative(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.distribution_assumption not in {"non_negative", "non_negative_integer"}:
        return None
    arr = _all_numeric_values(data)
    if arr.size == 0:
        return None
    n_neg = int(np.sum(arr < 0))
    if n_neg == 0:
        return None
    return AuditFinding(
        rule_id="negative_in_non_negative",
        severity=_DEFAULT_VERDICT["negative_in_non_negative"],
        message=(
            f"distribution_assumption='{contract.distribution_assumption}' but "
            f"{n_neg} value(s) are negative (min={float(arr.min()):.3g})"
        ),
        n_observed=n_neg,
    )


# ---------------------------------------------------------------------------
# Rule 7 — unit_interval_violation
# ---------------------------------------------------------------------------


def _rule_unit_interval_violation(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.distribution_assumption != "unit_interval":
        return None
    arr = _all_numeric_values(data)
    if arr.size == 0:
        return None
    n_out = int(np.sum((arr < 0.0) | (arr > 1.0)))
    if n_out == 0:
        return None
    return AuditFinding(
        rule_id="unit_interval_violation",
        severity=_DEFAULT_VERDICT["unit_interval_violation"],
        message=(
            f"distribution_assumption='unit_interval' but {n_out} value(s) "
            f"outside [0, 1] (range=[{float(arr.min()):.3g}, "
            f"{float(arr.max()):.3g}])"
        ),
        n_observed=n_out,
    )


# ---------------------------------------------------------------------------
# Rule 8 — non_integer_in_count
# ---------------------------------------------------------------------------


def _rule_non_integer_in_count(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.distribution_assumption not in {"integer_count", "non_negative_integer"}:
        return None
    arr = _all_numeric_values(data)
    if arr.size == 0:
        return None
    non_int = ~np.isclose(arr, np.round(arr), atol=0.0, rtol=0.0)
    n_non_int = int(np.sum(non_int))
    if n_non_int == 0:
        return None
    return AuditFinding(
        rule_id="non_integer_in_count",
        severity=_DEFAULT_VERDICT["non_integer_in_count"],
        message=(
            f"distribution_assumption='{contract.distribution_assumption}' but "
            f"{n_non_int} value(s) are non-integer"
        ),
        n_observed=n_non_int,
    )


# ---------------------------------------------------------------------------
# Rule 9 — excessive_missingness
# ---------------------------------------------------------------------------


def _rule_excessive_missingness(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    threshold = (
        contract.max_missingness_fraction
        if contract.max_missingness_fraction is not None
        else _DEFAULT_MISSINGNESS_THRESHOLD
    )
    cols = _numeric_columns(data)
    if not cols:
        return None
    block = data[cols]
    total = block.size
    if total == 0:
        return None
    n_nan = int(block.isna().to_numpy().sum())
    frac = n_nan / total
    if frac <= threshold:
        return None
    return AuditFinding(
        rule_id="excessive_missingness",
        severity=_DEFAULT_VERDICT["excessive_missingness"],
        message=(
            f"NaN fraction {frac:.1%} exceeds threshold {threshold:.1%}"
        ),
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# Rule 10 — tied_zero_inflated
# ---------------------------------------------------------------------------


def _rule_tied_zero_inflated(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.distribution_assumption != "approximately_gaussian":
        return None
    arr = _all_numeric_values(data)
    if arr.size == 0:
        return None
    zero_frac = float(np.mean(arr == 0.0))
    if zero_frac <= _ZERO_INFLATION_THRESHOLD:
        return None
    return AuditFinding(
        rule_id="tied_zero_inflated",
        severity=_DEFAULT_VERDICT["tied_zero_inflated"],
        message=(
            f"{zero_frac:.1%} of values are exact zeros — Gaussian assumption "
            "is dubious"
        ),
        threshold=_ZERO_INFLATION_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Rule 11 — cluster_imbalance
# ---------------------------------------------------------------------------


def _rule_cluster_imbalance(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.independence != "clustered_by_subject":
        return None
    if "subject_id" not in data.columns:
        return None
    counts = data["subject_id"].value_counts()
    if len(counts) < 2:
        return None
    biggest = int(counts.max())
    smallest = int(counts.min())
    if smallest == 0:
        return None
    ratio = biggest / smallest
    if ratio < _CLUSTER_IMBALANCE_RATIO:
        return None
    return AuditFinding(
        rule_id="cluster_imbalance",
        severity=_DEFAULT_VERDICT["cluster_imbalance"],
        message=(
            f"cluster sizes differ by {ratio:.1f}× (max={biggest}, "
            f"min={smallest})"
        ),
        threshold=_CLUSTER_IMBALANCE_RATIO,
    )


# ---------------------------------------------------------------------------
# Rule 12 — n_below_visualization_floor
# ---------------------------------------------------------------------------


def _rule_n_below_visualization_floor(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    if contract.n_minimum_for_visualization is None:
        return None
    n = len(data)
    if n >= contract.n_minimum_for_visualization:
        return None
    return AuditFinding(
        rule_id="n_below_visualization_floor",
        severity=_DEFAULT_VERDICT["n_below_visualization_floor"],
        message=(
            f"total n={n} below visualization floor "
            f"{contract.n_minimum_for_visualization}"
        ),
        n_observed=n,
        threshold=contract.n_minimum_for_visualization,
    )


# ---------------------------------------------------------------------------
# Rule 13 — effect_size_units_undeclared
# ---------------------------------------------------------------------------


_EFFECT_SIZE_TOKENS = ("{d}", "{cohen_d}", "{effect}", "{effect_size}")


def _rule_effect_size_units_undeclared(
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None,
) -> AuditFinding | None:
    template = contract.rendered_claim_template
    if template is None:
        return None
    if contract.effect_size_in_units is not None:
        return None
    if not any(tok in template for tok in _EFFECT_SIZE_TOKENS):
        return None
    return AuditFinding(
        rule_id="effect_size_units_undeclared",
        severity=_DEFAULT_VERDICT["effect_size_units_undeclared"],
        message=(
            "rendered_claim_template references an effect-size token "
            f"({', '.join(_EFFECT_SIZE_TOKENS)}) but effect_size_in_units is None"
        ),
    )


# ---------------------------------------------------------------------------
# Rule registry (stable iteration order — matches the spec's table order)
# ---------------------------------------------------------------------------


_RuleFn = Callable[
    [StatisticalContract, pd.DataFrame, str | None], AuditFinding | None
]

_RULES: tuple[tuple[str, _RuleFn], ...] = (
    ("underpowered", _rule_underpowered),
    ("non_normal_with_parametric_test", _rule_non_normal_with_parametric_test),
    ("uncorrected_multiple_comparisons", _rule_uncorrected_multiple_comparisons),
    ("missing_paired_structure", _rule_missing_paired_structure),
    ("singular_design", _rule_singular_design),
    ("negative_in_non_negative", _rule_negative_in_non_negative),
    ("unit_interval_violation", _rule_unit_interval_violation),
    ("non_integer_in_count", _rule_non_integer_in_count),
    ("excessive_missingness", _rule_excessive_missingness),
    ("tied_zero_inflated", _rule_tied_zero_inflated),
    ("cluster_imbalance", _rule_cluster_imbalance),
    ("n_below_visualization_floor", _rule_n_below_visualization_floor),
    ("effect_size_units_undeclared", _rule_effect_size_units_undeclared),
)


# ---------------------------------------------------------------------------
# Public driver
# ---------------------------------------------------------------------------


def _escalated(finding: AuditFinding, refuses_when: tuple[str, ...]) -> AuditFinding:
    """Promote a non-refuse finding to refuse if listed in refuses_when."""
    if finding.severity == "refuse":
        return finding
    if finding.rule_id not in refuses_when:
        return finding
    return AuditFinding(
        rule_id=finding.rule_id,
        severity="refuse",
        message=finding.message,
        n_observed=finding.n_observed,
        threshold=finding.threshold,
    )


def audit_recipe_against_data(
    *,
    contract: StatisticalContract,
    data: pd.DataFrame,
    group_column: str | None = None,
    recipe_full_name: str = "<unnamed>",
) -> AuditReport:
    """Walk all 13 rules against a (contract, data) pair.

    Parameters
    ----------
    contract:
        The recipe's :class:`StatisticalContract` (frozen).
    data:
        The bound data the recipe would consume. Numeric columns are
        treated as observations; ``subject_id`` and ``cluster_id`` are
        reserved index columns. Multiple-comparison correction is
        signalled by the presence of ``corrected_p``, ``q_value``, or
        ``p_adj``.
    group_column:
        Optional column name to use for per-group rules
        (``underpowered``, ``non_normal_with_parametric_test``). When
        ``None`` the entire DataFrame is treated as a single group.
    recipe_full_name:
        Free-text identifier for the recipe; shown in CLI / report
        output. Defaults to ``"<unnamed>"``.

    Returns
    -------
    AuditReport
        Always returned; never raises. The ``overall`` field is the
        max severity across findings ("pass" if none).
    """
    findings: list[AuditFinding] = []
    refuses_when = contract.refuses_when

    for _, fn in _RULES:
        finding = fn(contract, data, group_column)
        if finding is None:
            continue
        findings.append(_escalated(finding, refuses_when))

    if not findings:
        overall: Severity = "pass"
    else:
        overall = max(
            (f.severity for f in findings), key=lambda s: _SEVERITY_ORDER[s]
        )

    return AuditReport(
        recipe_full_name=recipe_full_name,
        findings=tuple(findings),
        overall=overall,
    )
