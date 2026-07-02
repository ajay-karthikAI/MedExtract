"""Inference entry point for the PyTorch clinical NLP pipeline.

`extract(text)` returns a dict shaped like the backend's `ExtractionResult`
schema, so the API can validate it directly. This module stays importable
without torch installed — heavy imports happen on first extraction.
"""

import importlib.util
import re
from threading import Lock

from . import model as model_layer

_pipe = None
_loaded_model_id: str | None = None
_load_lock = Lock()


def is_available() -> bool:
    """True if the ML dependencies are installed (does not load the model)."""
    return all(importlib.util.find_spec(m) is not None for m in ("torch", "transformers"))


def model_id() -> str:
    return model_layer.resolve_model_id()


def model_name() -> str:
    mid = _loaded_model_id or model_id()
    if mid == str(model_layer.CHECKPOINT_DIR):
        return "pytorch:medextract-ner (fine-tuned)"
    return f"pytorch:{mid}"


def _get_pipe():
    global _pipe, _loaded_model_id
    with _load_lock:
        if _pipe is None:
            _pipe, _loaded_model_id = model_layer.load_ner_pipeline()
    return _pipe


_JOINABLE_GAP = re.compile(r"^[\s\-/]{0,2}$")


def _to_entities(raw_predictions: list[dict], text: str) -> list[dict]:
    structures: list[tuple[int, int]] = []  # anatomy spans, kept for composition
    entities: list[dict] = []
    for pred in sorted(raw_predictions, key=lambda p: int(p["start"])):
        label = pred["entity_group"].lower().removeprefix("b-").removeprefix("i-")
        start, end = int(pred["start"]), int(pred["end"])
        score = float(pred["score"])
        if label in model_layer.STRUCTURE_LABELS:
            structures.append((start, end))
            continue
        category = model_layer.LABEL_TO_CATEGORY.get(label)
        surface = text[start:end]
        if category is None or score < model_layer.MIN_SCORE or not surface.strip(" \t\n,.;:"):
            continue
        entities.append(
            {
                "category": category,
                "span_start": start,
                "span_end": end,
                "confidence": score,
            }
        )

    entities = _merge_adjacent(entities, text)

    # Compose "chest" (structure) + "pain" (symptom) into "chest pain".
    for e in entities:
        if e["category"] != "symptom":
            continue
        for s_start, s_end in structures:
            if s_end <= e["span_start"] and _JOINABLE_GAP.match(text[s_end : e["span_start"]]):
                e["span_start"] = s_start

    for e in entities:
        surface = text[e["span_start"] : e["span_end"]]
        e["text"] = surface
        e["normalized"] = surface.lower().strip()
        e["confidence"] = round(e["confidence"], 3)
    return entities


def _merge_adjacent(entities: list[dict], text: str) -> list[dict]:
    """Merge same-category spans separated only by whitespace or a hyphen,
    e.g. word-level fragments of "x-ray" or "type 2 diabetes"."""
    merged: list[dict] = []
    for e in entities:
        prev = merged[-1] if merged else None
        if (
            prev
            and prev["category"] == e["category"]
            and _JOINABLE_GAP.match(text[prev["span_end"] : e["span_start"]])
        ):
            prev["span_end"] = e["span_end"]
            prev["confidence"] = (prev["confidence"] + e["confidence"]) / 2
        else:
            merged.append(e)
    return merged


def _dedupe(entities: list[dict]) -> list[dict]:
    """One entity per (category, normalized) pair — keep the highest-confidence."""
    best: dict[tuple[str, str], dict] = {}
    for e in entities:
        key = (e["category"], e["normalized"])
        if key not in best or e["confidence"] > best[key]["confidence"]:
            best[key] = e
    return sorted(best.values(), key=lambda e: e["span_start"])


def _summarize(groups: dict[str, list[dict]]) -> str:
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
    """Run NER + ICD suggestion + summary. Returns an ExtractionResult-shaped dict."""
    predictions = _get_pipe()(text)
    entities = _dedupe(_to_entities(predictions, text))

    groups: dict[str, list[dict]] = {
        "conditions": [e for e in entities if e["category"] == "condition"],
        "symptoms": [e for e in entities if e["category"] == "symptom"],
        "medications": [e for e in entities if e["category"] == "medication"],
        "procedures": [e for e in entities if e["category"] == "procedure"],
    }

    return {
        **groups,
        "icd10_suggestions": model_layer.IcdSuggester().suggest(entities),
        "patient_summary": _summarize(groups),
        "model_name": model_name(),
    }
