"""Cortex composite zone descriptors — zone × descriptor heatmap
across two conditions; signed z-score colouring on RdBu_r; flag
column highlights descriptors crossing the |z| > 0.5 manuscript
threshold.

Matrix family: >=1 imshow OR >=4 cell patches.
"""

from __future__ import annotations

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC
from ._shared import CortexZoneDescriptor

_FLAG_THRESHOLD = 0.5


class CortexZoneDescriptorsInput(RecipeContract):
    descriptors: list[CortexZoneDescriptor] = Field(..., min_length=4)
    zone_order: list[str] = Field(
        default_factory=lambda: ["contact", "intermediate",
                                 "desert", "far"],
    )
    title: str = "Cortex composite zone descriptors"


def _demo() -> CortexZoneDescriptorsInput:
    rng = np.random.default_rng(661)
    descriptors_list: list[CortexZoneDescriptor] = []
    descriptor_names = ["intensity_F-actin", "intensity_MT",
                        "density_F-actin", "density_MT",
                        "connectivity", "fragmentation"]
    zones = ["contact", "intermediate", "desert", "far"]
    # Per-condition base values (z-scores).
    base_z = {
        "WT": {
            ("contact", "intensity_F-actin"): 0.05,
            ("contact", "density_F-actin"): 0.10,
            ("contact", "connectivity"): -0.20,
            ("intermediate", "intensity_MT"): 0.10,
            ("desert", "fragmentation"): 0.30,
        },
        "LI": {
            ("contact", "intensity_F-actin"): 0.55,
            ("contact", "density_F-actin"): 0.78,
            ("contact", "connectivity"): 0.65,
            ("intermediate", "intensity_MT"): 0.40,
            ("desert", "fragmentation"): -0.55,
        },
    }
    for cond in ("WT", "LI"):
        for zone in zones:
            for desc in descriptor_names:
                z = base_z.get(cond, {}).get((zone, desc),
                                             rng.normal(0, 0.12))
                value = float(rng.normal(0, 1) + z)  # arbitrary unit
                flag = abs(z) > _FLAG_THRESHOLD
                descriptors_list.append(CortexZoneDescriptor(
                    zone=zone, descriptor=desc, condition=cond,
                    value=value, z_score=float(z), flag=bool(flag),
                ))
    return CortexZoneDescriptorsInput(descriptors=descriptors_list)


_META = RecipeMetadata(
    name="cortex_composite_zone_descriptors",
    modality="actin_microtubule_morphometry",
    family=RecipeFamily.matrix,
    answers_question=(
        "Across territory zones (contact / intermediate / desert / "
        "far) and descriptor families, which (zone, descriptor) "
        "combinations show the largest condition-dependent shifts "
        "(|z| > 0.5)?"
    ),
    required_fields=("descriptors",),
    optional_fields=("zone_order", "title"),
    file_format_hints=("yaml", "csv"),
    alternatives_in_modality=("colocalization_coefficient_matrix",),
    statistical_contract=StatisticalContract(
        min_n_per_group=10,
        distribution_assumption="approximately_gaussian",
        multiple_comparisons="any_correction_required",
        independence="iid",
        effect_size_in_units="standardized_d",
        rendered_claim_template="Cohen's d = {d:.2f} ({outcome_class})",
        refuses_when=("underpowered",),
    ),
)


@register_recipe(
    metadata=_META,
    contract=CortexZoneDescriptorsInput,
    demo_contract=_demo,
)
def render(contract: CortexZoneDescriptorsInput, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(6.4, 4.2))
    AESTHETIC.apply_to_ax(ax)

    # Build cohort table: rows = (zone, descriptor) pairs, columns = conditions.
    zones = list(contract.zone_order)
    descriptor_names: list[str] = []
    for d in contract.descriptors:
        if d.descriptor not in descriptor_names:
            descriptor_names.append(d.descriptor)
    conditions = list(dict.fromkeys(d.condition for d in contract.descriptors))

    # Pair each (zone, descriptor) row with its z_score per condition.
    rows: list[tuple[str, str]] = []
    z_matrix: dict[tuple[str, str, str], float] = {}
    flag_matrix: dict[tuple[str, str, str], bool] = {}
    for z in zones:
        for desc in descriptor_names:
            rows.append((z, desc))
            for d in contract.descriptors:
                if d.zone == z and d.descriptor == desc:
                    z_matrix[(z, desc, d.condition)] = d.z_score
                    flag_matrix[(z, desc, d.condition)] = d.flag

    n_rows = len(rows)
    n_cols = len(conditions) + 1   # + flag column

    z_grid = np.zeros((n_rows, len(conditions)))
    for i, (z, desc) in enumerate(rows):
        for j, cond in enumerate(conditions):
            z_grid[i, j] = float(z_matrix.get((z, desc, cond), 0.0))

    v_abs = max(0.6, float(np.abs(z_grid).max()))
    X = np.arange(n_cols + 1) - 0.5
    Y = np.arange(n_rows + 1) - 0.5
    z_show = np.zeros((n_rows, n_cols))
    z_show[:, : len(conditions)] = z_grid
    mask = np.zeros_like(z_show, dtype=bool)
    mask[:, len(conditions)] = True
    z_masked = np.ma.masked_array(z_show, mask=mask)
    mesh = ax.pcolormesh(X, Y, z_masked, cmap="RdBu_r",
                         vmin=-v_abs, vmax=v_abs,
                         shading="auto", zorder=2)

    # Cell annotations.
    for i, (z, desc) in enumerate(rows):
        for j, cond in enumerate(conditions):
            zv = float(z_matrix.get((z, desc, cond), 0.0))
            text_color = "white" if abs(zv) > 0.6 * v_abs else "#222222"
            ax.text(j, i, f"{smart_fmt(zv)}",
                    ha="center", va="center", fontsize=6.4,
                    color=text_color, zorder=4)
        # Flag column: any condition flagged?
        any_flag = any(flag_matrix.get((z, desc, c), False)
                       for c in conditions)
        flag_text = "FLAG" if any_flag else "ok"
        flag_color = "#C62828" if any_flag else "#2E7D32"
        ax.text(len(conditions), i, flag_text,
                ha="center", va="center", fontsize=6.4,
                color=flag_color, fontweight="bold", zorder=4)

    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([f"{z} · {d}" for z, d in rows],
                       fontsize=6.2)
    ax.invert_yaxis()
    ax.set_xticks(range(n_cols))
    ax.set_xticklabels(list(conditions) + ["flag"],
                       fontsize=6.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    cbar = ax.figure.colorbar(mesh, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("z-score", fontsize=6.6)
    cbar.ax.tick_params(labelsize=6.0)

    n_flagged = sum(
        1 for d in contract.descriptors if d.flag
    )
    ax.set_title(
        f"{contract.title}  ·  "
        f"{n_flagged} flagged (|z| > {_FLAG_THRESHOLD})  ·  "
        f"{len(zones)} zones × {len(descriptor_names)} descriptors",
        fontsize=8.2, pad=4,
    )
    return ax
