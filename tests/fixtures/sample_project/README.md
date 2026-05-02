# DISC1 Microglial Morphometry — Manuscript Companion

This repository accompanies a manuscript on **DISC1**-deficient microglia in
a mouse model of **lissencephaly**. We characterise microglial branching,
soma morphology, and process motility across cortical layers in
*Disc1*-haploinsufficient cortex versus wild-type littermates.

## Project overview

DISC1 (Disrupted-in-Schizophrenia-1) loss-of-function disrupts cortical
lamination. We use primary microglia isolated from P21 cortex of *Disc1*+/−
mice and wild-type controls, image fixed and live preparations, and
quantify morphometric features at the per-cell level.

Key biological contrasts:

- *Disc1*+/− vs WT microglia
- Cortical layer II/III vs V/VI
- Resting vs LPS-stimulated cytoskeletal state

## Repository layout

```
README.md             # this file
manuscript.md         # methods + results draft
methods.md            # full experimental design
data/
  morphometry_per_cell.csv      # per-cell features (n=30 cells)
  effect_sizes.csv              # bootstrapped effect sizes per feature
  README.md                     # data-file documentation
sample_refs.bib        # BibTeX (3 DISC1 references)
panelforge.project.yaml   # explicit panelforge config (optional)
```

## Imaging modality

Fixed-cell **z-stack confocal** imaging on a Zeiss LSM 880 with **Airyscan**.
Per-cell volumetric reconstruction at 0.04 µm lateral × 0.16 µm axial
sampling. Live-cell experiments not yet completed (this manuscript is
fixed-cell only).

## Statistics

Two-way ANOVA with **interaction** terms (genotype × layer). Effect sizes
are reported with 95 % bootstrap confidence intervals. Where the
biological hypothesis is "no difference," we additionally report a
**TOST** equivalence test against pre-registered bounds.

## Citation

If you use this dataset, cite the three references in `sample_refs.bib`.
