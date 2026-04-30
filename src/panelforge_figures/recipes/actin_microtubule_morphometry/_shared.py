"""Shared sub-contracts for the `actin_microtubule_morphometry` modality.

Pioneered by the `cytoskeletal_morphometry_companion` Wave 2 pack. The
sub-contracts here cover **territory-zone analyses**,
**contact-patch networks**, **colocalization coefficients**,
**cell outlines as PCA-coord glyphs**, and the
**Airyscan-to-zone-territory triptych** that opens the
manuscript narrative. Recipes in this modality (and a few
cross-modality consumers) import these directly. Future packs
that extend cytoskeleton morphometry can grow this module.
"""

from __future__ import annotations

from pydantic import Field

from ...core import RecipeContract

# --- territory atoms -------------------------------------------------------


class ZoneTerritoryMap(RecipeContract):
    """Per-cell H × W zone label grid.

    Used by W2.4 (intravital territory overlay) and W2.5
    (contact-network overlay). Zone values are integer labels
    (0 / 1 / 2 / 3) that map to a fixed legend
    (e.g. contact / desert / intermediate / far per the manuscript).
    """
    cell_id: str
    zone_grid: list[list[int]]                    # n_rows × n_cols, int labels
    zone_label_map: dict[int, str]                # 0 → "contact" etc.
    pixel_um: float = 0.5


class ContactPatchNetwork(RecipeContract):
    """Cell territory's contact-patch graph (nodes + edges).

    Used by W2.5. Nodes are placed at contact-patch centroids
    (xy_um); edges encode connectivity between nearby patches
    (passed as adjacency-list pairs of node indices). No graph
    algorithms are computed here — the recipe just plots nodes and
    edges as `ax.scatter` + `ax.plot` from this contract directly.
    """
    cell_id: str
    node_xy_um: list[list[float]]                 # n_nodes × 2
    edges: list[list[int]]                        # n_edges × 2 (i, j) indices
    node_weights: list[float] | None = None       # patch areas / weights
    roi_polygon_um: list[list[float]] | None = None   # closed polygon


class CellWithContactNetwork(RecipeContract):
    """Composite of a zone-territory map + a contact-patch network.

    Used by W2.5 directly. Bundling the two atoms keeps the recipe
    contract concise.
    """
    territory: ZoneTerritoryMap
    network: ContactPatchNetwork


# --- colocalization atoms --------------------------------------------------


class ColocalizationCoefficients(RecipeContract):
    """Per-cell {Manders M1, Manders M2, Pearson r, Spearman ρ}.

    Used by W2.7. Each cell carries the four canonical coefficients
    plus a condition label.
    """
    cell_id: str
    condition: str
    M1: float
    M2: float
    pearson_r: float
    spearman_rho: float


# --- PCA-with-glyphs atoms -------------------------------------------------


class CellOutlineWithPCCoord(RecipeContract):
    """One cell's outline polyline + its (PC1, PC2) coordinate.

    Used by W2.2. The outline is plotted as a custom scatter glyph
    at the cell's PC coord; the outline is a closed polyline
    (n_points × 2 in cell-local coordinates).
    """
    cell_id: str
    condition: str
    pc_coord: list[float]                          # length 2: [pc1, pc2]
    outline_xy: list[list[float]]                  # n_points × 2 (cell-local)


# --- Airyscan triptych atom ------------------------------------------------


class AiryscanTriptychBundle(RecipeContract):
    """One cell's three-panel triptych: raw → skeleton → zone map.

    Used by W2.3. The three layers must be H × W with matching
    extent; the recipe renders them side-by-side per cell.
    """
    cell_id: str
    condition: str
    raw_image: list[list[float]]                  # H × W (continuous, e.g. F-actin intensity)
    skeleton_overlay: list[list[float]]           # H × W (binary or graded skeleton mask)
    zone_map: list[list[int]]                     # H × W (integer zone labels)
    zone_label_map: dict[int, str]                # 0 → "contact" etc.
    pixel_um: float = 0.5


# --- shared demo palette ---------------------------------------------------


def _demo_zone_palette() -> dict[int, str]:
    """Zone integer → colour mapping for the contact / desert /
    intermediate / far territory schema used throughout the
    DISC1 manuscript companion pack. Reuses the existing modality
    palette colours where possible.
    """
    return {
        0: "#E91E63",   # contact (actin pink)
        1: "#9E9E9E",   # desert (mid grey)
        2: "#FFC107",   # intermediate (amber)
        3: "#37474F",   # far (slate)
    }


def _demo_zone_label_map() -> dict[int, str]:
    return {0: "contact", 1: "desert", 2: "intermediate", 3: "far"}


# --- Wave 3: cytoskeleton geometry + statistics atoms ----------------------


class BranchOrderEdge(RecipeContract):
    """One actin-to-MT angle observation + one nearest-neighbour distance.

    Used by W3.1 (`actin_mt_angle_rose_with_distance_inset`).
    The angle is in degrees (0 = parallel filaments).
    """
    cell_id: str
    condition: str
    angle_deg: float
    nn_distance_um: float


class ProtrusionOutlineWithCleveland(RecipeContract):
    """Per-protrusion outline + Cleveland-summary scalars.

    Used by W3.2 (`protrusion_outline_with_cleveland_summary`).
    Each cell carries a representative outline polyline and the
    paired width / erosion-depth scalars used in the Cleveland
    strip on the right of the panel.
    """
    cell_id: str
    condition: str
    outline_xy: list[list[float]]                 # n_points × 2
    width_um: float
    erosion_depth_um: float


class EdgeIntensityProfile(RecipeContract):
    """One per-cell intensity profile vs signed distance from cell edge.

    Used by W3.6 (`edge_gradient_intensity_profile`). Convention:
    positive `signed_distance_um` = inside the cell, negative =
    outside. `intensity` is the channel signal at each
    distance bin.
    """
    cell_id: str
    condition: str
    channel: str                                  # e.g. "F-actin" | "MT"
    signed_distance_um: list[float]
    intensity: list[float]


class CortexZoneDescriptor(RecipeContract):
    """One zone × descriptor × condition cell value with z-score colour.

    Used by W3.7 (`cortex_composite_zone_descriptors`). Each row is
    one (zone, descriptor, condition) triple with the per-cell
    population mean.
    """
    zone: str                                     # "contact" | "desert" | ...
    descriptor: str                               # e.g. "intensity_F-actin"
    condition: str
    value: float
    z_score: float                                # signed; > +0.5 = flagged
    flag: bool = False


class MTMeshDensitySnapshot(RecipeContract):
    """One cell's MT mesh-density grid in one compartment.

    Used by W3.8 (`mt_mesh_density_compartment_compare`).
    The grid carries per-pixel MT density (filaments per µm²).
    """
    cell_id: str
    condition: str
    compartment: str                              # "whole_cell" | "protrusion_internal"
    density_grid: list[list[float]]               # H × W
    pixel_um: float = 0.5


# --- Wave 4: narrative-integration atoms -----------------------------------


class PseudotimeOrderedCell(RecipeContract):
    """One cell's representative thumbnail + its pseudotime coord.

    Used by W4.1 (`pseudotime_thumbnail_strip`). The thumbnail is
    a small H × W cell-shape raster (intensity grid), and the
    pseudotime coord lives on a 1-D axis (typically [0, 1] from
    resting → extended along the Actin Drive Index).
    """
    cell_id: str
    condition: str
    pseudotime: float                              # axis coord (e.g. [0, 1])
    thumbnail_grid: list[list[float]]              # H × W (intensity)


class OverlapJuxtapositionCell(RecipeContract):
    """One cell's polymer-overlap × territory-juxtaposition coord.

    Used by W4.5 (`overlap_juxtaposition_quantification`).
    `polymer_overlap` quantifies actin-MT colocalization; `territory_
    juxtaposition` quantifies how closely territory zones abut.
    """
    cell_id: str
    condition: str
    polymer_overlap: float
    territory_juxtaposition: float


# --- factorial_design_companion Wave 3 atoms --------------------------------


class ShollProfile(RecipeContract):
    """One cell's Sholl analysis intersection profile.

    Used by W3.5 (`sholl_intersections_radial_histogram`). Each cell
    carries an array of intersection counts at concentric radii
    measured from the soma centroid; the radii are in micrometres.
    `condition` is typically a sex × genotype label; the recipe
    aggregates to per-condition mean + bootstrap CI ribbons.
    """
    cell_id: str
    condition: str                                # e.g. "female · CTL"
    radii_um: list[float]                          # ascending, length n_radii
    intersections: list[float]                     # length n_radii (>= 0)


class BehavioralFingerprintRow(RecipeContract):
    """One cell's three-panel fingerprint atoms (trace + violin + scatter).

    Used by W3.6 (`behavioral_fingerprint_trio_composite`). The recipe
    composes three sub-panels per condition: (i) representative
    velocity trace with state-shaded background, (ii) a violin
    distribution of a scalar summary (e.g. mean velocity), and
    (iii) a scatter of (cv-velocity, extension-fraction). Each row
    carries the atoms needed for one cell.
    """
    cell_id: str
    condition: str                                 # e.g. "female · CTL"
    trace_t_s: list[float]                         # representative track time
    trace_velocity_um_per_min: list[float]
    trace_state: list[str] | None = None           # optional state-shading
    summary_value: float                           # scalar for the violin
    cv_velocity: float                             # scatter x
    extension_fraction: float                      # scatter y


# --- multi-channel intravital field (used by W2.4 cross-modality) ----------


class MultiChannelField(RecipeContract):
    """One field-of-view's RGB(+) channel stack.

    Used by W2.4 in `intravital_imaging` modality. Lives here
    because the manuscript's intravital territory-overlay variant
    explicitly pairs a multi-channel image with the
    `ZoneTerritoryMap` defined above; centralising the contract
    here avoids cross-modality circular imports.
    """
    field_id: str
    red_channel: list[list[float]] = Field(...)    # H × W
    green_channel: list[list[float]] = Field(...)  # H × W
    blue_channel: list[list[float]] | None = None  # H × W (optional)
    pixel_um: float = 0.5
    channel_labels: dict[str, str] = Field(
        default_factory=lambda: {
            "red": "RFP", "green": "YFP", "blue": "DAPI",
        },
    )
