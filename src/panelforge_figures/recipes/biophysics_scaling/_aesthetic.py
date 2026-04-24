"""Visual DNA for `biophysics_scaling` recipes.

Conventions:
  - `okabe_ito` categorical for multi-regime / multi-condition overlays.
  - Continuous cividis for heat-map style densities.
  - Dashed reference slopes in grey, data in accent color.
  - Slope box: compact pill annotating the fitted exponent.
  - No strokes, no bold.

Beta-pack extension
-------------------
The pack adds a subclass `BiophysicsScalingAesthetic` of
`ModalityAesthetic` that carries an `outcome_palette` dict for the
three-colour outcome coding (significant / null_accepting / equivocal)
used by A.1, B.1, B.4, and similar equivalence-bounded forests. The
subclass is isolated to this modality — zero changes to
`core/aesthetic_base.py` and no impact on other modalities.
"""

from pydantic import Field

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic


class BiophysicsScalingAesthetic(ModalityAesthetic):
    """Modality aesthetic extended with a three-colour outcome palette.

    Used by recipes that classify effect-size CIs against a TOST
    equivalence zone. Override `outcome_palette` via the constructor
    to swap colours; recipes read keys ``significant`` /
    ``null_accepting`` / ``equivocal``.
    """

    outcome_palette: dict[str, str] = Field(
        default_factory=lambda: {
            "significant": "#1565C0",
            "null_accepting": "#2E7D32",
            "equivocal": "#9E9E9E",
        }
    )


AESTHETIC = BiophysicsScalingAesthetic(
    modality_name="biophysics_scaling",
    primary_palette="okabe_ito",
    continuous_cmap="cividis",
    density_cmap="magma",
    ratio_cmap="RdBu_r",
    annotation_style=AnnotationStyle(
        halo_width=0.0,
        label_fontsize=7.2,
        label_fontweight="normal",
        callout_pad=0.28,
        callout_accent="#333333",
    ),
    inset_convention=None,
    required_scale_bars=False,
    label_vocabulary={"slope": r"$\alpha$", "exponent": r"$\beta$"},
    spine_color="#333333",
)
