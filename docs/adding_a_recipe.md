# Adding a recipe

A recipe is a single file at
`src/panelforge_figures/recipes/<modality>/<recipe>.py`. This doc walks
through everything that file must contain for the CI to accept it.

## Minimal skeleton

```python
"""One-line description of the recipe and the claim it supports."""

from __future__ import annotations

from pydantic import Field
import numpy as np

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    add_halo_label,
    callout_box,
    get_palette,
    register_recipe,
    smart_fmt,
)
from ._aesthetic import AESTHETIC


class MyRecipeInput(RecipeContract):
    x: list[float] = Field(..., description="…")
    y: list[float] = Field(..., description="…")
    label: str = "output"


def _demo() -> MyRecipeInput:
    rng = np.random.default_rng(0)
    x = np.linspace(0, 10, 40)
    y = np.sin(x) + rng.normal(0, 0.2, x.size)
    return MyRecipeInput(x=x.tolist(), y=y.tolist(), label="demo")


_META = RecipeMetadata(
    name="my_recipe_name",
    modality="<modality>",
    family=RecipeFamily.diagnostic_curve,     # pick one from the enum
    answers_question="What question does this figure answer?",
    required_fields=("x", "y"),
    optional_fields=("label",),
    file_format_hints=("csv", "parquet"),
    alternatives_in_modality=("another_recipe_in_same_modality",),
)


@register_recipe(metadata=_META, contract=MyRecipeInput, demo_contract=_demo)
def render(contract: MyRecipeInput, ax=None, **_):
    """Render one panel into `ax`."""
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.0, 3.0))
    AESTHETIC.apply_to_ax(ax)                 # mandatory
    palette = get_palette(AESTHETIC.primary_palette)

    # ...plot here...

    return ax
```

## Hard requirements

1. **Imports from `._aesthetic`** — every recipe MUST
   `from ._aesthetic import AESTHETIC` and call `AESTHETIC.apply_to_ax(ax)`
   (or `.apply_to_fig(fig)`) somewhere. The aesthetic-compliance test
   AST-inspects your file.
2. **`demo_contract()`** — a callable returning a *realistic* input. It
   drives the gallery render and the smoke/quality tests. Keep it <20 KB
   of data; use synthetic but scientifically plausible values.
3. **`@register_recipe`** decorator — otherwise the CLI and skill can't
   find it.
4. **Named metadata** — `answers_question` must end in `?`;
   `alternatives_in_modality` should name at least one sibling recipe so
   the skill can justify its choice.
5. **No hardcoded colors** — use `palette.pick(...)` / semantic lookups.
6. **≥80 lines of substantive rendering code** (excluding docstring +
   imports). If you only call `sns.barplot`, the quality gate will not
   accept it — add halo'd labels, CI whiskers, smart numeric annotations,
   callout boxes, sensible ordering.

## Pick a family

Families drive the quality gate. See `RecipeFamily` in
`src/panelforge_figures/core/contract.py` for the full enum. Each family
has a rule under `tests/quality_rules/<modality>.py` that asserts the
figure has the right kind of content (bars, scatter, fills, lines,
polar axis, etc.). If your recipe genuinely doesn't fit any family,
add a new one + rule before you add the recipe.

## Add to the modality `__init__.py`

```python
from . import my_recipe_name  # noqa: F401
```

The package import triggers `@register_recipe`, which registers the
function in the global registry.

## Regenerate the gallery + commit the PNG

```bash
figures gallery regenerate
git add docs/gallery/<modality>/<recipe>.png
```

## Run the tests

```bash
pytest -q
```

Smoke, quality, aesthetic compliance must all pass. Catalog sanity
should now report one more recipe.
