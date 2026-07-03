"""Inference entry point for the TensorFlow/Keras clinical NLP pipeline.

Flow (mirrors the API contract of pytorch_pipeline.inference.extract):
1. tokenize + classify the note's clinical specialty with the Keras model
2. extract entities with lightweight lexicon span-matching
3. model-assist: entity confidence is boosted when the entity belongs to the
   predicted specialty, scaled by the classifier's probability
4. ICD-10 suggestions (placeholder lookup) and per-entity confidences

Returns a dict shaped exactly like the backend's `ExtractionResult` schema.
Importable without tensorflow installed — heavy imports happen lazily; without
a trained checkpoint it degrades to unboosted lexicon extraction.
"""

import importlib.util
import re
from threading import Lock

from . import model as model_layer
from .synthetic import CATEGORIES

_classifier = None
_classifier_loaded = False
_load_lock = Lock()


def is_available() -> bool:
    """True if TensorFlow is installed (does not load the model)."""
    return importlib.util.find_spec("tensorflow") is not None


def model_name() -> str:
    if model_layer.resolve_model_path().exists():
        return "tensorflow:medextract-category (keras, trained)"
    return "tensorflow:lexicon-only (keras classifier untrained)"


def _get_classifier():
    global _classifier, _classifier_loaded
    with _load_lock:
        if not _classifier_loaded:
            _classifier = model_layer.load_classifier()
            _classifier_loaded = True
    return _classifier


def classify(text: str) -> tuple[str | None, float]:
    """Predicted specialty and its probability; (None, 0.0) when untrained."""
    classifier = _get_classifier()
    if classifier is None:
        return None, 0.0
    import tensorflow as tf

    probs = classifier.predict(tf.constant([[text]]), verbose=0)[0]
    idx = int(probs.argmax())
    return CATEGORIES[idx], float(probs[idx])


def find_entities(text: str, specialty: str | None, specialty_prob: float) -> list[dict]:
    """Case-insensitive longest-match-first lexicon search with word
    boundaries; overlapping shorter matches are dropped."""
    lower = text.lower()
    claimed: list[tuple[int, int]] = []
    entities: list[dict] = []

    for term in sorted(model_layer.LEXICON, key=len, reverse=True):
        entity_type, specialties = model_layer.LEXICON[term]
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            span = (m.start(), m.end())
            if any(s < span[1] and span[0] < e for s, e in claimed):
                continue
            claimed.append(span)
            confidence = model_layer.BASE_CONFIDENCE
            if specialty is not None and specialty in specialties:
                confidence += model_layer.MAX_BOOST * specialty_prob
            entities.append(
                {
                    "category": entity_type,
                    "text": text[span[0] : span[1]],
                    "normalized": term,
                    "span_start": span[0],
                    "span_end": span[1],
                    "confidence": round(min(confidence, 0.99), 3),
                }
            )

    # One entity per (category, normalized); keep highest confidence.
    best: dict[tuple[str, str], dict] = {}
    for e in entities:
        key = (e["category"], e["normalized"])
        if key not in best or e["confidence"] > best[key]["confidence"]:
            best[key] = e
    return sorted(best.values(), key=lambda e: e["span_start"])


def summarize(groups: dict[str, list[dict]]) -> str:
    def names(items: list[dict]) -> str:
        vals = [i["normalized"] or i["text"] for i in items]
        return vals[0] if len(vals) == 1 else ", ".join(vals[:-1]) + " and " + vals[-1]

    parts: list[str] = []
    if groups["symptoms"]:
        parts.append(f"You came in with {names(groups['symptoms'])}.")
    if groups["conditions"]:
        parts.append(f"Your record mentions {names(groups['conditions'])}.")
    if groups["medications"]:
        parts.append(f"Medications discussed include {names(groups['medications'])}.")
    if groups["procedures"]:
        parts.append(f"Tests or procedures mentioned: {names(groups['procedures'])}.")
    if not parts:
        return (
            "We could not automatically identify specific medical details in this note. "
            "Please review it with your care team."
        )
    parts.append(
        "This is an automatic summary of the note, not medical advice — "
        "please talk to your doctor about anything that is unclear."
    )
    return " ".join(parts)


def extract(text: str) -> dict:
    """Classify + extract + suggest. Returns an ExtractionResult-shaped dict."""
    specialty, specialty_prob = classify(text)
    entities = find_entities(text, specialty, specialty_prob)

    groups: dict[str, list[dict]] = {
        "conditions": [e for e in entities if e["category"] == "condition"],
        "symptoms": [e for e in entities if e["category"] == "symptom"],
        "medications": [e for e in entities if e["category"] == "medication"],
        "procedures": [e for e in entities if e["category"] == "procedure"],
    }

    return {
        **groups,
        "icd10_suggestions": model_layer.IcdSuggester().suggest(entities),
        "patient_summary": summarize(groups),
        "model_name": model_name(),
    }
