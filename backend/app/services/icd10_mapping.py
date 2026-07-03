"""ICD-10 suggestion mapping from extracted entity evidence."""

import json
import logging
import re
from functools import lru_cache
from typing import Any

from app.schemas import EntityGroups, EntityOut, Icd10Out
from app.services import confidence, knowledge_base
from app.services.paths import icd10_mapping_path

logger = logging.getLogger(__name__)

CodeHit = tuple[str, str, float]
CodeMap = dict[str, CodeHit]

SYMPTOM_CODES: CodeMap = {
    "chest pain": ("R07.9", "Chest pain, unspecified", 0.82),
    "shortness of breath": ("R06.02", "Shortness of breath", 0.82),
    "dyspnea": ("R06.02", "Shortness of breath", 0.76),
    "cough": ("R05.9", "Cough, unspecified", 0.82),
    "fever": ("R50.9", "Fever, unspecified", 0.82),
    "headache": ("R51.9", "Headache, unspecified", 0.82),
    "fatigue": ("R53.83", "Other fatigue", 0.82),
    "abdominal pain": ("R10.9", "Unspecified abdominal pain", 0.82),
    "dysuria": ("R30.0", "Dysuria", 0.82),
    "nausea and vomiting": ("R11.2", "Nausea with vomiting, unspecified", 0.82),
    "nausea": ("R11.0", "Nausea", 0.82),
    "dizziness": ("R42", "Dizziness and giddiness", 0.82),
    "back pain": ("M54.9", "Dorsalgia, unspecified", 0.82),
    "joint pain": ("M25.50", "Pain in unspecified joint", 0.82),
    "arthralgia": ("M25.50", "Pain in unspecified joint", 0.76),
    "insomnia": ("G47.00", "Insomnia, unspecified", 0.82),
}


def map_icd10(groups: EntityGroups) -> list[Icd10Out]:
    suggestions: dict[str, Icd10Out] = {}
    condition_codes = _condition_codes()
    for entity in groups.conditions:
        _add_code(suggestions, entity, condition_codes, source="condition")
    for entity in groups.symptoms:
        _add_code(suggestions, entity, SYMPTOM_CODES, source="symptom")
    return list(suggestions.values())


@lru_cache
def _condition_codes() -> CodeMap:
    """Load diagnosis mappings from data/icd10_mapping.json."""
    path = icd10_mapping_path()
    code_map: CodeMap = {}
    try:
        raw_entries = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("ICD-10 mapping file not found: %s", path)
        raw_entries = []
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse ICD-10 mapping file %s: %s", path, exc)
        raw_entries = []

    if isinstance(raw_entries, list):
        for entry in raw_entries:
            _add_mapping_entry(code_map, entry)
    else:
        logger.warning("ICD-10 mapping file must contain a list of mapping entries: %s", path)

    try:
        for key, hit in knowledge_base.icd10_code_map().items():
            code_map.setdefault(key, hit)
    except Exception:
        logger.exception("Could not load ICD-10 snippets from local knowledge base")
    return code_map


def _add_mapping_entry(code_map: CodeMap, entry: Any) -> None:
    if not isinstance(entry, dict):
        logger.warning("Skipping malformed ICD-10 mapping entry: %r", entry)
        return

    name = _clean(entry.get("name"))
    code = _clean(entry.get("code"))
    description = _clean(entry.get("description"))
    if not name or not code or not description:
        logger.warning("Skipping incomplete ICD-10 mapping entry: %r", entry)
        return

    exact_hit = (code, description, 0.97)
    code_map[_lookup_key(name)] = exact_hit

    synonyms = entry.get("synonyms", [])
    if isinstance(synonyms, list):
        for synonym in synonyms:
            synonym_key = _lookup_key(_clean(synonym))
            if synonym_key:
                code_map.setdefault(synonym_key, (code, description, 0.9))
    else:
        logger.warning("ICD-10 mapping synonyms must be a list for %s", name)


def _add_code(
    suggestions: dict[str, Icd10Out],
    entity: EntityOut,
    code_map: CodeMap,
    *,
    source: str,
) -> None:
    key, hit = _lookup_code(entity, code_map)
    if hit is None:
        return

    code, description, match_quality = hit
    score = confidence.icd10_confidence(
        entity,
        source=source,
        match_quality=match_quality,
    )
    if score <= 0:
        return

    suggestion = Icd10Out(code=code, description=description, confidence=score)
    current = suggestions.get(code)
    if current is None or suggestion.confidence > current.confidence:
        suggestions[code] = suggestion


def _lookup_code(
    entity: EntityOut,
    code_map: CodeMap,
) -> tuple[str, CodeHit | None]:
    keys = [
        _lookup_key(entity.normalized),
        _lookup_key(entity.text),
    ]
    for key in keys:
        if key in code_map:
            return key, code_map[key]
    return "", None


def _lookup_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""
