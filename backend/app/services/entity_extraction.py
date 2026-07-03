"""Entity extraction and normalization for MedExtract analysis."""

import logging
import re
from collections.abc import Iterable

from app.schemas import EntityGroups, EntityOut, ExtractionResult
from app.services import confidence, knowledge_base, medical_dictionary

logger = logging.getLogger(__name__)

EntityLexicon = medical_dictionary.EntityLexicon

def _combined_lexicons() -> tuple[tuple[str, EntityLexicon], ...]:
    lexicons = {
        category: dict(lexicon)
        for category, lexicon in medical_dictionary.CATEGORY_LEXICONS
    }
    try:
        for category, aliases in knowledge_base.category_alias_lexicons().items():
            if category in lexicons:
                lexicons[category].update(aliases)
    except Exception:
        logger.exception("Could not load local knowledge aliases; using base dictionaries")
    return tuple((category, lexicons[category]) for category, _ in medical_dictionary.CATEGORY_LEXICONS)


LEXICONS = _combined_lexicons()
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
MEDICATION_ALLERGY_CONTEXT = re.compile(r"\b(allerg(?:y|ies|ic)|adverse reaction)\b")
INSULIN_NON_MEDICATION_CONTEXT = re.compile(r"^\s*(?:resistance|resistant|-resistant)\b")


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
    """Hybrid extraction: rules first, model second, then provenance-aware merge."""
    rule_groups = extract_entities(text)
    model_groups = normalize_model_payload(text, payload)
    return merge_entity_groups(rule_groups, model_groups)


def merge_entity_groups(rule_groups: EntityGroups, model_groups: EntityGroups) -> EntityGroups:
    """Merge duplicates while preserving whether evidence came from rules, model, or both."""
    rule_entities = {_entity_key(entity): entity for entity in flatten_groups(rule_groups)}
    model_entities = {_entity_key(entity): entity for entity in flatten_groups(model_groups)}

    merged: list[EntityOut] = []
    for key in sorted(
        set(rule_entities) | set(model_entities),
        key=lambda item: _sort_position(rule_entities.get(item) or model_entities.get(item)),
    ):
        merged.append(_merge_pair(rule_entities.get(key), model_entities.get(key)))
    return groups_from_entities(merged)


def _find_terms(text: str, lexicon: EntityLexicon, category: str) -> list[EntityOut]:
    lower = text.lower()
    found: list[EntityOut] = []
    claimed: list[tuple[int, int]] = []
    mention_counts = _normalized_mention_counts(text, lexicon, category)

    for term in sorted(lexicon, key=len, reverse=True):
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            span = (match.start(), match.end())
            if any(start < span[1] and span[0] < end for start, end in claimed):
                continue
            if _is_context_excluded(text, span[0], category):
                continue
            surface = text[span[0] : span[1]]
            normalized = _normalize_entity_name(
                category,
                surface=surface,
                normalized=lexicon[term],
            )
            claimed.append(span)
            found.append(
                EntityOut(
                    category=category,
                    text=surface,
                    normalized=normalized,
                    span_start=span[0],
                    span_end=span[1],
                    confidence=confidence.rule_entity_confidence(
                        term=term,
                        normalized=normalized,
                        text=text,
                        span_start=span[0],
                        span_end=span[1],
                        category=category,
                        mention_count=mention_counts.get(normalized.lower(), 1),
                        is_abbreviation=_is_abbreviation(term, category),
                    ),
                    source="rule",
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
        normalized=_normalize_entity_name(
            entity.category,
            surface=surface,
            normalized=entity.normalized,
        ),
        span_start=span_start,
        span_end=span_end,
        confidence=confidence.model_entity_confidence(
            probability=entity.confidence,
            text=text,
            surface=surface,
            span_start=span_start,
            span_end=span_end,
            category=entity.category,
            mention_count=_count_surface_mentions(text, surface),
        ),
        source="model",
    )


def _entity_key(entity: EntityOut) -> tuple[str, str]:
    return (entity.category, (entity.normalized or entity.text).lower())


def _sort_position(entity: EntityOut | None) -> tuple[int, str]:
    if entity is None:
        return (10**9, "")
    return (entity.span_start if entity.span_start is not None else 10**9, entity.text.lower())


def _merge_pair(rule_entity: EntityOut | None, model_entity: EntityOut | None) -> EntityOut:
    if rule_entity is not None and model_entity is not None:
        source = "both"
    elif rule_entity is not None:
        source = "rule"
    else:
        source = "model"
    primary = rule_entity or model_entity
    secondary = model_entity if rule_entity is not None else None
    if primary is None:
        raise ValueError("Cannot merge missing entities")

    return EntityOut(
        category=primary.category,
        text=primary.text,
        normalized=primary.normalized or (secondary.normalized if secondary else None),
        span_start=primary.span_start,
        span_end=primary.span_end,
        confidence=confidence.hybrid_entity_confidence(rule_entity, model_entity),
        source=source,
    )


def _dedupe(entities: list[EntityOut]) -> list[EntityOut]:
    best: dict[tuple[str, str], EntityOut] = {}
    for entity in entities:
        key = (entity.category, (entity.normalized or entity.text).lower())
        current = best.get(key)
        if current is None or entity.confidence > current.confidence:
            best[key] = entity
    return sorted(best.values(), key=lambda entity: entity.span_start or 0)


def _normalize_entity_name(category: str, *, surface: str, normalized: str | None = None) -> str:
    dictionary_name = medical_dictionary.normalize(
        category,
        surface=surface,
        normalized=normalized,
    )
    return knowledge_base.normalize_name(
        category,
        surface=surface,
        normalized=dictionary_name,
    ) or dictionary_name


def _is_abbreviation(term: str, category: str) -> bool:
    match = medical_dictionary.ABBREVIATIONS.get(term.lower())
    return (match is not None and match[0] == category) or knowledge_base.is_abbreviation(
        term,
        category,
    )


def _normalized_mention_counts(
    text: str,
    lexicon: EntityLexicon,
    category: str,
) -> dict[str, int]:
    lower = text.lower()
    spans_by_normalized: dict[str, list[tuple[int, int]]] = {}

    for term in sorted(lexicon, key=len, reverse=True):
        normalized = medical_dictionary.normalize(category, surface=term, normalized=lexicon[term]).lower()
        spans = spans_by_normalized.setdefault(normalized, [])
        for match in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            span = (match.start(), match.end())
            if any(start < span[1] and span[0] < end for start, end in spans):
                continue
            spans.append(span)

    return {normalized: len(spans) for normalized, spans in spans_by_normalized.items()}


def _count_surface_mentions(text: str, surface: str) -> int:
    term = surface.strip().lower()
    if not term:
        return 0
    return sum(1 for _ in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text.lower()))


def _is_context_excluded(text: str, span_start: int, category: str) -> bool:
    prefix = text[max(0, span_start - 100) : span_start].lower()
    clause = CLAUSE_BOUNDARY.split(prefix)[-1]

    if category == "condition" and FAMILY_HISTORY.search(clause):
        return True
    if category == "medication":
        suffix = text[span_start : min(len(text), span_start + 40)].lower()
        medication_context = re.split(r"[.;\n]", prefix)[-1]
        if MEDICATION_ALLERGY_CONTEXT.search(medication_context):
            return True
        if text[span_start : span_start + len("insulin")].lower() == "insulin" and INSULIN_NON_MEDICATION_CONTEXT.match(
            suffix[len("insulin") :]
        ):
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
