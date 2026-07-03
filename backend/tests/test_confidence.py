from app.schemas import EntityOut, Icd10Out
from app.services import confidence


def test_confidence_defaults_do_not_fake_certainty():
    entity = EntityOut(category="condition", text="hypertension")
    code = Icd10Out(code="I10", description="Essential hypertension")

    assert entity.confidence == 0.0
    assert code.confidence == 0.0


def test_overall_confidence_is_zero_without_entities():
    assert confidence.overall_confidence([], []) == 0.0


def test_overall_confidence_reflects_sparse_low_evidence():
    entities = [EntityOut(category="condition", text="hypertension", confidence=0.4)]
    codes = [Icd10Out(code="I10", description="Essential hypertension", confidence=0.3)]

    assert confidence.overall_confidence(entities, codes) < 0.4


def test_icd10_confidence_is_bounded_by_supporting_entity():
    entity = EntityOut(category="condition", text="hypertension", confidence=0.9)

    assert confidence.icd10_confidence(entity, source="condition") < entity.confidence


def test_rule_entity_confidence_stays_below_model_like_certainty():
    score = confidence.rule_entity_confidence(
        term="type 2 diabetes",
        text="Assessment: type 2 diabetes.",
        span_start=12,
        span_end=27,
        category="condition",
    )

    assert 0.0 < score < 0.8
