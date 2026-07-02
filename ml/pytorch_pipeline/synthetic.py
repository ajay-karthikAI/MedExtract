"""Synthetic clinical-note generator with gold entity annotations.

Produces (text, spans) pairs where spans are (start, end, category) character
offsets. Entirely fabricated vocabulary — no real patient data. Used by
train.py (converted to BIO tags) and evaluate.py (compared against predictions).
"""

import random

CONDITIONS = [
    "hypertension", "type 2 diabetes", "asthma", "hyperlipidemia", "migraine",
    "anemia", "pneumonia", "urinary tract infection", "hypothyroidism",
    "atrial fibrillation", "depression", "anxiety", "osteoarthritis", "GERD",
]
SYMPTOMS = [
    "chest pain", "shortness of breath", "fatigue", "fever", "cough",
    "headache", "nausea", "dizziness", "palpitations", "abdominal pain",
    "back pain", "wheezing", "dysuria", "joint pain",
]
MEDICATIONS = [
    "lisinopril", "metformin", "atorvastatin", "amlodipine", "albuterol",
    "omeprazole", "levothyroxine", "sertraline", "ibuprofen", "amoxicillin",
    "nitrofurantoin", "sumatriptan", "hydrochlorothiazide", "apixaban",
]
PROCEDURES = [
    "ECG", "chest x-ray", "CT scan", "MRI", "echocardiogram", "urinalysis",
    "CBC", "spirometry", "stress test", "colonoscopy",
]

# {c}=condition {s}=symptom {m}=medication {p}=procedure — repeated letters
# draw distinct values.
TEMPLATES = [
    "Patient presents with {s} and {s}. History of {c}. Currently taking {m}. {p} ordered today.",
    "Chief complaint: {s}. PMH significant for {c} and {c}. Continue {m} at current dose. Plan: {p} and {p}.",
    "{s} for the past three days. Known {c}. Started on {m} and {m}. Will obtain {p}.",
    "Follow-up for {c}. Reports {s} but denies {s}. Refilled {m}. {p} reviewed and unremarkable.",
    "New onset {s} with associated {s} and {s}. Assessment: likely {c}. Prescribed {m}. {p} scheduled.",
    "Routine visit. {c} well controlled on {m}. No {s} reported. Annual {p} due next month.",
    "Presents after {s} episode. History includes {c}, {c}, and {c}. Medications: {m}, {m}. Ordered {p}.",
]

POOLS = {"c": CONDITIONS, "s": SYMPTOMS, "m": MEDICATIONS, "p": PROCEDURES}
CATEGORY_NAMES = {"c": "condition", "s": "symptom", "m": "medication", "p": "procedure"}


def generate_note(rng: random.Random) -> tuple[str, list[tuple[int, int, str]]]:
    """One synthetic note with gold (start, end, category) spans."""
    template = rng.choice(TEMPLATES)
    used: dict[str, list[str]] = {k: [] for k in POOLS}
    text_parts: list[str] = []
    spans: list[tuple[int, int, str]] = []
    cursor = 0

    i = 0
    while i < len(template):
        if template[i] == "{" and i + 2 < len(template) and template[i + 2] == "}":
            slot = template[i + 1]
            candidates = [v for v in POOLS[slot] if v not in used[slot]]
            value = rng.choice(candidates or POOLS[slot])
            used[slot].append(value)
            spans.append((cursor, cursor + len(value), CATEGORY_NAMES[slot]))
            text_parts.append(value)
            cursor += len(value)
            i += 3
        else:
            text_parts.append(template[i])
            cursor += 1
            i += 1

    return "".join(text_parts), spans


def generate_dataset(n: int, seed: int = 13) -> list[tuple[str, list[tuple[int, int, str]]]]:
    rng = random.Random(seed)
    return [generate_note(rng) for _ in range(n)]
