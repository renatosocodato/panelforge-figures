"""Mixed-effects model figures — forest, raincloud, caterpillar, diagnostics.

This modality covers the standard outputs of hierarchical / mixed-effects
regressions (lmer, brms, lme4-style). Figures support the reviewer's
question "which terms matter, how much, and with what uncertainty?".
"""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="mixed_effects_models",
    description=(
        "Forests, raincloud variants, caterpillar plots, marginal-effect ribbons, "
        "emmeans contrast grids + group-level emmeans with pairwise brackets, "
        "posterior term + contrast densities, ICC variance decomposition + "
        "fixed/random/residual partition (Nakagawa-Schielzeth), AIC/BIC model "
        "comparison ladder, residual diagnostics, random-slope panels + "
        "(intercept, slope) scatter, partial-residuals-vs-predictor, "
        "posterior-predictive checks."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    bayes_posterior_density_by_term,
    emmeans_contrast_grid,
    fixed_vs_random_effect_partition,
    group_level_emmeans_with_pairwise,
    icc_variance_decomposition,
    marginal_effects_ribbon,
    mixed_model_residual_diagnostic,
    model_comparison_aic_bic_ladder,
    partial_residuals_vs_predictor,
    posterior_contrast_density,
    posterior_predictive_check,
    random_effects_caterpillar,
    random_intercepts_vs_slopes_scatter,
    random_slopes_per_cluster,
    sex_stratified_raincloud_with_coef_box,
    sex_x_genotype_interaction_forest,
)

__all__ = [
    "AESTHETIC",
    "bayes_posterior_density_by_term",
    "emmeans_contrast_grid",
    "fixed_vs_random_effect_partition",
    "group_level_emmeans_with_pairwise",
    "icc_variance_decomposition",
    "marginal_effects_ribbon",
    "mixed_model_residual_diagnostic",
    "model_comparison_aic_bic_ladder",
    "partial_residuals_vs_predictor",
    "posterior_contrast_density",
    "posterior_predictive_check",
    "random_effects_caterpillar",
    "random_intercepts_vs_slopes_scatter",
    "random_slopes_per_cluster",
    "sex_stratified_raincloud_with_coef_box",
    "sex_x_genotype_interaction_forest",
]
