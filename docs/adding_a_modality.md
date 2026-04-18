# Adding a modality

Adding a new modality is a 3-file ritual plus a quality rule.

## 1. Create the subpackage

```
src/panelforge_figures/recipes/<modality>/
├── __init__.py                ← registers the modality + imports recipes
├── _aesthetic.py              ← defines the AESTHETIC instance
└── <recipe_1>.py, <recipe_2>.py, …
```

## 2. `_aesthetic.py`

```python
"""Visual DNA for <modality> recipes."""

from ...core.aesthetic_base import AnnotationStyle, ModalityAesthetic

AESTHETIC = ModalityAesthetic(
    modality_name="<modality>",
    primary_palette="<palette_name>",
    ratio_cmap="RdBu_r",                 # only if the modality uses ratios
    continuous_cmap="viridis",
    density_cmap="magma",
    annotation_style=AnnotationStyle(
        halo_width=2.8,
        label_fontsize=7.8,
        label_fontweight="bold",
        callout_pad=0.30,
        callout_accent="#333333",
    ),
    inset_convention=None,               # or an InsetConvention(...)
    required_scale_bars=False,           # True for imaging modalities
    label_vocabulary={"key": "display"},
    color_anchor=None,                   # e.g. 1.0 for FRET ratio
    spine_color="#333333",
)
```

## 3. `__init__.py`

```python
"""<modality description>."""

from ...core.contract import register_modality
from ._aesthetic import AESTHETIC

register_modality(
    name="<modality>",
    description="One or two sentence description.",
    aesthetic=AESTHETIC,
)

from . import recipe_1, recipe_2   # noqa: F401
```

## 4. Quality rules

Add or extend `tests/quality_rules/<modality>.py` if the modality
introduces recipe families that don't exist yet. Then register them in
`tests/quality_rules/__init__.py`'s `RULES` dict.

## 5. Write the recipes

Follow [adding_a_recipe.md](adding_a_recipe.md). Each recipe in this
modality MUST `from ._aesthetic import AESTHETIC` and apply it to the axis.

## 6. Regenerate gallery + commit

```bash
figures gallery regenerate
git add docs/gallery/<modality>/*.png
```

## 7. Run tests + catalog sanity

```bash
pytest -q
figures catalog --json | python -c "import json,sys; d=json.load(sys.stdin); print(len(d['modalities']), 'modalities'); print(sum(len(m['recipes']) for m in d['modalities']), 'recipes')"
```

## 8. Update docs

- Add a row to `docs/recipes_by_modality.md` with a link to the
  `answers_question` field of each recipe.
- Add the recipe links to `docs/recipes_by_question.md`.
- Update `CHANGELOG.md` under the current `[Unreleased]` entry.
