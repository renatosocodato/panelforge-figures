"""Recipe registry and metadata."""

import pytest

from panelforge_figures.core.aesthetic_base import ModalityAesthetic
from panelforge_figures.core.contract import (
    RecipeFamily,
    ensure_all_imported,
    get_recipe,
    list_modalities,
    list_recipes,
    modality_aesthetic,
    modality_description,
    register_modality,
    registry_counts,
)


def test_registry_has_at_least_18_recipes():
    ensure_all_imported()
    assert len(list_recipes()) >= 18


def test_each_modality_has_its_recipes_registered():
    ensure_all_imported()
    counts = registry_counts()
    assert counts["grant_and_conceptual"] == 17
    assert counts["meta_and_diagnostic"] == 35
    assert counts["sensitivity_analysis"] == 16


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


# ---------------------------------------------------------------------------
# register_modality aesthetic type enforcement (structural-debt item #15)
# ---------------------------------------------------------------------------

def test_register_modality_rejects_non_aesthetic_object():
    """A bogus aesthetic must raise TypeError at registration, not surface
    later as an AttributeError deep inside a recipe's ``apply_to_ax`` call.

    Before this fix the untyped boundary stored any object silently.
    """
    class NotAnAesthetic:
        pass

    with pytest.raises(TypeError) as excinfo:
        register_modality(
            "__bogus_aesthetic_modality__",
            "should never register",
            aesthetic=NotAnAesthetic(),
        )
    assert "ModalityAesthetic" in str(excinfo.value)
    # The rejected modality must not have leaked into the aesthetic registry.
    assert modality_aesthetic("__bogus_aesthetic_modality__") is None
    # ...nor into the description registry: registration is atomic, so a
    # rejected call leaves NO partial state (the type check runs before any
    # registry mutation).
    assert modality_description("__bogus_aesthetic_modality__") == ""


def test_register_modality_rejects_dict_lookalike():
    """A dict that quacks like an aesthetic config is still rejected — the
    boundary enforces the actual ModalityAesthetic type, not duck-typing.
    """
    with pytest.raises(TypeError):
        register_modality(
            "__bogus_dict_modality__",
            "should never register",
            aesthetic={"modality_name": "x", "primary_palette": "y"},
        )


def test_register_modality_accepts_valid_aesthetic_and_none():
    """A real ModalityAesthetic registers; None is accepted (no aesthetic)."""
    aesthetic = ModalityAesthetic(
        modality_name="__valid_aesthetic_modality__",
        primary_palette="journal_neutral",
    )
    register_modality(
        "__valid_aesthetic_modality__",
        "valid aesthetic",
        aesthetic=aesthetic,
    )
    assert modality_aesthetic("__valid_aesthetic_modality__") is aesthetic

    # None is the no-aesthetic path and must not raise.
    register_modality("__no_aesthetic_modality__", "no aesthetic")
    assert modality_aesthetic("__no_aesthetic_modality__") is None


def test_all_real_modalities_register_a_valid_aesthetic():
    """Every shipped modality that declares an aesthetic passes a real
    ModalityAesthetic, so the new type gate does not reject any of them.
    """
    ensure_all_imported()
    for name in list_modalities():
        aes = modality_aesthetic(name)
        assert aes is None or isinstance(aes, ModalityAesthetic)
