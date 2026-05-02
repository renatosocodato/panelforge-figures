# DISC1 Loss-of-Function Reshapes Microglial Branching in Mouse Cortex

## Abstract

We report that *Disc1* haploinsufficiency, a genetic model of human
**lissencephaly**, alters primary microglial morphology in a layer-
and compartment-specific way. Using **z-stack confocal Airyscan** imaging
of fixed P21 cortex, we quantify per-cell area, perimeter, branch order,
and Sholl-like radial complexity across 30 cells, then test the resulting
effect sizes against pre-registered **TOST** equivalence bounds.

## Introduction

DISC1 is a scaffold protein with multiple roles in cortical development.
Loss-of-function alleles produce a lissencephaly-spectrum phenotype, and
recent work suggests that the microglial compartment — historically
under-studied in DISC1 biology — also contributes to the cortical
phenotype. Comparable cytoskeletal-remodelling work in **Cdc42 CKO mice**
established the **compartment-aware** analysis framework we adopt here.

## Methods (summary)

Primary microglia were isolated from P21 *Disc1*+/− and wild-type cortex.
Cells were fixed, immunostained for IBA1 and phalloidin, and imaged on a
Zeiss LSM 880 in **Airyscan** mode (z-stack, 0.04 µm lateral resolution).
Per-cell features were extracted with a custom Python pipeline and
analysed by two-way **ANOVA with interaction** (genotype × cortical layer).
For each feature we report Cohen's *d* with 95 % bootstrap CI. Where the
biological hypothesis is the null ("no difference"), we additionally
report a **TOST**-style equivalence test against pre-registered bounds
of ±0.3 standardised units. All analyses are **compartment-aware**:
soma and protrusion compartments are scored separately on each cell.

## Results

Across the 30 cells, *Disc1*+/− microglia show a small reduction in
total branch order in cortical layer II/III but not in layer V/VI; the
genotype × layer interaction term is significant at *p* = 0.04. The
soma-vs-protrusion compartment split shows the effect is concentrated in
the protrusion compartment. Equivalence testing confirms that mean cell
area is statistically equivalent between genotypes within ±0.3 SD bounds.

## Discussion

The compartment-aware analysis localises the DISC1 phenotype to
microglial protrusions. This is consistent with cytoskeletal remodelling
work in Cdc42 conditional-knockout systems and motivates a follow-up
live-cell motility assay. The TOST-based equivalence reporting on cell
area should not be conflated with a positive effect on branch order.
