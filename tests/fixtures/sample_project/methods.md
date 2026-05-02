# Methods

## Animals

All work was approved under institutional animal-care protocol M-2025-014.
*Disc1*+/− mice on a C57BL/6J background were obtained from a colony
maintained in-house; wild-type littermates served as controls. Cortex was
collected at P21 from both sexes (sex was recorded but not balanced as a
factorial level in this dataset).

## Primary microglia preparation

**Primary microglia** were isolated from dissected P21 cortex by mild
enzymatic dissociation and CD11b+ magnetic bead separation. Yields were
typically 1.2–1.8 × 10^5 cells per cortex. Cells were plated at low
density on poly-L-lysine-coated coverslips, fixed at 24 h post-plating,
and immunostained for IBA1, phalloidin (F-actin), and DAPI.

## Imaging

Cells were imaged on a Zeiss LSM 880 confocal microscope in **Airyscan**
super-resolution mode. Per-cell **z-stack confocal** acquisition used
0.04 µm lateral and 0.16 µm axial sampling, covering the full
soma+protrusion volume. 30 cells were imaged across 3 biological
replicates per genotype.

## Per-cell feature extraction

A custom Python pipeline segments each cell, extracts the soma centroid,
and traces protrusions in 3D. Features per cell:

- area_um2 — projected 2D area
- perimeter_um — convex-hull perimeter
- branch_order — maximum branch generation
- sholl_intersections — radial Sholl-like profile area
- compartment — `soma` / `protrusion` (each cell scored twice)

## Statistics

Two-way **ANOVA with interaction** (genotype × cortical layer) was used
for each feature. Effect sizes were estimated by 1,000-iteration
bootstrap with bias-corrected and accelerated 95 % confidence intervals.
For features where the biological hypothesis is the null, we
additionally pre-registered a **TOST** equivalence test with bounds of
±0.3 standardised mean difference units. The analysis is
**compartment-aware**: soma and protrusion compartments are scored
separately and reported in the same effect-size table.

The experimental design is **not** a balanced 2×2 factorial: only one
factor (genotype) is fully orthogonalised against cortical layer; sex
is recorded but unbalanced. We therefore avoid full factorial-style
forest plots in the figure plan.
