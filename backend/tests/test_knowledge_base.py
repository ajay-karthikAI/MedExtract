from app.schemas import EntityGroups, EntityOut
from app.services import extraction, icd10_mapping, knowledge_base
from app.services.paths import knowledge_file_path


def test_local_knowledge_files_exist():
    assert knowledge_file_path("icd10_descriptions.json").exists()
    assert knowledge_file_path("medication_aliases.json").exists()
    assert knowledge_file_path("condition_definitions.json").exists()
    assert knowledge_file_path("clinical_abbreviations.json").exists()


def test_retrieves_matching_abbreviation_and_condition_snippets():
    entity = EntityOut(category="condition", text="HLD", normalized=None, confidence=0.8)

    snippets = knowledge_base.retrieve_for_entity(entity)

    assert snippets
    assert snippets[0].kind == "clinical_abbreviation"
    assert snippets[0].normalized == "hyperlipidemia"
    assert any(snippet.kind == "condition_definition" for snippet in snippets)


def test_knowledge_base_enhances_entity_normalization():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="HLD", normalized=None, confidence=0.82)
        ],
        medications=[
            EntityOut(category="medication", text="Proventil", normalized=None, confidence=0.82)
        ],
    )

    enhanced = knowledge_base.enhance_groups(groups)

    assert [entity.normalized for entity in enhanced.conditions] == ["hyperlipidemia"]
    assert [entity.normalized for entity in enhanced.medications] == ["albuterol"]


def test_knowledge_aliases_seed_candidate_extraction_and_mapping():
    result = extraction.extract("PMH: HLD. Uses Proventil inhaler.")

    assert {entity.normalized for entity in result.conditions} == {"hyperlipidemia"}
    assert {entity.normalized for entity in result.medications} == {"albuterol"}
    assert {suggestion.code for suggestion in result.icd10_suggestions} == {"E78.5"}


def test_icd10_mapping_uses_local_knowledge_aliases():
    groups = EntityGroups(
        conditions=[
            EntityOut(
                category="condition",
                text="essential hypertension",
                normalized="essential hypertension",
                confidence=0.84,
            )
        ]
    )

    suggestions = icd10_mapping.map_icd10(groups)

    assert [suggestion.code for suggestion in suggestions] == ["I10"]
