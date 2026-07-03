from app.services import entity_extraction


def test_entity_extraction_groups_all_categories():
    groups = entity_extraction.extract_entities(
        "Reports chest pain. PMH: hypertension. Continue lisinopril. ECG ordered."
    )

    assert {entity.normalized for entity in groups.symptoms} == {"chest pain"}
    assert {entity.normalized for entity in groups.conditions} == {"hypertension"}
    assert {entity.normalized for entity in groups.medications} == {"lisinopril"}
    assert {entity.normalized for entity in groups.procedures} == {"electrocardiogram"}


def test_dictionary_abbreviations_are_normalized_by_category():
    groups = entity_extraction.extract_entities(
        "Assessment: STEMI with CHF, HTN, and DM2. Patient reports SOB. "
        "Given Lasix. EKG ordered."
    )

    assert {entity.normalized for entity in groups.conditions} == {
        "ST-elevation myocardial infarction",
        "congestive heart failure",
        "hypertension",
        "type 2 diabetes mellitus",
    }
    assert {entity.normalized for entity in groups.symptoms} == {"shortness of breath"}
    assert {entity.normalized for entity in groups.medications} == {"furosemide"}
    assert {entity.normalized for entity in groups.procedures} == {"electrocardiogram"}


def test_dictionary_common_variants_are_normalized():
    groups = entity_extraction.extract_entities(
        "History of heart attack and high blood pressure. "
        "Continue Glucophage. CXR ordered."
    )

    assert {entity.normalized for entity in groups.conditions} == {
        "myocardial infarction",
        "hypertension",
    }
    assert {entity.normalized for entity in groups.medications} == {"metformin"}
    assert {entity.normalized for entity in groups.procedures} == {"chest radiograph"}


def test_dictionary_abbreviations_require_exact_boundaries():
    groups = entity_extraction.extract_entities("Patient was sobbing during the visit.")

    assert groups.symptoms == []


def test_model_payload_entities_use_dictionary_normalization():
    note = "PMH: HTN. Reports SOB."
    payload = {
        "conditions": [
            {
                "category": "condition",
                "text": "HTN",
                "normalized": "htn",
                "span_start": note.index("HTN"),
                "span_end": note.index("HTN") + len("HTN"),
                "confidence": 0.9,
            }
        ],
        "symptoms": [
            {
                "category": "symptom",
                "text": "SOB",
                "normalized": "sob",
                "span_start": note.index("SOB"),
                "span_end": note.index("SOB") + len("SOB"),
                "confidence": 0.9,
            }
        ],
    }

    groups = entity_extraction.normalize_model_payload(note, payload)

    assert {entity.normalized for entity in groups.conditions} == {"hypertension"}
    assert {entity.normalized for entity in groups.symptoms} == {"shortness of breath"}


def test_entity_extraction_skips_negated_symptoms():
    groups = entity_extraction.extract_entities(
        "Patient denies fever or cough but reports shortness of breath."
    )

    assert {entity.normalized for entity in groups.symptoms} == {"shortness of breath"}


def test_entity_extraction_skips_family_history_conditions():
    groups = entity_extraction.extract_entities(
        "Family history of diabetes. Patient has hypertension."
    )

    assert {entity.normalized for entity in groups.conditions} == {"hypertension"}


def test_entity_extraction_does_not_assign_high_rule_confidence():
    groups = entity_extraction.extract_entities("Assessment: type 2 diabetes.")

    assert groups.conditions
    assert max(entity.confidence for entity in groups.conditions) < 0.8


def test_flatten_groups_keeps_response_order():
    groups = entity_extraction.extract_entities(
        "Chest pain with hypertension. Continue metformin. ECG ordered."
    )

    assert [entity.category for entity in entity_extraction.flatten_groups(groups)] == [
        "condition",
        "symptom",
        "medication",
        "procedure",
    ]
