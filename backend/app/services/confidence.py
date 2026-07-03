"""Evidence-weighted confidence helpers for analysis outputs."""

import re

from app.schemas import EntityOut, Icd10Out

RULE_EXACT_BASE = 0.84
RULE_ABBREVIATION_BASE = 0.82
RULE_VARIANT_BASE = 0.78
RULE_ENTITY_MAX = 0.9
UNCERTAIN_ENTITY_MAX = 0.52
AGREEMENT_CONFIDENCE_MIN = 0.88
AGREEMENT_BOOST = 0.1
AGREEMENT_MAX = 0.96
MODEL_ONLY_MAX = 0.78
MODEL_ONLY_WEAK_THRESHOLD = 0.55
MODEL_ONLY_WEAK_FACTOR = 0.75

UNCERTAINTY_TERMS = (
    "possible",
    "possibly",
    "probable",
    "probably",
    "suspected",
    "rule out",
    "r/o",
    "question of",
    "concern for",
)

CONTEXT_TERMS: dict[str, tuple[str, ...]] = {
    "condition": (
        "assessment",
        "diagnosis",
        "diagnoses",
        "dx",
        "history",
        "h/o",
        "pmh",
        "problem list",
    ),
    "symptom": (
        "chief complaint",
        "cc",
        "complains of",
        "hpi",
        "presents with",
        "reports",
    ),
    "medication": (
        "continue",
        "medication",
        "medications",
        "meds",
        "prescribed",
        "rx",
        "start",
        "taking",
    ),
    "procedure": (
        "ordered",
        "performed",
        "plan",
        "procedure",
        "test",
        "tests",
    ),
}

CLAUSE_BOUNDARY = re.compile(r"[.;:\n]")


def clamp_confidence(value: float | int | None, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Return a bounded confidence score rounded consistently."""
    if value is None:
        return minimum
    return round(max(minimum, min(float(value), maximum)), 3)


def _evidence_window(text: str, start: int, end: int, *, width: int = 60) -> str:
    return text[max(0, start - width) : min(len(text), end + width)].lower()


def _canonical(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _mention_bonus(mention_count: int) -> float:
    if mention_count >= 3:
        return 0.05
    if mention_count == 2:
        return 0.03
    return 0.0


def _has_context(window: str, category: str) -> bool:
    return any(cue in window for cue in CONTEXT_TERMS.get(category, ()))


def _has_uncertainty(window: str) -> bool:
    return any(cue in window for cue in UNCERTAINTY_TERMS)


def _has_local_uncertainty(text: str, start: int, end: int) -> bool:
    prefix = text[max(0, start - 50) : start].lower()
    suffix = text[end : min(len(text), end + 35)].lower()
    local_clause = f"{CLAUSE_BOUNDARY.split(prefix)[-1]} {CLAUSE_BOUNDARY.split(suffix)[0]}"
    return _has_uncertainty(local_clause)


def rule_entity_confidence(
    *,
    term: str,
    normalized: str | None = None,
    text: str,
    span_start: int,
    span_end: int,
    category: str,
    mention_count: int = 1,
    is_abbreviation: bool = False,
) -> float:
    """Score dictionary evidence from match type, context, and repeated support."""
    term_key = _canonical(term)
    normalized_key = _canonical(normalized)
    if is_abbreviation:
        score = RULE_ABBREVIATION_BASE
    elif normalized_key and term_key == normalized_key:
        score = RULE_EXACT_BASE
    else:
        score = RULE_VARIANT_BASE

    score += _mention_bonus(mention_count)

    window = _evidence_window(text, span_start, span_end)
    if _has_context(window, category):
        score += 0.03
    if _has_local_uncertainty(text, span_start, span_end):
        score = min(score - 0.25, UNCERTAIN_ENTITY_MAX)
    if len(term_key) <= 3 and not is_abbreviation:
        score -= 0.08

    return clamp_confidence(score, maximum=RULE_ENTITY_MAX)


def model_entity_confidence(
    *,
    probability: float | int | None,
    text: str,
    surface: str,
    span_start: int | None,
    span_end: int | None,
    category: str,
    mention_count: int = 0,
) -> float:
    """Convert model probability into evidence confidence without overclaiming."""
    probability_score = clamp_confidence(probability)
    if probability_score <= 0:
        return 0.0

    valid_span = span_start is not None and span_end is not None and 0 <= span_start < span_end <= len(text)
    lower_text = text.lower()
    surface_key = surface.strip().lower()
    surface_index = lower_text.find(surface_key) if surface_key else -1
    has_text_evidence = valid_span or surface_index >= 0

    score = 0.18 + (probability_score * 0.62)
    if has_text_evidence:
        score += 0.04
    else:
        score *= 0.65

    window = ""
    if valid_span:
        window = _evidence_window(text, span_start, span_end)
    elif surface_index >= 0:
        window = _evidence_window(text, surface_index, surface_index + len(surface_key))

    if window and _has_context(window, category):
        score += 0.02
    score += min(_mention_bonus(mention_count), 0.03)

    if probability_score < MODEL_ONLY_WEAK_THRESHOLD:
        score = min(score * MODEL_ONLY_WEAK_FACTOR, 0.42)
    uncertainty_start = span_start if valid_span else surface_index
    uncertainty_end = span_end if valid_span else surface_index + len(surface_key)
    if uncertainty_start >= 0 and uncertainty_end is not None and _has_local_uncertainty(
        text,
        uncertainty_start,
        uncertainty_end,
    ):
        score = min(score - 0.18, 0.48)

    return clamp_confidence(score, maximum=MODEL_ONLY_MAX)


def icd10_confidence(entity: EntityOut, *, source: str, match_quality: float = 1.0) -> float:
    """Score ICD support from entity confidence and mapping specificity."""
    support = clamp_confidence(entity.confidence)
    if support <= 0:
        return 0.0
    quality = clamp_confidence(match_quality)
    if source == "condition":
        provenance_bonus = {"both": 0.04, "rule": 0.02, "model": 0.0}.get(entity.source, 0.0)
        return clamp_confidence((support * 0.92 * quality) + provenance_bonus, maximum=0.93)
    return clamp_confidence(support * 0.7 * quality, maximum=0.72)


def hybrid_entity_confidence(rule_entity: EntityOut | None, model_entity: EntityOut | None) -> float:
    """Score merged entities based on independent supporting evidence."""
    if rule_entity is not None and model_entity is not None:
        support = max(
            clamp_confidence(rule_entity.confidence),
            clamp_confidence(model_entity.confidence),
        )
        if support < MODEL_ONLY_WEAK_THRESHOLD:
            return clamp_confidence(support + 0.12, maximum=0.72)
        return clamp_confidence(
            max(AGREEMENT_CONFIDENCE_MIN, support + AGREEMENT_BOOST),
            maximum=AGREEMENT_MAX,
        )

    if rule_entity is not None:
        return clamp_confidence(rule_entity.confidence, maximum=RULE_ENTITY_MAX)

    if model_entity is None:
        return 0.0

    support = clamp_confidence(model_entity.confidence)
    if support < MODEL_ONLY_WEAK_THRESHOLD:
        return clamp_confidence(support * MODEL_ONLY_WEAK_FACTOR, maximum=0.45)
    return clamp_confidence(support, maximum=MODEL_ONLY_MAX)


def ensemble_agreement_confidence(confidences: list[float], *, vote_count: int) -> float:
    """Boost only when independent framework entity votes agree."""
    if not confidences:
        return 0.0
    support = max(clamp_confidence(score) for score in confidences)
    boost = min(0.08, 0.04 * max(0, vote_count - 1))
    return clamp_confidence(support + boost, maximum=AGREEMENT_MAX)


def ensemble_disagreement_confidence(confidence: float) -> float:
    """Lower confidence when an entity is not confirmed by other active frameworks."""
    return clamp_confidence(clamp_confidence(confidence) * 0.86, maximum=0.82)


def overall_confidence(entities: list[EntityOut], icd_codes: list[Icd10Out]) -> float:
    """Aggregate confidence from entity evidence, agreement, and ICD quality."""
    if not entities:
        return 0.0

    entity_scores = [clamp_confidence(entity.confidence) for entity in entities]
    entity_mean = sum(entity_scores) / len(entity_scores)
    strongest_entities = sorted(entity_scores, reverse=True)[:3]
    strongest_mean = sum(strongest_entities) / len(strongest_entities)

    if icd_codes:
        code_scores = [clamp_confidence(code.confidence) for code in icd_codes]
        code_mean = sum(code_scores) / len(code_scores)
    else:
        code_mean = 0.0

    agreement_ratio = sum(
        1 for entity in entities if entity.source in {"both", "ensemble_agreement"}
    ) / len(entities)
    model_only_ratio = sum(1 for entity in entities if entity.source == "model") / len(entities)
    evidence_factor = min(
        1.0,
        0.82 + (0.04 * len(entities)) + (0.025 * len(icd_codes)) + (0.04 * agreement_ratio),
    )

    score = (
        (entity_mean * 0.64)
        + (strongest_mean * 0.12)
        + (code_mean * 0.2)
        + (agreement_ratio * 0.04)
    )
    if not icd_codes:
        score *= 0.88
    score *= evidence_factor
    score -= model_only_ratio * 0.04
    return clamp_confidence(score, maximum=0.95)
