"""Local file-backed retrieval for lightweight medical knowledge snippets."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.schemas import EntityGroups, EntityOut
from app.services.paths import knowledge_file_path

logger = logging.getLogger(__name__)

ENTITY_FIELDS: tuple[tuple[str, str], ...] = (
    ("conditions", "condition"),
    ("symptoms", "symptom"),
    ("medications", "medication"),
    ("procedures", "procedure"),
)
VALID_CATEGORIES = {category for _, category in ENTITY_FIELDS}

KNOWLEDGE_FILES = {
    "icd10": "icd10_descriptions.json",
    "medications": "medication_aliases.json",
    "conditions": "condition_definitions.json",
    "abbreviations": "clinical_abbreviations.json",
}


@dataclass(frozen=True)
class KnowledgeSnippet:
    kind: str
    category: str | None
    term: str
    normalized: str
    snippet: str
    aliases: tuple[str, ...] = ()
    code: str | None = None
    description: str | None = None
    match_quality: float = 0.9


CodeHit = tuple[str, str, float]


def retrieve_snippets(
    text: str,
    entities: Iterable[EntityOut],
    *,
    limit_per_entity: int = 4,
) -> dict[str, list[KnowledgeSnippet]]:
    """Retrieve exact local snippets for candidate entities.

    The note text is accepted for the pipeline-facing contract; retrieval is
    intentionally candidate anchored so unrelated note terms do not rewrite
    outputs.
    """
    _ = text
    return {
        _entity_label(entity): retrieve_for_entity(entity, limit=limit_per_entity)
        for entity in entities
    }


def retrieve_for_entity(entity: EntityOut, *, limit: int = 4) -> list[KnowledgeSnippet]:
    keys = [_lookup_key(entity.normalized), _lookup_key(entity.text)]
    matches: dict[tuple[str, str, str | None], KnowledgeSnippet] = {}
    index = _snippet_index()

    for key in keys:
        if not key:
            continue
        for lookup in ((entity.category, key), (None, key)):
            for snippet in index.get(lookup, []):
                if snippet.category not in (None, entity.category):
                    continue
                matches[(snippet.kind, snippet.normalized, snippet.code)] = snippet

    snippets = sorted(matches.values(), key=_snippet_priority)
    return snippets[: max(0, limit)]


def enhance_groups(groups: EntityGroups) -> EntityGroups:
    """Normalize candidate entities with retrieved local snippets."""
    enhanced = [
        _enhance_entity(entity, retrieve_for_entity(entity))
        for entity in _flatten_groups(groups)
    ]
    return _groups_from_entities(_dedupe_entities(enhanced))


def normalize_name(category: str, *, surface: str, normalized: str | None = None) -> str | None:
    """Normalize a candidate name from exact local knowledge aliases."""
    probe = EntityOut(
        category=category,
        text=surface,
        normalized=normalized,
    )
    return _best_normalized_name(probe, retrieve_for_entity(probe)) or normalized


@lru_cache
def category_alias_lexicons() -> dict[str, dict[str, str]]:
    """Return exact-match aliases that can seed candidate extraction."""
    lexicons: dict[str, dict[str, str]] = {category: {} for category in VALID_CATEGORIES}
    for snippet in _all_snippets():
        if snippet.category not in lexicons:
            continue
        for term in _candidate_terms(snippet):
            lexicons[snippet.category][term.lower()] = snippet.normalized
    return lexicons


@lru_cache
def abbreviation_terms() -> frozenset[tuple[str, str]]:
    terms: set[tuple[str, str]] = set()
    for snippet in _abbreviation_snippets():
        if snippet.category:
            for term in _candidate_terms(snippet):
                terms.add((snippet.category, term.lower()))
    return frozenset(terms)


def is_abbreviation(term: str, category: str) -> bool:
    return (category, term.strip().lower()) in abbreviation_terms()


@lru_cache
def icd10_code_map() -> dict[str, CodeHit]:
    """Return local ICD-10 mappings keyed by exact names and aliases."""
    code_map: dict[str, CodeHit] = {}
    for snippet in _icd10_snippets():
        if not snippet.code or not snippet.description:
            continue
        primary_key = _lookup_key(snippet.normalized)
        if primary_key:
            code_map[primary_key] = (
                snippet.code,
                snippet.description,
                max(snippet.match_quality, 0.96),
            )
        for alias in snippet.aliases:
            alias_key = _lookup_key(alias)
            if alias_key:
                code_map.setdefault(alias_key, (snippet.code, snippet.description, 0.9))
    return code_map


@lru_cache
def _snippet_index() -> dict[tuple[str | None, str], list[KnowledgeSnippet]]:
    index: dict[tuple[str | None, str], list[KnowledgeSnippet]] = {}
    for snippet in _all_snippets():
        for term in _candidate_terms(snippet):
            key = _lookup_key(term)
            if not key:
                continue
            index.setdefault((snippet.category, key), []).append(snippet)
            index.setdefault((None, key), []).append(snippet)
    return index


@lru_cache
def _all_snippets() -> tuple[KnowledgeSnippet, ...]:
    return (
        *_icd10_snippets(),
        *_medication_snippets(),
        *_condition_snippets(),
        *_abbreviation_snippets(),
    )


@lru_cache
def _icd10_snippets() -> tuple[KnowledgeSnippet, ...]:
    snippets: list[KnowledgeSnippet] = []
    for entry in _load_entries(KNOWLEDGE_FILES["icd10"]):
        code = _clean(entry.get("code"))
        name = _clean(entry.get("name"))
        description = _clean(entry.get("description"))
        if not code or not name or not description:
            logger.warning("Skipping incomplete ICD-10 knowledge entry: %r", entry)
            continue
        category = _clean(entry.get("category")) or "condition"
        aliases = tuple(_clean_list(entry.get("aliases")))
        snippets.append(
            KnowledgeSnippet(
                kind="icd10_description",
                category=category,
                term=name,
                normalized=name,
                snippet=_clean(entry.get("snippet")) or f"{name}: {description}",
                aliases=aliases,
                code=code,
                description=description,
                match_quality=0.97,
            )
        )
    return tuple(snippets)


@lru_cache
def _medication_snippets() -> tuple[KnowledgeSnippet, ...]:
    snippets: list[KnowledgeSnippet] = []
    for entry in _load_entries(KNOWLEDGE_FILES["medications"]):
        generic = _clean(entry.get("generic"))
        if not generic:
            logger.warning("Skipping medication knowledge entry without generic name: %r", entry)
            continue
        aliases = tuple(_clean_list(entry.get("aliases")))
        snippets.append(
            KnowledgeSnippet(
                kind="medication_alias",
                category="medication",
                term=generic,
                normalized=generic,
                snippet=_clean(entry.get("snippet")) or _medication_snippet(generic, aliases, entry),
                aliases=aliases,
                match_quality=0.95,
            )
        )
    return tuple(snippets)


@lru_cache
def _condition_snippets() -> tuple[KnowledgeSnippet, ...]:
    snippets: list[KnowledgeSnippet] = []
    for entry in _load_entries(KNOWLEDGE_FILES["conditions"]):
        name = _clean(entry.get("name"))
        definition = _clean(entry.get("definition"))
        if not name or not definition:
            logger.warning("Skipping incomplete condition knowledge entry: %r", entry)
            continue
        aliases = tuple(_clean_list(entry.get("aliases")))
        snippets.append(
            KnowledgeSnippet(
                kind="condition_definition",
                category="condition",
                term=name,
                normalized=name,
                snippet=_clean(entry.get("snippet")) or f"{name}: {definition}",
                aliases=aliases,
                match_quality=0.94,
            )
        )
    return tuple(snippets)


@lru_cache
def _abbreviation_snippets() -> tuple[KnowledgeSnippet, ...]:
    snippets: list[KnowledgeSnippet] = []
    for entry in _load_entries(KNOWLEDGE_FILES["abbreviations"]):
        abbreviation = _clean(entry.get("abbreviation"))
        expansion = _clean(entry.get("expansion"))
        category = _clean(entry.get("category"))
        if not abbreviation or not expansion or category not in VALID_CATEGORIES:
            logger.warning("Skipping incomplete abbreviation knowledge entry: %r", entry)
            continue
        aliases = tuple(_clean_list(entry.get("aliases")))
        snippets.append(
            KnowledgeSnippet(
                kind="clinical_abbreviation",
                category=category,
                term=abbreviation,
                normalized=expansion,
                snippet=_clean(entry.get("snippet")) or f"{abbreviation}: {expansion}",
                aliases=aliases,
                match_quality=0.95,
            )
        )
    return tuple(snippets)


def _load_entries(filename: str) -> list[dict[str, Any]]:
    path = knowledge_file_path(filename)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("Knowledge file not found: %s", path)
        return []
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse knowledge file %s: %s", path, exc)
        return []

    if not isinstance(raw, list):
        logger.warning("Knowledge file must contain a list: %s", path)
        return []
    return [entry for entry in raw if isinstance(entry, dict)]


def _candidate_terms(snippet: KnowledgeSnippet) -> tuple[str, ...]:
    terms = [snippet.term, snippet.normalized, *snippet.aliases]
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        cleaned = term.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            deduped.append(cleaned)
    return tuple(deduped)


def _enhance_entity(entity: EntityOut, snippets: list[KnowledgeSnippet]) -> EntityOut:
    normalized = _best_normalized_name(entity, snippets)
    if normalized == entity.normalized:
        return entity
    return entity.model_copy(update={"normalized": normalized})


def _best_normalized_name(entity: EntityOut, snippets: list[KnowledgeSnippet]) -> str | None:
    for kind in (
        "clinical_abbreviation",
        "medication_alias",
        "condition_definition",
        "icd10_description",
    ):
        for snippet in snippets:
            if snippet.kind == kind and snippet.category in (None, entity.category):
                return snippet.normalized
    return entity.normalized


def _dedupe_entities(entities: list[EntityOut]) -> list[EntityOut]:
    best: dict[tuple[str, str], EntityOut] = {}
    for entity in entities:
        key = (entity.category, (entity.normalized or entity.text).lower())
        current = best.get(key)
        if current is None or entity.confidence > current.confidence:
            best[key] = entity
    return sorted(best.values(), key=lambda entity: entity.span_start or 0)


def _flatten_groups(groups: EntityGroups) -> list[EntityOut]:
    return [
        entity
        for field_name, _ in ENTITY_FIELDS
        for entity in getattr(groups, field_name)
    ]


def _groups_from_entities(entities: Iterable[EntityOut]) -> EntityGroups:
    groups = EntityGroups()
    for entity in entities:
        if entity.category in VALID_CATEGORIES:
            getattr(groups, f"{entity.category}s").append(entity)
    return groups


def _snippet_priority(snippet: KnowledgeSnippet) -> tuple[int, str]:
    priority = {
        "clinical_abbreviation": 0,
        "medication_alias": 1,
        "condition_definition": 2,
        "icd10_description": 3,
    }
    return (priority.get(snippet.kind, 10), snippet.normalized.lower())


def _entity_label(entity: EntityOut) -> str:
    return f"{entity.category}:{(entity.normalized or entity.text).lower()}"


def _medication_snippet(generic: str, aliases: tuple[str, ...], entry: dict[str, Any]) -> str:
    drug_class = _clean(entry.get("class"))
    alias_text = f" Aliases: {', '.join(aliases)}." if aliases else ""
    class_text = f" Class: {drug_class}." if drug_class else ""
    return f"{generic}.{alias_text}{class_text}".strip()


def _lookup_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clean_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [cleaned for item in value if (cleaned := _clean(item))]
