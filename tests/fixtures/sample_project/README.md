# Example Microglial Morphometry — Manuscript Companion (test fixture)

This is a test-fixture project used by the panelforge-figures test suite to
exercise project-scan, intake, scoring, and rendering against a realistic
manuscript-style repository layout. The biological framing is illustrative —
the data are synthetic and the references are placeholders.

## Project overview

A representative anchor (gene-of-interest) loss-of-function reshapes
cortical microglial morphology. The fixture uses primary microglia isolated
from P21 cortex of an example mutant versus wild-type controls, with
fixed-cell imaging and per-cell feature quantification.

Key biological contrasts:

- Example mutant vs WT microglia
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
sample_refs.bib       # BibTeX (3 placeholder references)
panelforge.project.yaml   # explicit panelforge config (optional)
```

## Imaging modality

Fixed-cell **z-stack confocal** imaging on a Zeiss LSM 880 with **Airyscan**.
Per-cell volumetric reconstruction at 0.04 µm lateral × 0.16 µm axial
sampling. Live-cell experiments not yet completed (this fixture is
fixed-cell only).

## Statistics

Two-way ANOVA with **interaction** terms (genotype × layer). Effect sizes
are reported with 95 % bootstrap confidence intervals. Where the
biological hypothesis is "no difference," we additionally report a
**TOST** equivalence test against pre-registered bounds.

## Citation

If you use this dataset, cite the three placeholder references in
`sample_refs.bib`.
