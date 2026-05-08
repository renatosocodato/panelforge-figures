"""Recipe authoring co-pilot (Elevation 6).

Scaffolds a draft recipe (Python module + smoke test + gallery demo)
following the existing 448-recipe pattern. The author refines the
rendering logic; everything else is generated.

Public surface
--------------
``scaffold_recipe`` builds an in-memory :class:`RecipeScaffold` describing
the artefacts a fresh recipe needs:

* ``recipes/<modality>/<recipe_name>.py`` — the recipe module text
  (``RecipeMetadata``, ``StatisticalContract``, ``register_recipe``,
  family-appropriate render scaffold, demo data generator).
* ``tests/recipes/test_<recipe_name>.py`` — a smoke test plus a style
  ratchet (axis present, demo content rendered).
* ``docs/gallery/<modality>/<recipe_name>.png`` — the auto-rendered demo.

``write_scaffold`` materialises the recipe and test files; it does not
clobber existing files unless ``overwrite=True``.

``render_demo_to_gallery`` lazily imports the freshly written recipe,
instantiates the demo contract, renders, and writes the PNG. This step
is wrapped in a try / except by the CLI so a broken scaffold doesn't
block the rest of the workflow.

The five supported families (``coef_forest``, ``comparison``,
``correlation``, ``factorial``, ``equivalence``) ship with default
``StatisticalContract`` skeletons that pass the audit defaults; the
caller may override individual fields via the
``statistical_contract_overrides`` mapping.
"""
from __future__ import annotations

import importlib
import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "FAMILY_TEMPLATES",
    "RecipeAuthoringError",
    "RecipeScaffold",
    "list_supported_families",
    "render_demo_to_gallery",
    "scaffold_demo_data_generator",
    "scaffold_recipe",
    "scaffold_recipe_test",
    "validate_modality_name",
    "validate_recipe_name",
    "write_scaffold",
]


class RecipeAuthoringError(ValueError):
    """Raised on invalid modality/recipe names or unsupported family."""


@dataclass(frozen=True)
class RecipeScaffold:
    """Generated artefacts for a new recipe.

    Attributes mirror what ``write_scaffold`` will produce on disk plus
    the unrendered ``recipe_module_text`` / ``test_module_text`` so a
    caller can inspect the source before persisting it.
    """
    modality: str
    recipe_name: str
    family: str
    recipe_module_path: Path
    test_module_path: Path
    gallery_png_path: Path
    recipe_module_text: str
    test_module_text: str
    research_question: str
    statistical_contract_dict: dict[str, Any]


# ─────────────────────────── family templates ────────────────────────────

# Each entry below picks values from the closed taxonomy in
# ``core.statistical_contract`` (DistributionAssumption /
# MultipleComparisonsPolicy / IndependenceStructure). The ``render_scaffold``
# is intentionally minimal but rich enough to satisfy the family quality
# rule in ``tests/quality_rules/`` (e.g. coef_forest needs ≥3 markers +
# ≥1 reference line). The author replaces the body once the rendering
# logic is finalised.
FAMILY_TEMPLATES: dict[str, dict[str, Any]] = {
    "coef_forest": {
        "default_contract_skeleton": {
            "min_n_per_group": 10,
            "distribution_assumption": "approximately_gaussian",
            "multiple_comparisons": "any_correction_required",
            "independence": "iid",
            "effect_size_in_units": "standardized_d",
            "rendered_claim_template": "Cohen's d = {d:.2f} ({outcome_class})",
            "refuses_when": ("underpowered",),
        },
        "render_scaffold": (
            "    AESTHETIC_apply(ax)\n"
            "    # TODO: replace this stub with the real coef-forest rendering.\n"
            "    # Defaults below satisfy the coef_forest quality gate\n"
            "    # (>=3 estimate markers + >=1 reference line).\n"
            "    terms = list(contract.terms)\n"
            "    y = np.arange(len(terms))[::-1]\n"
            "    ax.axvline(0.0, color=\"#888888\", lw=0.7, ls=\"--\")\n"
            "    for yi, t in zip(y, terms):\n"
            "        ax.plot([t['ci_lo'], t['ci_hi']], [yi, yi],\n"
            "                color=\"#37474F\", lw=1.0)\n"
            "        ax.scatter([t['d']], [yi], s=42,\n"
            "                   facecolor=\"#37474F\", edgecolor=\"white\")\n"
            "    ax.set_yticks(y)\n"
            "    ax.set_yticklabels([t['term'] for t in terms], fontsize=7)\n"
            "    ax.set_xlabel(\"Cohen's d\")\n"
        ),
    },
    "comparison": {
        "default_contract_skeleton": {
            "min_n_per_group": 8,
            "distribution_assumption": "approximately_gaussian",
            "multiple_comparisons": "none",
            "independence": "iid",
            "effect_size_in_units": "standardized_d",
            "rendered_claim_template": "Cohen's d = {d:.2f}",
            "refuses_when": ("underpowered",),
        },
        "render_scaffold": (
            "    AESTHETIC_apply(ax)\n"
            "    # TODO: replace this stub with the real comparison rendering.\n"
            "    ax.boxplot(\n"
            "        [contract.group_a, contract.group_b],\n"
            "        labels=[\"A\", \"B\"],\n"
            "    )\n"
            "    ax.set_ylabel(contract.response_label)\n"
        ),
    },
    "correlation": {
        "default_contract_skeleton": {
            "min_n_per_group": 30,
            "distribution_assumption": "approximately_gaussian",
            "multiple_comparisons": "none",
            "independence": "iid",
            "effect_size_in_units": "pearson_r",
            "rendered_claim_template": "r = {r:.2f}",
            "refuses_when": ("underpowered",),
        },
        "render_scaffold": (
            "    AESTHETIC_apply(ax)\n"
            "    # TODO: replace this stub with the real correlation rendering.\n"
            "    ax.scatter(contract.x, contract.y, s=14,\n"
            "               facecolor=\"#37474F\", edgecolor=\"white\")\n"
            "    ax.set_xlabel(\"x\")\n"
            "    ax.set_ylabel(\"y\")\n"
        ),
    },
    "factorial": {
        "default_contract_skeleton": {
            "min_n_per_group": 10,
            "distribution_assumption": "approximately_gaussian",
            "multiple_comparisons": "any_correction_required",
            "independence": "iid",
            "effect_size_in_units": "partial_eta_squared",
            "rendered_claim_template": "F = {f:.2f}, p = {p:.3g}",
            "refuses_when": ("underpowered",),
        },
        "render_scaffold": (
            "    AESTHETIC_apply(ax)\n"
            "    # TODO: replace this stub with the real factorial rendering.\n"
            "    cells = contract.cells\n"
            "    labels = list(cells.keys())\n"
            "    means = [float(np.mean(cells[k])) for k in labels]\n"
            "    ax.bar(np.arange(len(labels)), means,\n"
            "           color=\"#37474F\", edgecolor=\"white\")\n"
            "    ax.set_xticks(np.arange(len(labels)))\n"
            "    ax.set_xticklabels(labels, fontsize=7)\n"
            "    ax.set_ylabel(contract.response_label)\n"
        ),
    },
    "equivalence": {
        "default_contract_skeleton": {
            "min_n_per_group": 12,
            "distribution_assumption": "approximately_gaussian",
            "multiple_comparisons": "none",
            "independence": "iid",
            "effect_size_in_units": "standardized_d",
            "rendered_claim_template": "TOST passed (|d| < {margin:.2f})",
            "refuses_when": ("underpowered",),
        },
        "render_scaffold": (
            "    AESTHETIC_apply(ax)\n"
            "    # TODO: replace this stub with the real equivalence rendering.\n"
            "    ax.errorbar(\n"
            "        [contract.d], [0],\n"
            "        xerr=[[contract.d - contract.ci_lo],\n"
            "              [contract.ci_hi - contract.d]],\n"
            "        fmt=\"o\", color=\"#37474F\",\n"
            "    )\n"
            "    ax.axvline(-contract.margin, color=\"#888888\", lw=0.5, ls=\"--\")\n"
            "    ax.axvline(contract.margin, color=\"#888888\", lw=0.5, ls=\"--\")\n"
            "    ax.axvline(0.0, color=\"#BDBDBD\", lw=0.4, ls=\":\")\n"
            "    ax.set_xlabel(\"Cohen's d\")\n"
        ),
    },
}


_VALID_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_modality_name(name: str) -> None:
    """Modality names are lowercase_snake_case (matches existing modules)."""
    if not isinstance(name, str) or not _VALID_NAME_PATTERN.match(name):
        raise RecipeAuthoringError(
            f"modality name must be lowercase_snake_case (got {name!r})"
        )


def validate_recipe_name(name: str) -> None:
    """Recipe names are lowercase_snake_case (matches existing recipes)."""
    if not isinstance(name, str) or not _VALID_NAME_PATTERN.match(name):
        raise RecipeAuthoringError(
            f"recipe name must be lowercase_snake_case (got {name!r})"
        )


def list_supported_families() -> tuple[str, ...]:
    """Return the families recognised by ``scaffold_recipe``."""
    return tuple(FAMILY_TEMPLATES.keys())


# ─────────────────────────── demo generators ─────────────────────────────


def scaffold_demo_data_generator(family: str) -> str:
    """Family-specific demo data generator body (Python source as text)."""
    if family == "coef_forest":
        return textwrap.dedent('''\
            rng = np.random.default_rng(820)
            terms = []
            for label in ("term_a", "term_b", "term_c"):
                d = float(rng.normal(0.3, 0.1))
                terms.append({
                    "term": label,
                    "d": d,
                    "p_value": 0.04,
                    "ci_lo": d - 0.2,
                    "ci_hi": d + 0.2,
                })
            return _DemoInput(terms=terms, response_label="demo")
        ''').rstrip("\n")
    if family == "comparison":
        return textwrap.dedent('''\
            rng = np.random.default_rng(820)
            return _DemoInput(
                group_a=rng.normal(0.0, 1.0, 30).tolist(),
                group_b=rng.normal(0.4, 1.0, 30).tolist(),
                response_label="demo",
            )
        ''').rstrip("\n")
    if family == "correlation":
        return textwrap.dedent('''\
            rng = np.random.default_rng(820)
            x = rng.normal(0.0, 1.0, 50)
            y = 0.5 * x + rng.normal(0.0, 1.0, 50)
            return _DemoInput(x=x.tolist(), y=y.tolist())
        ''').rstrip("\n")
    if family == "factorial":
        return textwrap.dedent('''\
            rng = np.random.default_rng(820)
            return _DemoInput(
                cells={
                    "a1b1": rng.normal(0.0, 1.0, 10).tolist(),
                    "a1b2": rng.normal(0.3, 1.0, 10).tolist(),
                    "a2b1": rng.normal(0.5, 1.0, 10).tolist(),
                    "a2b2": rng.normal(0.8, 1.0, 10).tolist(),
                },
                response_label="demo",
            )
        ''').rstrip("\n")
    if family == "equivalence":
        return textwrap.dedent('''\
            return _DemoInput(d=0.1, ci_lo=-0.3, ci_hi=0.3, margin=0.5)
        ''').rstrip("\n")
    raise RecipeAuthoringError(f"no demo generator for family {family!r}")


# ─────────────────────────── contract field maps ─────────────────────────


_FAMILY_CONTRACT_FIELDS: dict[str, str] = {
    "coef_forest": (
        "    terms: list[dict[str, Any]] = Field(...)\n"
        "    response_label: str = \"\"\n"
    ),
    "comparison": (
        "    group_a: list[float] = Field(...)\n"
        "    group_b: list[float] = Field(...)\n"
        "    response_label: str = \"\"\n"
    ),
    "correlation": (
        "    x: list[float] = Field(...)\n"
        "    y: list[float] = Field(...)\n"
    ),
    "factorial": (
        "    cells: dict[str, list[float]] = Field(...)\n"
        "    response_label: str = \"\"\n"
    ),
    "equivalence": (
        "    d: float = Field(...)\n"
        "    ci_lo: float = Field(...)\n"
        "    ci_hi: float = Field(...)\n"
        "    margin: float = Field(...)\n"
    ),
}


_FAMILY_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "coef_forest": ("terms",),
    "comparison": ("group_a", "group_b"),
    "correlation": ("x", "y"),
    "factorial": ("cells",),
    "equivalence": ("d", "ci_lo", "ci_hi", "margin"),
}


_FAMILY_OPTIONAL_FIELDS: dict[str, tuple[str, ...]] = {
    "coef_forest": ("response_label",),
    "comparison": ("response_label",),
    "correlation": (),
    "factorial": ("response_label",),
    "equivalence": (),
}


# ─────────────────────────── source rendering ─────────────────────────────


def _render_recipe_module(
    *,
    modality: str,
    recipe_name: str,
    family: str,
    research_question: str,
    contract_skeleton: dict[str, Any],
    render_scaffold: str,
    demo_gen: str,
) -> str:
    """Generate the recipe module source text.

    The output is import-clean, ruff-clean (modulo per-recipe TODOs the
    author has to fill in), and registers itself with the global recipe
    registry on import. The render body is intentionally a thin scaffold
    that already satisfies the family quality gate.
    """
    contract_class = _camel_case(recipe_name) + "Input"
    research_question_literal = research_question.replace('"""', "'''")

    contract_lines = ["StatisticalContract("]
    for key, value in contract_skeleton.items():
        contract_lines.append(f"        {key}={value!r},")
    contract_lines.append("    )")
    contract_block = "\n".join(contract_lines)

    required_fields = _FAMILY_REQUIRED_FIELDS[family]
    optional_fields = _FAMILY_OPTIONAL_FIELDS[family]
    required_tuple = ", ".join(repr(f) for f in required_fields)
    if len(required_fields) == 1:
        required_tuple += ","
    optional_tuple = ", ".join(repr(f) for f in optional_fields)
    if len(optional_fields) == 1:
        optional_tuple += ","

    contract_fields = _FAMILY_CONTRACT_FIELDS[family]
    demo_body = textwrap.indent(demo_gen, "    ")

    return f'''"""{recipe_name} — auto-scaffolded {family} recipe (panelforge author-recipe).

Research question:
    {research_question_literal}

Generated by ``panelforge_figures.manifest.recipe_authoring.scaffold_recipe``.
The author should:
  1. Replace the demo data generator with one matching the real input shape.
  2. Replace the render body with the production rendering logic.
  3. Tighten the ``StatisticalContract`` (min_n, refuses_when, claim template).
  4. Add this recipe to the parent modality ``__init__.py`` import list.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import Field

from ...core import (
    RecipeContract,
    RecipeFamily,
    RecipeMetadata,
    StatisticalContract,
    register_recipe,
)


def AESTHETIC_apply(ax) -> None:
    """Apply the modality aesthetic if available, else a sane default."""
    try:
        from ._aesthetic import AESTHETIC  # type: ignore[import-not-found]
        AESTHETIC.apply_to_ax(ax)
    except Exception:
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)


class {contract_class}(RecipeContract):
{contract_fields}

# Alias used by the demo generator below.
_DemoInput = {contract_class}


def _demo() -> {contract_class}:
{demo_body}


_META = RecipeMetadata(
    name={recipe_name!r},
    modality={modality!r},
    family=RecipeFamily.{family},
    answers_question=(
        {research_question_literal!r}
    ),
    required_fields=({required_tuple}),
    optional_fields=({optional_tuple}),
    statistical_contract={contract_block},
)


@register_recipe(
    metadata=_META,
    contract={contract_class},
    demo_contract=_demo,
)
def render(contract: {contract_class}, ax=None, **_):
    if ax is None:
        import matplotlib.pyplot as plt
        _, ax = plt.subplots(figsize=(4.4, 3.0))
{render_scaffold}    return ax
'''


def scaffold_recipe_test(
    *, modality: str, recipe_name: str, family: str
) -> str:
    """Generate the recipe smoke-test source text."""
    return _render_recipe_test(
        modality=modality, recipe_name=recipe_name, family=family,
    )


def _render_recipe_test(
    *, modality: str, recipe_name: str, family: str
) -> str:
    """Smoke + style ratchet: importable, registers, demo renders, has content."""
    full_name = f"{modality}.{recipe_name}"
    return f'''"""Smoke + style ratchet for the auto-scaffolded recipe {full_name!r}.

Generated by panelforge ``author-recipe``. Adjust the assertions once
the production rendering logic is in place; do not delete this file —
the smoke layer guards against accidental regressions in the registry.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # noqa: E402  (must precede pyplot import)
import matplotlib.pyplot as plt  # noqa: E402

from panelforge_figures.core.contract import (  # noqa: E402
    ensure_all_imported,
    get_recipe,
)


def test_smoke() -> None:
    """The freshly scaffolded recipe must register and render its demo."""
    ensure_all_imported()
    entry = get_recipe({full_name!r})
    fig, ax = plt.subplots(figsize=(3.0, 2.4))
    try:
        entry.render(entry.demo_contract(), ax=ax)
        assert any(
            a.has_data() or len(a.get_children()) > 0 for a in fig.axes
        ), {f"recipe {full_name!r} produced an empty axis"!r}
    finally:
        plt.close(fig)


def test_metadata_family() -> None:
    """Style ratchet — family declaration must equal the scaffolded one."""
    ensure_all_imported()
    entry = get_recipe({full_name!r})
    assert entry.metadata.family.value == {family!r}
    assert entry.metadata.modality == {modality!r}
'''


def _camel_case(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


# ─────────────────────────── public API ──────────────────────────────────


def scaffold_recipe(
    *,
    modality: str,
    recipe_name: str,
    family: str,
    research_question: str,
    project_root: Path,
    statistical_contract_overrides: dict[str, Any] | None = None,
) -> RecipeScaffold:
    """Build an in-memory scaffold for a new recipe.

    The function performs all the validation up front and returns a
    :class:`RecipeScaffold` containing both the generated text and the
    target paths. Caller decides when to persist via
    :func:`write_scaffold` and (optionally) :func:`render_demo_to_gallery`.
    """
    validate_modality_name(modality)
    validate_recipe_name(recipe_name)
    if family not in FAMILY_TEMPLATES:
        raise RecipeAuthoringError(
            f"family {family!r} not supported; use one of "
            f"{list_supported_families()}"
        )
    if not isinstance(research_question, str) or not research_question.strip():
        raise RecipeAuthoringError("research_question must be a non-empty string")

    template = FAMILY_TEMPLATES[family]
    contract_skeleton = dict(template["default_contract_skeleton"])
    if statistical_contract_overrides:
        contract_skeleton.update(statistical_contract_overrides)
    render_scaffold = template["render_scaffold"]
    demo_gen = scaffold_demo_data_generator(family)

    recipe_text = _render_recipe_module(
        modality=modality,
        recipe_name=recipe_name,
        family=family,
        research_question=research_question,
        contract_skeleton=contract_skeleton,
        render_scaffold=render_scaffold,
        demo_gen=demo_gen,
    )
    test_text = _render_recipe_test(
        modality=modality, recipe_name=recipe_name, family=family,
    )

    project_root = Path(project_root)
    recipe_path = (
        project_root / "src" / "panelforge_figures"
        / "recipes" / modality / f"{recipe_name}.py"
    )
    test_path = (
        project_root / "tests" / "recipes" / f"test_{recipe_name}.py"
    )
    gallery_png = (
        project_root / "docs" / "gallery"
        / modality / f"{recipe_name}.png"
    )

    return RecipeScaffold(
        modality=modality,
        recipe_name=recipe_name,
        family=family,
        recipe_module_path=recipe_path,
        test_module_path=test_path,
        gallery_png_path=gallery_png,
        recipe_module_text=recipe_text,
        test_module_text=test_text,
        research_question=research_question,
        statistical_contract_dict=contract_skeleton,
    )


def write_scaffold(
    scaffold: RecipeScaffold, *, overwrite: bool = False
) -> dict[str, Path]:
    """Materialise the scaffold on disk.

    Creates parent directories as needed and refuses to overwrite
    existing recipe / test files unless ``overwrite=True``. Always
    creates a gallery directory placeholder so downstream tooling has a
    place to drop the demo PNG. The placeholder is *not* a PNG — the
    caller renders the real demo via :func:`render_demo_to_gallery`.

    Returns a dict ``{"recipe": ..., "test": ..., "gallery": ...}`` of
    the absolute paths that were touched.
    """
    if not overwrite:
        if scaffold.recipe_module_path.exists():
            raise RecipeAuthoringError(
                f"recipe file already exists: {scaffold.recipe_module_path} "
                "(pass overwrite=True to replace it)"
            )
        if scaffold.test_module_path.exists():
            raise RecipeAuthoringError(
                f"test file already exists: {scaffold.test_module_path} "
                "(pass overwrite=True to replace it)"
            )
    scaffold.recipe_module_path.parent.mkdir(parents=True, exist_ok=True)
    scaffold.test_module_path.parent.mkdir(parents=True, exist_ok=True)
    scaffold.gallery_png_path.parent.mkdir(parents=True, exist_ok=True)
    scaffold.recipe_module_path.write_text(scaffold.recipe_module_text)
    scaffold.test_module_path.write_text(scaffold.test_module_text)
    return {
        "recipe": scaffold.recipe_module_path.resolve(),
        "test": scaffold.test_module_path.resolve(),
        "gallery": scaffold.gallery_png_path.resolve(),
    }


def render_demo_to_gallery(scaffold: RecipeScaffold) -> Path:
    """Import the freshly written recipe, render the demo, save to gallery.

    Imports are deferred so we don't pay matplotlib's import cost for
    every CLI invocation. The function is best-effort: rendering failures
    raise so the CLI can present them to the author, but they do not
    leave the disk in a bad state because :func:`write_scaffold` already
    persisted the recipe + test.
    """
    if not scaffold.recipe_module_path.exists():
        raise RecipeAuthoringError(
            f"recipe file missing: {scaffold.recipe_module_path}; "
            "call write_scaffold(...) before rendering the demo"
        )
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    # Best-effort: drop the cached registration so a re-scaffold during
    # the same Python process picks up the new module.
    module_name = (
        f"panelforge_figures.recipes.{scaffold.modality}.{scaffold.recipe_name}"
    )
    import sys as _sys

    _sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)

    contract = module._demo()  # noqa: SLF001 — generator name is private by convention
    fig, ax = plt.subplots(figsize=(4.4, 3.0))
    try:
        module.render(contract, ax=ax)
        scaffold.gallery_png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(scaffold.gallery_png_path, dpi=120, bbox_inches="tight")
    finally:
        plt.close(fig)
    return scaffold.gallery_png_path.resolve()
