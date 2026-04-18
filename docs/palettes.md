# Palettes

13 palettes are registered at package import. Each has an ordered `colors`
tuple and an optional `semantic` map so recipes can look up colors by the
*role* they play (e.g., `home_gate_trap.pick("GATE") == "#F9A825"`).

| Palette | Semantic keys | Typical use |
|---|---|---|
| `okabe_ito` | — | Color-universal categorical (8 colors) |
| `sex_dimorphic` | F, M, pooled | Sex stratification |
| `home_gate_trap` | HOME, GATE, TRAP | Tristable RhoGTPase states |
| `wt_ko` | WT, KO | Genotype comparison |
| `redox_bistable` | reduced, oxidized, intermediate | Redox bistability |
| `fret_donor_acceptor` | donor, acceptor, ratio_up, ratio_down | FRET biosensor panels |
| `sex_x_genotype` | F_WT, M_WT, F_KO, M_KO | 2×2 sex × genotype |
| `timepoint_gradient` | — | Time-course overlays |
| `mechanism_class` | signaling, metabolic, cytoskeletal, other | Pathway/mechanism groups |
| `cytoskeleton_components` | actin, microtubule, intermediate_filament | Cytoskeleton panels |
| `rhogtpase_family` | RhoA, Rac1, Cdc42 | RhoGTPase comparisons |
| `microglia_states` | homeostatic, surveillant, activated, DAM, proliferative | Microglial states |
| `journal_neutral` | — | Venue-neutral categorical (6 colors) |

## Semantic lookup in recipes

```python
from panelforge_figures.core.palette import get_palette, semantic_color

p = get_palette("sex_dimorphic")
c_F = p.pick("F")                         # "#C73E7F"
c_def = semantic_color("wt_ko", "missing", default="#888888")
```

Recipes must NOT hardcode hex colors outside of `core/palette.py` or a
modality's `_aesthetic.py`. The aesthetic-compliance test doesn't catch
this automatically yet, but reviewers should.

## Adding a palette

```python
from panelforge_figures.core.palette import Palette, register_palette

register_palette(
    Palette(
        name="my_palette",
        colors=("#112233", "#445566"),
        semantic={"first": "#112233", "second": "#445566"},
        description="Short, human-readable description.",
    )
)
```

Call this at package import time (e.g. in a modality's `_aesthetic.py` if
the palette is modality-specific).
