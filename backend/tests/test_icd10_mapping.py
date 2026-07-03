from app.schemas import EntityGroups, EntityOut
from app.services import icd10_mapping


def test_maps_conditions_and_symptoms_to_codes():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="hypertension", normalized="hypertension", confidence=0.6)
        ],
        symptoms=[
            EntityOut(category="symptom", text="chest pain", normalized="chest pain", confidence=0.6)
        ],
    )

    codes = {suggestion.code: suggestion for suggestion in icd10_mapping.map_icd10(groups)}

    assert set(codes) == {"I10", "R07.9"}
    assert codes["I10"].confidence > codes["R07.9"].confidence
    assert codes["I10"].confidence < 0.5


def test_icd10_mapping_keeps_stronger_duplicate_code_evidence():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="high blood pressure", normalized="hypertension", confidence=0.4),
            EntityOut(category="condition", text="hypertension", normalized="hypertension", confidence=0.7),
        ]
    )

    suggestions = icd10_mapping.map_icd10(groups)

    assert [suggestion.code for suggestion in suggestions] == ["I10"]
    assert suggestions[0].confidence == 0.546


def test_icd10_mapping_omits_unmapped_entities():
    groups = EntityGroups(
        medications=[
            EntityOut(category="medication", text="lisinopril", normalized="lisinopril", confidence=0.7)
        ]
    )

    assert icd10_mapping.map_icd10(groups) == []


def test_icd10_mapping_handles_dictionary_normalized_cardiac_terms():
    groups = EntityGroups(
        conditions=[
            EntityOut(
                category="condition",
                text="STEMI",
                normalized="ST-elevation myocardial infarction",
                confidence=0.7,
            ),
            EntityOut(
                category="condition",
                text="CHF",
                normalized="congestive heart failure",
                confidence=0.7,
            ),
        ]
    )

    assert {suggestion.code for suggestion in icd10_mapping.map_icd10(groups)} == {
        "I21.3",
        "I50.9",
    }
