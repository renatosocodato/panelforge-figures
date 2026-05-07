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
  pattern); rule names in ``refuses_when`` are validated against the
  audit module's rule registry at audit-time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DEFAULT_CONTRACT",
    "DistributionAssumption",
    "IndependenceStructure",
    "MultipleComparisonsPolicy",
    "StatisticalContract",
]


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


# All-permissive default — the 392 untagged recipes all share this instance.
DEFAULT_CONTRACT = StatisticalContract()
