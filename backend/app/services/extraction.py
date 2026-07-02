"""Rule/dictionary-based placeholder extractor.

Lets the app run end-to-end with zero ML dependencies. Replace with a trained
model from ml/ by implementing `extract(text) -> ExtractionResult` with the
same signature. Lexicons are intentionally small — this is a skeleton, not a
clinical NLP system.
"""

import re

from app.schemas import EntityOut, ExtractionResult, Icd10Out

# term -> (canonical name, ICD-10 code or None, ICD-10 description)
CONDITIONS: dict[str, tuple[str, str | None, str]] = {
    "hypertension": ("hypertension", "I10", "Essential (primary) hypertension"),
    "high blood pressure": ("hypertension", "I10", "Essential (primary) hypertension"),
    "type 2 diabetes": ("type 2 diabetes mellitus", "E11.9", "Type 2 diabetes mellitus without complications"),
    "diabetes mellitus": ("diabetes mellitus", "E11.9", "Type 2 diabetes mellitus without complications"),
    "asthma": ("asthma", "J45.909", "Unspecified asthma, uncomplicated"),
    "copd": ("chronic obstructive pulmonary disease", "J44.9", "COPD, unspecified"),
    "atrial fibrillation": ("atrial fibrillation", "I48.91", "Unspecified atrial fibrillation"),
    "hyperlipidemia": ("hyperlipidemia", "E78.5", "Hyperlipidemia, unspecified"),
    "gerd": ("gastroesophageal reflux disease", "K21.9", "GERD without esophagitis"),
    "migraine": ("migraine", "G43.909", "Migraine, unspecified, not intractable"),
    "anemia": ("anemia", "D64.9", "Anemia, unspecified"),
    "pneumonia": ("pneumonia", "J18.9", "Pneumonia, unspecified organism"),
    "urinary tract infection": ("urinary tract infection", "N39.0", "Urinary tract infection, site not specified"),
    "hypothyroidism": ("hypothyroidism", "E03.9", "Hypothyroidism, unspecified"),
    "depression": ("major depressive disorder", "F32.9", "Major depressive disorder, single episode, unspecified"),
    "anxiety": ("anxiety disorder", "F41.9", "Anxiety disorder, unspecified"),
    "osteoarthritis": ("osteoarthritis", "M19.90", "Unspecified osteoarthritis, unspecified site"),
}

SYMPTOMS: dict[str, str] = {
    "chest pain": "chest pain",
    "shortness of breath": "dyspnea",
    "dyspnea": "dyspnea",
    "fatigue": "fatigue",
    "fever": "fever",
    "cough": "cough",
    "headache": "headache",
    "nausea": "nausea",
    "vomiting": "vomiting",
    "dizziness": "dizziness",
    "palpitations": "palpitations",
    "abdominal pain": "abdominal pain",
    "back pain": "back pain",
    "sore throat": "sore throat",
    "wheezing": "wheezing",
    "swelling": "edema",
    "edema": "edema",
    "rash": "rash",
    "joint pain": "arthralgia",
    "dysuria": "dysuria",
    "burning with urination": "dysuria",
}

MEDICATIONS: dict[str, str] = {
    "lisinopril": "lisinopril",
    "metformin": "metformin",
    "atorvastatin": "atorvastatin",
    "amlodipine": "amlodipine",
    "albuterol": "albuterol",
    "omeprazole": "omeprazole",
    "levothyroxine": "levothyroxine",
    "sertraline": "sertraline",
    "ibuprofen": "ibuprofen",
    "acetaminophen": "acetaminophen",
    "aspirin": "aspirin",
    "amoxicillin": "amoxicillin",
    "azithromycin": "azithromycin",
    "nitrofurantoin": "nitrofurantoin",
    "warfarin": "warfarin",
    "apixaban": "apixaban",
    "insulin": "insulin",
    "prednisone": "prednisone",
    "sumatriptan": "sumatriptan",
    "hydrochlorothiazide": "hydrochlorothiazide",
}

PROCEDURES: dict[str, str] = {
    "ecg": "electrocardiogram",
    "ekg": "electrocardiogram",
    "electrocardiogram": "electrocardiogram",
    "chest x-ray": "chest radiograph",
    "x-ray": "radiograph",
    "ct scan": "computed tomography",
    "mri": "magnetic resonance imaging",
    "echocardiogram": "echocardiogram",
    "colonoscopy": "colonoscopy",
    "urinalysis": "urinalysis",
    "blood work": "laboratory panel",
    "cbc": "complete blood count",
    "spirometry": "spirometry",
    "stress test": "cardiac stress test",
    "biopsy": "biopsy",
}

# Symptom-level ICD-10 hints used when no condition match covers them.
SYMPTOM_ICD10: dict[str, tuple[str, str]] = {
    "chest pain": ("R07.9", "Chest pain, unspecified"),
    "dyspnea": ("R06.02", "Shortness of breath"),
    "cough": ("R05.9", "Cough, unspecified"),
    "fever": ("R50.9", "Fever, unspecified"),
    "headache": ("R51.9", "Headache, unspecified"),
    "fatigue": ("R53.83", "Other fatigue"),
    "abdominal pain": ("R10.9", "Unspecified abdominal pain"),
    "dysuria": ("R30.0", "Dysuria"),
}

MODEL_NAME = "rule-based-v0"


def _find_terms(text: str, lexicon: dict, category: str) -> list[EntityOut]:
    """Case-insensitive whole-word search; longest terms first so
    'type 2 diabetes' wins over 'diabetes'."""
    lower = text.lower()
    found: list[EntityOut] = []
    claimed: list[tuple[int, int]] = []

    for term in sorted(lexicon, key=len, reverse=True):
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            span = (m.start(), m.end())
            if any(s < span[1] and span[0] < e for s, e in claimed):
                continue  # overlaps a longer match
            claimed.append(span)
            value = lexicon[term]
            normalized = value[0] if isinstance(value, tuple) else value
            found.append(
                EntityOut(
                    category=category,
                    text=text[span[0]:span[1]],
                    normalized=normalized,
                    span_start=span[0],
                    span_end=span[1],
                    confidence=0.6,  # dictionary match, no context awareness
                )
            )
    found.sort(key=lambda e: e.span_start or 0)
    return found


def _dedupe(entities: list[EntityOut]) -> list[EntityOut]:
    seen: set[str] = set()
    out = []
    for e in entities:
        key = e.normalized or e.text.lower()
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def _icd10_for(conditions: list[EntityOut], symptoms: list[EntityOut]) -> list[Icd10Out]:
    suggestions: dict[str, Icd10Out] = {}
    for c in conditions:
        for term, (canonical, code, desc) in CONDITIONS.items():
            if canonical == c.normalized and code and code not in suggestions:
                suggestions[code] = Icd10Out(code=code, description=desc, confidence=0.5)
                break
    for s in symptoms:
        hint = SYMPTOM_ICD10.get(s.normalized or "")
        if hint and hint[0] not in suggestions:
            suggestions[hint[0]] = Icd10Out(code=hint[0], description=hint[1], confidence=0.35)
    return list(suggestions.values())


def _summarize(
    conditions: list[EntityOut],
    symptoms: list[EntityOut],
    medications: list[EntityOut],
    procedures: list[EntityOut],
) -> str:
    def names(items: list[EntityOut]) -> str:
        vals = [i.normalized or i.text for i in items]
        if len(vals) == 1:
            return vals[0]
        return ", ".join(vals[:-1]) + " and " + vals[-1]

    parts: list[str] = []
    if symptoms:
        parts.append(f"You came in with {names(symptoms)}.")
    if conditions:
        parts.append(f"Your record mentions {names(conditions)}.")
    if medications:
        parts.append(f"Medications discussed include {names(medications)}.")
    if procedures:
        parts.append(f"Tests or procedures mentioned: {names(procedures)}.")
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


def extract(text: str) -> ExtractionResult:
    conditions = _dedupe(_find_terms(text, CONDITIONS, "condition"))
    symptoms = _dedupe(_find_terms(text, SYMPTOMS, "symptom"))
    medications = _dedupe(_find_terms(text, MEDICATIONS, "medication"))
    procedures = _dedupe(_find_terms(text, PROCEDURES, "procedure"))

    return ExtractionResult(
        conditions=conditions,
        symptoms=symptoms,
        medications=medications,
        procedures=procedures,
        icd10_suggestions=_icd10_for(conditions, symptoms),
        patient_summary=_summarize(conditions, symptoms, medications, procedures),
        model_name=MODEL_NAME,
    )
