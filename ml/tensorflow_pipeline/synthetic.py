"""Synthetic specialty-labeled clinical notes with gold entity annotations.

Each sample is (text, spans, specialty): spans are (start, end, entity_category)
character offsets; specialty is the note-level class the Keras classifier
learns to predict. Entirely fabricated — no real patient data.
"""

import random

# Specialty -> entity-type -> terms. Terms may repeat across specialties
# (e.g. shortness of breath is cardio + respiratory); that ambiguity is what
# makes the note-level classifier non-trivial.
SPECIALTY_TERMS: dict[str, dict[str, list[str]]] = {
    "cardiovascular": {
        "condition": ["hypertension", "atrial fibrillation", "hyperlipidemia", "coronary artery disease"],
        "symptom": ["chest pain", "palpitations", "shortness of breath", "edema", "dizziness"],
        "medication": ["lisinopril", "atorvastatin", "amlodipine", "apixaban", "hydrochlorothiazide"],
        "procedure": ["ECG", "echocardiogram", "stress test", "troponin panel"],
    },
    "respiratory": {
        "condition": ["asthma", "COPD", "pneumonia"],
        "symptom": ["cough", "wheezing", "shortness of breath", "fever"],
        "medication": ["albuterol", "prednisone", "azithromycin"],
        "procedure": ["chest x-ray", "spirometry", "CBC"],
    },
    "endocrine": {
        "condition": ["type 2 diabetes", "hypothyroidism", "hyperlipidemia"],
        "symptom": ["fatigue", "weight gain", "increased thirst"],
        "medication": ["metformin", "levothyroxine", "insulin", "atorvastatin"],
        "procedure": ["A1c test", "thyroid panel", "lipid panel"],
    },
    "neurological": {
        "condition": ["migraine"],
        "symptom": ["headache", "nausea", "light sensitivity", "dizziness"],
        "medication": ["sumatriptan", "ibuprofen"],
        "procedure": ["MRI", "CT scan"],
    },
    "genitourinary": {
        "condition": ["urinary tract infection"],
        "symptom": ["dysuria", "urinary frequency", "back pain", "fever"],
        "medication": ["nitrofurantoin", "amoxicillin"],
        "procedure": ["urinalysis", "urine culture"],
    },
    "gastrointestinal": {
        "condition": ["GERD"],
        "symptom": ["abdominal pain", "nausea", "vomiting", "heartburn"],
        "medication": ["omeprazole"],
        "procedure": ["colonoscopy", "abdominal ultrasound"],
    },
    "psychiatric": {
        "condition": ["depression", "anxiety"],
        "symptom": ["insomnia", "fatigue", "poor concentration"],
        "medication": ["sertraline"],
        "procedure": ["PHQ-9 screening"],
    },
    "musculoskeletal": {
        "condition": ["osteoarthritis"],
        "symptom": ["joint pain", "back pain", "stiffness"],
        "medication": ["ibuprofen", "acetaminophen"],
        "procedure": ["x-ray", "physical therapy evaluation"],
    },
}

CATEGORIES = sorted(SPECIALTY_TERMS)

# {c}=condition {s}=symptom {m}=medication {p}=procedure
TEMPLATES = [
    "Patient presents with {s} and {s}. History of {c}. Currently taking {m}. {p} ordered today.",
    "Chief complaint: {s}. PMH significant for {c}. Continue {m} at current dose. Plan: {p}.",
    "{s} for the past three days. Known {c}. Started on {m}. Will obtain {p}.",
    "Follow-up for {c}. Reports {s} but denies {s}. Refilled {m}. {p} reviewed and unremarkable.",
    "New onset {s} with associated {s}. Assessment: likely {c}. Prescribed {m}. {p} scheduled.",
    "Routine visit. {c} well controlled on {m}. No {s} reported. Annual {p} due next month.",
]

SLOT_TO_TYPE = {"c": "condition", "s": "symptom", "m": "medication", "p": "procedure"}


def generate_note(
    rng: random.Random, specialty: str | None = None
) -> tuple[str, list[tuple[int, int, str]], str]:
    specialty = specialty or rng.choice(CATEGORIES)
    pools = SPECIALTY_TERMS[specialty]
    template = rng.choice(TEMPLATES)

    used: dict[str, list[str]] = {t: [] for t in SLOT_TO_TYPE.values()}
    parts: list[str] = []
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    i = 0
    while i < len(template):
        if template[i] == "{" and i + 2 < len(template) and template[i + 2] == "}":
            entity_type = SLOT_TO_TYPE[template[i + 1]]
            candidates = [t for t in pools[entity_type] if t not in used[entity_type]]
            value = rng.choice(candidates or pools[entity_type])
            used[entity_type].append(value)
            spans.append((cursor, cursor + len(value), entity_type))
            parts.append(value)
            cursor += len(value)
            i += 3
        else:
            parts.append(template[i])
            cursor += 1
            i += 1
    return "".join(parts), spans, specialty


def generate_dataset(
    n: int, seed: int = 7
) -> list[tuple[str, list[tuple[int, int, str]], str]]:
    rng = random.Random(seed)
    # Round-robin specialties for a balanced classification dataset.
    return [generate_note(rng, CATEGORIES[i % len(CATEGORIES)]) for i in range(n)]
