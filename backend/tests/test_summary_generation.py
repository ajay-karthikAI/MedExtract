from app.schemas import EntityGroups, EntityOut
from app.services import summary_generation


def test_summary_generation_uses_structured_entities():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="hypertension", normalized="hypertension", confidence=0.6)
        ],
        medications=[
            EntityOut(category="medication", text="lisinopril", normalized="lisinopril", confidence=0.6)
        ],
    )

    summary = summary_generation.generate_patient_summary(groups)

    assert "high blood pressure" in summary
    assert "lisinopril" in summary
    assert "not medical advice" in summary
    assert "not medical advice or a diagnosis" in summary


def test_summary_generation_has_empty_findings_fallback():
    summary = summary_generation.generate_patient_summary(EntityGroups())

    assert "Main problems mentioned in the note: none identified" in summary
    assert "Follow-up instructions found in the note: none identified" in summary
    assert "not medical advice or a diagnosis" in summary


def test_summary_generation_uses_plain_language_and_follow_up_from_note():
    groups = EntityGroups(
        conditions=[
            EntityOut(
                category="condition",
                text="STEMI",
                normalized="ST-elevation myocardial infarction",
                confidence=0.85,
            )
        ],
        symptoms=[
            EntityOut(category="symptom", text="SOB", normalized="shortness of breath", confidence=0.82)
        ],
        medications=[
            EntityOut(category="medication", text="Lasix", normalized="furosemide", confidence=0.82)
        ],
        procedures=[
            EntityOut(
                category="procedure",
                text="EKG",
                normalized="electrocardiogram",
                confidence=0.82,
            )
        ],
    )

    summary = summary_generation.generate_patient_summary(
        groups,
        "Assessment: STEMI with SOB. Given Lasix. EKG done. "
        "Plan: follow up with cardiology in 1 week.",
    )

    assert "serious heart attack" in summary
    assert "shortness of breath" in summary
    assert "furosemide" in summary
    assert "heart tracing test" in summary
    assert "follow up with cardiology in 1 week" in summary
    assert "ST-elevation myocardial infarction" not in summary
    assert "electrocardiogram" not in summary


def test_summary_generation_does_not_turn_visit_reason_into_instruction():
    groups = EntityGroups(
        conditions=[
            EntityOut(category="condition", text="pneumonia", normalized="pneumonia", confidence=0.8)
        ]
    )

    summary = summary_generation.generate_patient_summary(
        groups,
        "Pneumonia follow-up: cough persists. Amoxicillin prescribed.",
    )

    assert "Follow-up instructions found in the note: none identified" in summary
    assert "please talk to your doctor" not in summary
    assert "care team" not in summary
