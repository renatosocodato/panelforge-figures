"""Shared sub-contracts for the `omics_differential` modality.

Pioneered by the `cdc42_factorial_companion` Wave 2 pack. The
sub-contracts here cover **multi-omic concordance** (proteome ×
phosphoproteome scatter, GEF/GAP/Effector module concordance) and
**pathway-space support** (multi-layer triangulation, theme-level
bridge summary, GGE branch-selectivity permutation) — the
manuscript's Figure 4 + Figure 5K-L narrative around how proteome
and phosphoproteome capture independent dimensions of sex biology.

Future packs that add multi-omic recipes can extend this module.
"""

from __future__ import annotations

from pydantic import Field

from ...core import RecipeContract

# --- proteome × phosphoproteome concordance --------------------------------


class ProteomePhosphoConcordanceRow(RecipeContract):
    """One pathway's proteome × phosphoproteome sex-effect score.

    Used by W2.1 (`proteome_phosphoproteome_pathway_scatter`).
    Each row carries one Reactome (or other) pathway with its
    proteome sex-effect score and phosphoproteome sex-effect score;
    the recipe scatters them and overlays Spearman ρ.
    """
    pathway: str
    proteome_score: float                            # signed, e.g. log2FC
    phospho_score: float                             # signed, e.g. KSEA
    n_proteins: int | None = None
    branch: str | None = None                        # optional GGE branch tag


# --- module concordance ----------------------------------------------------


class ModuleConcordanceCell(RecipeContract):
    """One module × condition × signed-score cell with sign-concordance flag.

    Used by W2.2 (`module_concordance_signed_heatmap`) and W2.6
    (`pathway_module_activity_with_sign_concordance`). Each cell
    carries a signed centred score (e.g. log2 FC or z-scored
    activity) and an optional sign-concordance verdict.
    """
    module: str                                      # e.g. "CDC42_GEF"
    condition: str                                   # e.g. "F-CKO"
    signed_score: float
    sign_concordance: str = Field(
        "neutral",
        description="'agree' | 'disagree' | 'neutral'",
    )


# --- pathway-space support -------------------------------------------------


class PathwaySupportLayer(RecipeContract):
    """One theme × match-tier × support-level cell.

    Used by W2.3 (`pathway_space_triangulation_heatmap`) and W2.4
    (`pathway_space_bridge_summary_heatmap`). Each layer captures
    how strongly an internal imaging-derived theme is supported by
    an external pathway-space layer (matched / analog / surrogate /
    internal).
    """
    theme: str                                       # e.g. "cytoskeletal_Rho"
    match_tier: str                                  # "matched" | "analog" | "internal"
    support_level: float                             # 0.0 .. 1.0
    note: str | None = None


# --- GGE branch-selectivity permutation ------------------------------------


class GGEBranchRow(RecipeContract):
    """One GGE branch with its observed score + null draws.

    Used by W2.5 (`gge_branch_selectivity_permutation_bar`). Each
    row carries a branch label, the observed effect (e.g. fraction
    of pathways with male-biased phospho), and a permutation null
    bundle keyed by the branch.
    """
    branch: str                                      # e.g. "GGE_phospho_M_high"
    observed: float
    n_pathways: int
    is_gge: bool = False                             # True if GGE-enriched


class PermutationNullBundle(RecipeContract):
    """Permutation-null distribution for a single observed effect.

    Used by W2.5. Carries the empirical null draws (sampled under
    label permutation) plus the empirical p-value with the
    +1 / +1 small-sample correction.
    """
    label: str                                       # echo of which observed effect
    null_values: list[float]
    p_perm: float
