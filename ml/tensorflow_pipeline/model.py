"""Model layer for the TensorFlow/Keras clinical NLP pipeline.

Pieces:
1. A small Keras text classifier (TextVectorization -> Embedding -> pooling ->
   Dense softmax) that predicts a note's clinical specialty. Tokenization is
   the TextVectorization layer inside the model, so the saved .keras artifact
   is self-contained.
2. The entity lexicon (term -> entity type + specialties), derived from
   synthetic.SPECIALTY_TERMS, used by inference's lightweight span matcher.
3. ICD-10 suggestion — dictionary-lookup placeholder, same contract as the
   PyTorch pipeline's.
"""

import os
from pathlib import Path

from .synthetic import CATEGORIES, SPECIALTY_TERMS

CHECKPOINT = Path(__file__).resolve().parent / "checkpoints" / "medextract-category.keras"


def resolve_model_path() -> Path:
    override = os.environ.get("MEDEXTRACT_TF_MODEL")
    return Path(override) if override else CHECKPOINT


def build_model(vocab_size: int = 6000, seq_len: int = 160):
    """Untrained classifier. Caller must `adapt` the TextVectorization layer."""
    import tensorflow as tf

    vectorize = tf.keras.layers.TextVectorization(
        max_tokens=vocab_size, output_sequence_length=seq_len, name="tokenizer"
    )
    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(1,), dtype=tf.string),
            vectorize,
            tf.keras.layers.Embedding(vocab_size, 64, mask_zero=True),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(len(CATEGORIES), activation="softmax"),
        ],
        name="medextract_category_classifier",
    )
    return model, vectorize


def load_classifier():
    """Trained classifier from checkpoint, or None if absent/unloadable."""
    import tensorflow as tf

    path = resolve_model_path()
    if not path.exists():
        return None
    return tf.keras.models.load_model(path)


# ---------------------------------------------------------------------------
# Entity lexicon: flat term -> (entity_type, {specialties it belongs to}).
# Terms appearing in several specialties keep all of them; inference boosts
# confidence when the classifier's predicted specialty is among them.
# ---------------------------------------------------------------------------
def _build_lexicon() -> dict[str, tuple[str, frozenset[str]]]:
    lexicon: dict[str, tuple[str, set[str]]] = {}
    for specialty, pools in SPECIALTY_TERMS.items():
        for entity_type, terms in pools.items():
            for term in terms:
                key = term.lower()
                if key in lexicon:
                    lexicon[key][1].add(specialty)
                else:
                    lexicon[key] = (entity_type, {specialty})
    return {t: (etype, frozenset(specs)) for t, (etype, specs) in lexicon.items()}


LEXICON = _build_lexicon()

BASE_CONFIDENCE = 0.55  # dictionary match with no model support
MAX_BOOST = 0.35  # added when the classifier agrees, scaled by its probability


class IcdSuggester:
    """Placeholder ICD-10 'classifier': dictionary lookup over normalized
    entities, scores scaled by entity confidence. Same contract as the
    PyTorch pipeline's suggester so API output stays identical.
    """

    CONDITION_CODES: dict[str, tuple[str, str]] = {
        "hypertension": ("I10", "Essential (primary) hypertension"),
        "type 2 diabetes": ("E11.9", "Type 2 diabetes mellitus without complications"),
        "type 2 diabetes mellitus": ("E11.9", "Type 2 diabetes mellitus without complications"),
        "asthma": ("J45.909", "Unspecified asthma, uncomplicated"),
        "copd": ("J44.9", "COPD, unspecified"),
        "atrial fibrillation": ("I48.91", "Unspecified atrial fibrillation"),
        "hyperlipidemia": ("E78.5", "Hyperlipidemia, unspecified"),
        "coronary artery disease": ("I25.10", "ASHD of native coronary artery without angina"),
        "gerd": ("K21.9", "GERD without esophagitis"),
        "migraine": ("G43.909", "Migraine, unspecified, not intractable"),
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
        "cough": ("R05.9", "Cough, unspecified"),
        "fever": ("R50.9", "Fever, unspecified"),
        "headache": ("R51.9", "Headache, unspecified"),
        "fatigue": ("R53.83", "Other fatigue"),
        "abdominal pain": ("R10.9", "Unspecified abdominal pain"),
        "dysuria": ("R30.0", "Dysuria"),
        "nausea": ("R11.0", "Nausea"),
        "dizziness": ("R42", "Dizziness and giddiness"),
        "back pain": ("M54.9", "Dorsalgia, unspecified"),
        "joint pain": ("M25.50", "Pain in unspecified joint"),
        "insomnia": ("G47.00", "Insomnia, unspecified"),
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
                suggestions[hit[0]] = {
                    "code": hit[0],
                    "description": hit[1],
                    "confidence": round(base_conf * float(entity["confidence"]), 3),
                }
        return list(suggestions.values())
