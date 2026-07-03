"""Backend analysis orchestrator.

The public `extract(text)` shape is unchanged, but the work is intentionally
split: entity extraction, ICD-10 mapping, summary generation, and confidence
scoring live in separate modules.
"""

import logging

from app.schemas import EntityGroups, ExtractionResult
from app.services import entity_extraction, icd10_mapping, summary_generation

logger = logging.getLogger(__name__)

MODEL_NAME = "rule-based-v0"


def build_result(groups: EntityGroups, *, model_name: str = MODEL_NAME) -> ExtractionResult:
    """Compose an API-compatible extraction result from entity groups."""
    icd10_suggestions = icd10_mapping.map_icd10(groups)
    return ExtractionResult(
        conditions=groups.conditions,
        symptoms=groups.symptoms,
        medications=groups.medications,
        procedures=groups.procedures,
        icd10_suggestions=icd10_suggestions,
        patient_summary=summary_generation.generate_patient_summary(groups),
        model_name=model_name,
    )


def extract(text: str) -> ExtractionResult:
    """Rule-based fallback extraction with explicit empty-result behavior."""
    try:
        groups = entity_extraction.extract_entities(text)
    except Exception:
        logger.exception("Rule-based entity extraction failed; returning empty analysis")
        groups = EntityGroups()
    return build_result(groups, model_name=MODEL_NAME)
