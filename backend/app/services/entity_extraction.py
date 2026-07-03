"""Entity extraction and normalization for MedExtract analysis."""

import logging
import re
from collections.abc import Iterable

from app.schemas import EntityGroups, EntityOut, ExtractionResult
from app.services import confidence, medical_dictionary

logger = logging.getLogger(__name__)

EntityLexicon = medical_dictionary.EntityLexicon

LEXICONS = medical_dictionary.CATEGORY_LEXICONS
GROUP_FIELDS: tuple[tuple[str, str], ...] = (
    ("conditions", "condition"),
    ("symptoms", "symptom"),
    ("medications", "medication"),
    ("procedures", "procedure"),
)

VALID_CATEGORIES = {category for category, _ in LEXICONS}
NEGATED_CATEGORIES = {"condition", "symptom", "medication", "procedure"}
CLAUSE_BOUNDARY = re.compile(r"[.;:\n]")
NEGATION_CUES = (
    "denies",
    "denied",
    "negative for",
    "no",
    "no evidence of",
    "not experiencing",
    "not taking",
    "without",
)
NEGATION_CANCELERS = (" but ", " however ", " though ", " although ", " except ")
FAMILY_HISTORY = re.compile(r"\bfamily history of\s+$")


def flatten_groups(groups: EntityGroups) -> list[EntityOut]:
    return groups.conditions + groups.symptoms + groups.medications + groups.procedures


def groups_from_entities(entities: Iterable[EntityOut]) -> EntityGroups:
    groups = EntityGroups()
    for entity in entities:
        if entity.category in VALID_CATEGORIES:
            getattr(groups, f"{entity.category}s").append(entity)
    return groups


def extract_entities(text: str) -> EntityGroups:
    """Extract rule-based entities using longest-match span search."""
    entities: list[EntityOut] = []
    for category, lexicon in LEXICONS:
        entities.extend(_find_terms(text, lexicon, category))
    return groups_from_entities(_dedupe(entities))


def normalize_model_entities(text: str, result: ExtractionResult) -> EntityGroups:
    """Use only entity evidence from a model-shaped response."""
    return normalize_model_payload(text, result)


def normalize_model_payload(text: str, payload: object) -> EntityGroups:
    """Extract entity evidence from a model payload, ignoring non-entity fields."""
    entities: list[EntityOut] = []
    for field_name, category in GROUP_FIELDS:
        for item in _payload_items(payload, field_name):
            entity = _entity_from_model_item(item, category)
            if entity is not None:
                entities.append(entity)

    sanitized: list[EntityOut] = []
    for entity in entities:
        normalized = _sanitize_model_entity(text, entity)
        if normalized is not None:
            sanitized.append(normalized)
    return groups_from_entities(_dedupe(sanitized))


def extract_with_model_payload(text: str, payload: object) -> EntityGroups:
    """Merge model entity evidence with the rule-based dictionary layer."""
    model_entities = flatten_groups(normalize_model_payload(text, payload))
    dictionary_entities = flatten_groups(extract_entities(text))
    return groups_from_entities(_dedupe(model_entities + dictionary_entities))


def _find_terms(text: str, lexicon: EntityLexicon, category: str) -> list[EntityOut]:
    lower = text.lower()
    found: list[EntityOut] = []
    claimed: list[tuple[int, int]] = []

    for term in sorted(lexicon, key=len, reverse=True):
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            span = (match.start(), match.end())
            if any(start < span[1] and span[0] < end for start, end in claimed):
                continue
            if _is_context_excluded(text, span[0], category):
                continue
            claimed.append(span)
            found.append(
                EntityOut(
                    category=category,
                    text=text[span[0] : span[1]],
                    normalized=medical_dictionary.normalize(
                        category,
                        surface=text[span[0] : span[1]],
                        normalized=lexicon[term],
                    ),
                    span_start=span[0],
                    span_end=span[1],
                    confidence=confidence.rule_entity_confidence(
                        term=term,
                        text=text,
                        span_start=span[0],
                        span_end=span[1],
                        category=category,
                    ),
                )
            )
    return found


def _payload_items(payload: object, field_name: str) -> list[object]:
    if isinstance(payload, ExtractionResult):
        items = getattr(payload, field_name)
    elif isinstance(payload, dict):
        items = payload.get(field_name, [])
    else:
        items = getattr(payload, field_name, [])
    if items is None:
        return []
    if isinstance(items, (str, bytes)) or not isinstance(items, Iterable):
        raise ValueError(f"Model payload field {field_name!r} must be a list of entities")
    return list(items)


def _entity_from_model_item(item: object, category: str) -> EntityOut | None:
    if isinstance(item, EntityOut):
        data = item.model_dump()
    elif isinstance(item, dict):
        data = {**item}
    else:
        try:
            data = EntityOut.model_validate(item).model_dump()
        except Exception as exc:
            logger.warning("Dropping malformed model entity: %s", exc)
            return None

    data.setdefault("category", category)
    try:
        return EntityOut.model_validate(data)
    except Exception as exc:
        logger.warning("Dropping malformed model entity: %s", exc)
        return None


def _sanitize_model_entity(text: str, entity: EntityOut) -> EntityOut | None:
    if entity.category not in VALID_CATEGORIES:
        logger.info("Dropping entity with unsupported category: %s", entity.category)
        return None

    span_start = entity.span_start
    span_end = entity.span_end
    surface = entity.text.strip()
    if span_start is not None and span_end is not None and 0 <= span_start < span_end <= len(text):
        surface = text[span_start:span_end].strip() or surface
        if _is_context_excluded(text, span_start, entity.category):
            return None
    if not surface:
        return None

    return EntityOut(
        category=entity.category,
        text=surface,
        normalized=medical_dictionary.normalize(
            entity.category,
            surface=surface,
            normalized=entity.normalized,
        ),
        span_start=span_start,
        span_end=span_end,
        confidence=confidence.clamp_confidence(entity.confidence),
    )


def _dedupe(entities: list[EntityOut]) -> list[EntityOut]:
    best: dict[tuple[str, str], EntityOut] = {}
    for entity in entities:
        key = (entity.category, entity.normalized or entity.text.lower())
        current = best.get(key)
        if current is None or entity.confidence > current.confidence:
            best[key] = entity
    return sorted(best.values(), key=lambda entity: entity.span_start or 0)


def _is_context_excluded(text: str, span_start: int, category: str) -> bool:
    prefix = text[max(0, span_start - 100) : span_start].lower()
    clause = CLAUSE_BOUNDARY.split(prefix)[-1]

    if category == "condition" and FAMILY_HISTORY.search(clause):
        return True
    if category not in NEGATED_CATEGORIES:
        return False

    cue_positions = [
        match.start()
        for cue in NEGATION_CUES
        for match in re.finditer(rf"\b{re.escape(cue)}\b", clause)
    ]
    last_cue = max(cue_positions, default=-1)
    if last_cue < 0:
        return False

    after_cue = clause[last_cue:]
    if any(cancel in after_cue for cancel in NEGATION_CANCELERS):
        return False
    words_after_cue = re.findall(r"[a-z0-9]+", after_cue)
    return len(words_after_cue) <= 10
