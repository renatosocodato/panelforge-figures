"""Recipe registry and metadata."""

import pytest

from panelforge_figures.core.contract import (
    RecipeFamily,
    ensure_all_imported,
    get_recipe,
    list_modalities,
    list_recipes,
    modality_description,
    registry_counts,
)


def test_registry_has_at_least_18_recipes():
    ensure_all_imported()
    assert len(list_recipes()) >= 18


def test_each_modality_has_its_recipes_registered():
    ensure_all_imported()
    counts = registry_counts()
    assert counts["grant_and_conceptual"] == 16
    assert counts["meta_and_diagnostic"] == 21
    assert counts["sensitivity_analysis"] == 15


def test_every_registered_recipe_has_required_fields_and_question():
    ensure_all_imported()
    for e in list_recipes():
        m = e.metadata
        assert m.name
        assert m.modality
        assert isinstance(m.family, RecipeFamily)
        assert m.answers_question.endswith("?"), f"{e.full_name} must pose its question"
        assert m.required_fields, f"{e.full_name} has no required_fields"


def test_every_recipe_has_demo_contract_callable():
    ensure_all_imported()
    for e in list_recipes():
        obj = e.demo_contract()
        # Accept any instance that passes the pydantic contract (or its raw class).
        assert obj is not None


def test_get_recipe_unknown_key_raises():
    with pytest.raises(KeyError):
        get_recipe("nonexistent.recipe")


def test_modality_description_populated():
    ensure_all_imported()
    for name in list_modalities():
        assert modality_description(name), f"modality {name} missing description"
