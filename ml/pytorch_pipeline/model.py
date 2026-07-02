"""Model layer for the PyTorch clinical NLP pipeline.

Three concerns live here:
1. NER model resolution/loading (fine-tuned checkpoint if present, otherwise a
   small pretrained biomedical transformer from the Hugging Face Hub).
2. Mapping model label spaces onto MedExtract's four entity categories.
3. ICD-10 suggestion — currently a dictionary-lookup placeholder standing in
   for a trained code-classification head.
"""

import os
from pathlib import Path

# Small biomedical NER model (DistilBERT fine-tuned on MACCROBAT, ~66M params).
DEFAULT_MODEL = "d4data/biomedical-ner-all"
CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints" / "medextract-ner"

CATEGORIES = ("condition", "symptom", "medication", "procedure")
# BIO scheme used by train.py for fine-tuned checkpoints.
BIO_LABELS = ["O"] + [f"{prefix}-{cat}" for cat in CATEGORIES for prefix in ("B", "I")]

# Model label (lowercased, B-/I- stripped) -> MedExtract category. Covers both
# our fine-tuned scheme and the MACCROBAT label space of the default model;
# unmapped labels (lab values, durations, …) are intentionally dropped.
# MACCROBAT tags past-condition mentions ("History of hypertension") as History.
LABEL_TO_CATEGORY: dict[str, str] = {
    "condition": "condition",
    "symptom": "symptom",
    "medication": "medication",
    "procedure": "procedure",
    "disease_disorder": "condition",
    "history": "condition",
    "sign_symptom": "symptom",
    "diagnostic_procedure": "procedure",
    "therapeutic_procedure": "procedure",
}

# Anatomy spans aren't entities themselves, but a structure directly before a
# symptom composes with it ("chest" + "pain" -> "chest pain").
STRUCTURE_LABELS = {"biological_structure"}

MIN_SCORE = 0.5


def resolve_model_id() -> str:
    """Which model inference will load, without loading it."""
    override = os.environ.get("MEDEXTRACT_PT_MODEL")
    if override:
        return override
    if (CHECKPOINT_DIR / "config.json").exists():
        return str(CHECKPOINT_DIR)
    return DEFAULT_MODEL


def load_ner_pipeline():
    """Load the token-classification pipeline (CPU; heavy imports kept lazy)."""
    from transformers import pipeline

    model_id = resolve_model_id()
    return (
        pipeline(
            "token-classification",
            model=model_id,
            # "first" aggregates at word level, avoiding subword fragments
            # ("li"/"sin"/"opril"); "simple" splits on B-/I- boundaries.
            aggregation_strategy="first",
            device=-1,
        ),
        model_id,
    )


class IcdSuggester:
    """Placeholder ICD-10 'classifier': dictionary lookup over normalized
    entities. Swap for a trained classification head without changing callers.
    """

    CONDITION_CODES: dict[str, tuple[str, str]] = {
        "hypertension": ("I10", "Essential (primary) hypertension"),
        "high blood pressure": ("I10", "Essential (primary) hypertension"),
        "type 2 diabetes": ("E11.9", "Type 2 diabetes mellitus without complications"),
        "type 2 diabetes mellitus": ("E11.9", "Type 2 diabetes mellitus without complications"),
        "diabetes mellitus": ("E11.9", "Type 2 diabetes mellitus without complications"),
        "diabetes": ("E11.9", "Type 2 diabetes mellitus without complications"),
        "asthma": ("J45.909", "Unspecified asthma, uncomplicated"),
        "copd": ("J44.9", "COPD, unspecified"),
        "chronic obstructive pulmonary disease": ("J44.9", "COPD, unspecified"),
        "atrial fibrillation": ("I48.91", "Unspecified atrial fibrillation"),
        "hyperlipidemia": ("E78.5", "Hyperlipidemia, unspecified"),
        "gerd": ("K21.9", "GERD without esophagitis"),
        "migraine": ("G43.909", "Migraine, unspecified, not intractable"),
        "anemia": ("D64.9", "Anemia, unspecified"),
        "pneumonia": ("J18.9", "Pneumonia, unspecified organism"),
        "urinary tract infection": ("N39.0", "Urinary tract infection, site not specified"),
        "hypothyroidism": ("E03.9", "Hypothyroidism, unspecified"),
        "depression": ("F32.9", "Major depressive disorder, single episode, unspecified"),
        "anxiety": ("F41.9", "Anxiety disorder, unspecified"),
        "osteoarthritis": ("M19.90", "Unspecified osteoarthritis, unspecified site"),
    }

    SYMPTOM_CODES: dict[str, tuple[str, str]] = {
        "chest pain": ("R07.9", "Chest pain, unspecified"),
        "shortness of breath": ("R06.02", "Shortness of breath"),
        "dyspnea": ("R06.02", "Shortness of breath"),
        "cough": ("R05.9", "Cough, unspecified"),
        "fever": ("R50.9", "Fever, unspecified"),
        "headache": ("R51.9", "Headache, unspecified"),
        "fatigue": ("R53.83", "Other fatigue"),
        "abdominal pain": ("R10.9", "Unspecified abdominal pain"),
        "dysuria": ("R30.0", "Dysuria"),
        "nausea": ("R11.0", "Nausea"),
        "dizziness": ("R42", "Dizziness and giddiness"),
    }

    def suggest(self, entities: list[dict]) -> list[dict]:
        suggestions: dict[str, dict] = {}
        for entity in entities:
            key = (entity.get("normalized") or entity["text"]).lower()
            if entity["category"] == "condition":
                hit, base_conf = self.CONDITION_CODES.get(key), 0.5
            elif entity["category"] == "symptom":
                hit, base_conf = self.SYMPTOM_CODES.get(key), 0.35
            else:
                continue
            if hit and hit[0] not in suggestions:
                # Scale by NER confidence so weak entities yield weak codes.
                suggestions[hit[0]] = {
                    "code": hit[0],
                    "description": hit[1],
                    "confidence": round(base_conf * float(entity["confidence"]), 3),
                }
        return list(suggestions.values())


def mean_confidence(entities: list[dict]) -> float:
    if not entities:
        return 0.0
    return round(sum(float(e["confidence"]) for e in entities) / len(entities), 3)
