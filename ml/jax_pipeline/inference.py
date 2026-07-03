"""Inference entry point for the JAX/Flax research pipeline.

Same flow and output shape as tensorflow_pipeline.inference.extract — the
Flax classifier predicts the note's specialty, the shared clinical lexicon
extracts entities, and confidences are boosted when the classifier agrees.
Entity finding, summarization, and ICD suggestion are imported from
tensorflow_pipeline (pure Python, no TF required) so the two pipelines differ
*only* in the model — that's the research comparison.
"""

import importlib.util
from threading import Lock

from tensorflow_pipeline.inference import find_entities, summarize
from tensorflow_pipeline.model import IcdSuggester
from tensorflow_pipeline.synthetic import CATEGORIES

from . import model as model_layer

_bundle = None  # (model, params, vocab)
_bundle_loaded = False
_load_lock = Lock()


def is_available() -> bool:
    """True if JAX + Flax are installed (does not load the model)."""
    return all(importlib.util.find_spec(m) is not None for m in ("jax", "flax", "optax"))


def model_name() -> str:
    if (model_layer.resolve_model_dir() / "config.json").exists():
        return "jax:medextract-category (flax, trained)"
    return "jax:lexicon-only (flax classifier untrained)"


def _get_bundle():
    global _bundle, _bundle_loaded
    with _load_lock:
        if not _bundle_loaded:
            _bundle = model_layer.load_checkpoint()
            _bundle_loaded = True
    return _bundle


def classify(text: str) -> tuple[str | None, float]:
    """Predicted specialty and its probability; (None, 0.0) when untrained."""
    bundle = _get_bundle()
    if bundle is None:
        return None, 0.0
    import jax
    import jax.numpy as jnp

    model, params, vocab = bundle
    ids = jnp.asarray([model_layer.tokenize(text, vocab)], dtype=jnp.int32)
    probs = jax.nn.softmax(model.apply({"params": params}, ids))[0]
    idx = int(probs.argmax())
    return CATEGORIES[idx], float(probs[idx])


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
        "icd10_suggestions": IcdSuggester().suggest(entities),
        "patient_summary": summarize(groups),
        "model_name": model_name(),
    }
