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
        "emmeans contrast grids, posterior-predictive checks, ICC variance "
        "decomposition, residual diagnostics, random-slope panels, posterior "
        "density-by-term."
    ),
    aesthetic=AESTHETIC,
)

from . import (  # noqa: E402,F401
    bayes_posterior_density_by_term,
    emmeans_contrast_grid,
    icc_variance_decomposition,
    marginal_effects_ribbon,
    mixed_model_residual_diagnostic,
    posterior_predictive_check,
    random_effects_caterpillar,
    random_slopes_per_cluster,
    sex_x_genotype_interaction_forest,
)

__all__ = [
    "AESTHETIC",
    "bayes_posterior_density_by_term",
    "emmeans_contrast_grid",
    "icc_variance_decomposition",
    "marginal_effects_ribbon",
    "mixed_model_residual_diagnostic",
    "posterior_predictive_check",
    "random_effects_caterpillar",
    "random_slopes_per_cluster",
    "sex_x_genotype_interaction_forest",
]
