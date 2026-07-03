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


def test_overall_confidence_not_stuck_in_fifties_for_exact_evidence():
    entities = [
        EntityOut(
            category="condition",
            text="HTN",
            normalized="hypertension",
            confidence=0.85,
            source="rule",
        )
    ]
    codes = [Icd10Out(code="I10", description="Essential hypertension", confidence=0.779)]

    assert confidence.overall_confidence(entities, codes) >= 0.7


def test_icd10_confidence_is_bounded_by_supporting_entity():
    entity = EntityOut(category="condition", text="hypertension", confidence=0.9)

    assert confidence.icd10_confidence(entity, source="condition") < entity.confidence


def test_exact_rule_entity_confidence_is_high():
    score = confidence.rule_entity_confidence(
        term="hypertension",
        normalized="hypertension",
        text="Assessment: hypertension.",
        span_start=12,
        span_end=24,
        category="condition",
    )

    assert score >= 0.84


def test_abbreviation_rule_entity_confidence_is_high_but_not_perfect():
    score = confidence.rule_entity_confidence(
        term="htn",
        normalized="hypertension",
        text="PMH: HTN.",
        span_start=5,
        span_end=8,
        category="condition",
        is_abbreviation=True,
    )

    assert 0.8 <= score < 0.9


def test_uncertain_rule_entity_confidence_is_low():
    score = confidence.rule_entity_confidence(
        term="hypertension",
        normalized="hypertension",
        text="Assessment: possible hypertension.",
        span_start=21,
        span_end=33,
        category="condition",
    )

    assert score <= 0.52


def test_uncertainty_does_not_leak_across_clauses():
    score = confidence.rule_entity_confidence(
        term="htn",
        normalized="hypertension",
        text="PMH: HTN. Assessment: possible pneumonia.",
        span_start=5,
        span_end=8,
        category="condition",
        is_abbreviation=True,
    )

    assert score >= 0.8


def test_supporting_mentions_raise_confidence():
    single = confidence.rule_entity_confidence(
        term="hypertension",
        normalized="hypertension",
        text="Assessment: hypertension.",
        span_start=12,
        span_end=24,
        category="condition",
        mention_count=1,
    )
    repeated = confidence.rule_entity_confidence(
        term="hypertension",
        normalized="hypertension",
        text="Assessment: hypertension. PMH: hypertension.",
        span_start=12,
        span_end=24,
        category="condition",
        mention_count=2,
    )

    assert repeated > single


def test_model_probability_converts_to_medium_evidence():
    score = confidence.model_entity_confidence(
        probability=0.9,
        text="Assessment: zebroid syndrome.",
        surface="zebroid syndrome",
        span_start=12,
        span_end=28,
        category="condition",
        mention_count=1,
    )

    assert 0.55 <= score <= 0.78


def test_hybrid_confidence_boosts_rule_model_agreement():
    rule = EntityOut(category="condition", text="HTN", normalized="hypertension", confidence=0.84)
    model = EntityOut(category="condition", text="HTN", normalized="hypertension", confidence=0.72)

    assert confidence.hybrid_entity_confidence(rule, model) > model.confidence
    assert confidence.hybrid_entity_confidence(rule, model) >= 0.88


def test_hybrid_confidence_lowers_weak_model_only_evidence():
    model = EntityOut(category="condition", text="rare syndrome", confidence=0.4)

    assert confidence.hybrid_entity_confidence(None, model) < model.confidence


def test_ensemble_agreement_boosts_but_caps_confidence():
    score = confidence.ensemble_agreement_confidence([0.82, 0.84, 0.86], vote_count=3)

    assert score > 0.86
    assert score <= 0.96


def test_ensemble_disagreement_lowers_confidence():
    assert confidence.ensemble_disagreement_confidence(0.8) < 0.8
