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

    assert "hypertension" in summary
    assert "lisinopril" in summary
    assert "not medical advice" in summary


def test_summary_generation_has_empty_findings_fallback():
    summary = summary_generation.generate_patient_summary(EntityGroups())

    assert "could not automatically identify" in summary
    assert "care team" in summary
