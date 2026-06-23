"""Per-recipe statistical-rigor contract.

The audit layer (``manifest.statistical_audit``) consumes a recipe's
``StatisticalContract`` and the bound data to decide RENDER / WARN /
REFUSE before any pixels are drawn.

See ``docs/spec_statistical_contract.md`` for the full vocabulary and
13-rule audit pipeline.

Design notes
------------
* The dataclass is **frozen** so contracts can sit on the otherwise-frozen
  :class:`RecipeMetadata` without breaking equality / hashing.
* Every field defaults to its **all-permissive sentinel** (``None`` /
  ``"any"`` / ``"none"`` / ``()``) so existing recipes that omit the
  argument continue to render unchanged — this is a backwards-compat
  guarantee for the 392 untagged recipes (see spec §6, Tier-2 deferral).
* The literal types form a **closed taxonomy** (mirrors PR #57 enum
  pattern).
* ``refuses_when`` lists audit rule ids that this recipe escalates from
  WARN to REFUSE. The audit driver treats it as an escalation-only
  allow-list: a finding whose ``rule_id`` is listed is promoted to
  REFUSE (``manifest.statistical_audit._escalated``). Every name **is**
  validated at construction time against the closed rule taxonomy
  (:data:`KNOWN_REFUSAL_RULES`): an id that matches no audit rule is a
  programming error in the contract — a typo would otherwise silently
  never escalate anything — so :class:`StatisticalContract` raises
  :class:`ValueError` naming the unknown rule and listing the valid ones.
  The audit layer asserts its own registry matches this taxonomy, so the
  two cannot drift (see spec §3, "enum-validated ... at registry-import
  time").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DEFAULT_CONTRACT",
    "KNOWN_REFUSAL_RULES",
    "DistributionAssumption",
    "IndependenceStructure",
    "MultipleComparisonsPolicy",
    "StatisticalContract",
]


# Closed taxonomy of audit rule ids that may appear in ``refuses_when``.
# This mirrors the 13-rule registry in ``manifest.statistical_audit``
# (``ALL_RULE_NAMES``), which asserts at import time that the two agree so
# they cannot drift. Defined here — in the inward ``core`` layer that owns
# the contract — so ``StatisticalContract`` can validate ``refuses_when``
# without importing the outward ``manifest`` layer.
KNOWN_REFUSAL_RULES: frozenset[str] = frozenset(
    {
        "underpowered",
        "non_normal_with_parametric_test",
        "uncorrected_multiple_comparisons",
        "missing_paired_structure",
        "singular_design",
        "negative_in_non_negative",
        "unit_interval_violation",
        "non_integer_in_count",
        "excessive_missingness",
        "tied_zero_inflated",
        "cluster_imbalance",
        "n_below_visualization_floor",
        "effect_size_units_undeclared",
    }
)


DistributionAssumption = Literal[
    "any",
    "approximately_gaussian",
    "non_negative",
    "unit_interval",
    "integer_count",
    "non_negative_integer",
]

MultipleComparisonsPolicy = Literal[
    "none",
    "any_correction_required",
    "bonferroni",
    "fdr_bh",
]

IndependenceStructure = Literal[
    "any",
    "iid",
    "paired",
    "clustered_by_subject",
]


@dataclass(frozen=True)
class StatisticalContract:
    """Per-recipe statistical-rigor contract.

    Recipes declare the conditions under which they will RENDER vs
    REFUSE. See ``docs/spec_statistical_contract.md`` for the audit
    pipeline that consumes these contracts.
    """

    min_n_per_group: int | None = None
    distribution_assumption: DistributionAssumption = "any"
    multiple_comparisons: MultipleComparisonsPolicy = "none"
    independence: IndependenceStructure = "any"
    effect_size_in_units: str | None = None
    rendered_claim_template: str | None = None
    n_minimum_for_visualization: int | None = None
    refuses_when: tuple[str, ...] = ()
    max_missingness_fraction: float | None = None  # WARN above this
    requires_ci: bool = False
    """When ``True``, the figure-bias auditor (Elevation 17) treats omission
    of confidence-interval fields in ``audit_findings`` as an honest-reporting
    violation (severity = error). Backwards-compatible — existing recipes
    default to ``False`` and continue to render unchanged. See
    ``docs/spec_figure_bias_auditor.md`` §4.2."""

    def __post_init__(self) -> None:
        # ``refuses_when`` is an escalation allow-list keyed by audit rule
        # id. An id that matches no rule never escalates anything, so a typo
        # would silently disable a refusal policy. Reject it loudly: an
        # unknown rule is a programming error in the contract, not a data
        # problem the (never-raising) audit could surface later.
        unknown = [r for r in self.refuses_when if r not in KNOWN_REFUSAL_RULES]
        if unknown:
            valid = ", ".join(sorted(KNOWN_REFUSAL_RULES))
            raise ValueError(
                "StatisticalContract.refuses_when contains unknown audit rule "
                f"id(s): {sorted(unknown)}. Valid rule ids are: {valid}."
            )


# All-permissive default — the 392 untagged recipes all share this instance.
DEFAULT_CONTRACT = StatisticalContract()
