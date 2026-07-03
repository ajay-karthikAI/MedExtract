"""Evidence-weighted confidence helpers for analysis outputs."""

from app.schemas import EntityOut, Icd10Out

RULE_ENTITY_MAX = 0.78
RULE_ENTITY_MIN = 0.35

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


def clamp_confidence(value: float | int | None, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
    """Return a bounded confidence score rounded consistently."""
    if value is None:
        return minimum
    return round(max(minimum, min(float(value), maximum)), 3)


def _evidence_window(text: str, start: int, end: int, *, width: int = 60) -> str:
    return text[max(0, start - width) : min(len(text), end + width)].lower()


def rule_entity_confidence(
    *,
    term: str,
    text: str,
    span_start: int,
    span_end: int,
    category: str,
) -> float:
    """Score a rule-based entity without pretending it has model certainty."""
    normalized = term.strip().lower()
    score = 0.56
    if " " in normalized or "-" in normalized:
        score += 0.06

    window = _evidence_window(text, span_start, span_end)
    if any(cue in window for cue in CONTEXT_TERMS.get(category, ())):
        score += 0.04
    if any(cue in window for cue in UNCERTAINTY_TERMS):
        score -= 0.12
    if len(normalized) <= 3:
        score -= 0.03

    return clamp_confidence(score, minimum=RULE_ENTITY_MIN, maximum=RULE_ENTITY_MAX)


def icd10_confidence(entity: EntityOut, *, source: str) -> float:
    """Code confidence is bounded by the supporting entity evidence."""
    support = clamp_confidence(entity.confidence)
    if support <= 0:
        return 0.0
    if source == "condition":
        return clamp_confidence(support * 0.78, maximum=0.78)
    return clamp_confidence(support * 0.56, maximum=0.58)


def overall_confidence(entities: list[EntityOut], icd_codes: list[Icd10Out]) -> float:
    """Aggregate confidence while penalizing sparse or weak evidence."""
    if not entities:
        return 0.0

    entity_scores = [clamp_confidence(entity.confidence) for entity in entities]
    entity_mean = sum(entity_scores) / len(entity_scores)

    if icd_codes:
        code_scores = [clamp_confidence(code.confidence) for code in icd_codes]
        code_mean = sum(code_scores) / len(code_scores)
    else:
        code_mean = entity_mean * 0.65

    evidence_count = len(entities) + len(icd_codes)
    coverage_factor = min(1.0, 0.65 + (0.05 * evidence_count))
    score = ((entity_mean * 0.7) + (code_mean * 0.3)) * coverage_factor
    return clamp_confidence(score, maximum=0.92)
