import json

from app.schemas import EntityGroups, EntityOut
from app.services import icd10_mapping
from app.services.paths import icd10_mapping_path


def test_local_icd10_mapping_file_contains_requested_diagnoses():
    path = icd10_mapping_path()
    entries = json.loads(path.read_text(encoding="utf-8"))
    codes = {entry["code"] for entry in entries}

    assert {
        "E11.9",
        "I10",
        "E78.5",
        "J18.9",
        "J45.909",
        "I50.9",
        "I21.3",
        "F32.9",
        "G43.909",
        "N39.0",
    }.issubset(codes)


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
    assert 0.5 < codes["I10"].confidence < 0.65


def test_icd10_mapping_keeps_stronger_duplicate_code_evidence():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="high blood pressure", normalized="hypertension", confidence=0.4),
            EntityOut(category="condition", text="hypertension", normalized="hypertension", confidence=0.7),
        ]
    )

    suggestions = icd10_mapping.map_icd10(groups)

    assert [suggestion.code for suggestion in suggestions] == ["I10"]
    assert suggestions[0].confidence == 0.645


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


def test_icd10_mapping_uses_condition_synonyms_from_json():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="DM2", normalized=None, confidence=0.8),
            EntityOut(category="condition", text="STEMI", normalized=None, confidence=0.8),
            EntityOut(category="condition", text="UTI", normalized=None, confidence=0.8),
        ]
    )

    assert {suggestion.code for suggestion in icd10_mapping.map_icd10(groups)} == {
        "E11.9",
        "I21.3",
        "N39.0",
    }


def test_icd10_mapping_covers_common_dictionary_conditions():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="COPD", normalized="chronic obstructive pulmonary disease", confidence=0.84),
            EntityOut(category="condition", text="AFib", normalized="atrial fibrillation", confidence=0.84),
            EntityOut(category="condition", text="GERD", normalized="gastroesophageal reflux disease", confidence=0.84),
            EntityOut(category="condition", text="anemia", normalized="anemia", confidence=0.84),
            EntityOut(category="condition", text="hypothyroidism", normalized="hypothyroidism", confidence=0.84),
            EntityOut(category="condition", text="anxiety", normalized="anxiety disorder", confidence=0.84),
            EntityOut(category="condition", text="osteoarthritis", normalized="osteoarthritis", confidence=0.84),
            EntityOut(category="condition", text="ACS", normalized="acute coronary syndrome", confidence=0.84),
        ]
    )

    assert {suggestion.code for suggestion in icd10_mapping.map_icd10(groups)} == {
        "J44.9",
        "I48.91",
        "K21.9",
        "D64.9",
        "E03.9",
        "F41.9",
        "M19.90",
        "I24.9",
    }
