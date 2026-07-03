"""ICD-10 suggestion mapping from extracted entity evidence."""

from app.schemas import EntityGroups, EntityOut, Icd10Out
from app.services import confidence

CONDITION_CODES: dict[str, tuple[str, str]] = {
    "st-elevation myocardial infarction": (
        "I21.3",
        "ST elevation (STEMI) myocardial infarction of unspecified site",
    ),
    "myocardial infarction": ("I21.9", "Acute myocardial infarction, unspecified"),
    "congestive heart failure": ("I50.9", "Heart failure, unspecified"),
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
    "coronary artery disease": ("I25.10", "ASHD of native coronary artery without angina"),
    "gerd": ("K21.9", "GERD without esophagitis"),
    "gastroesophageal reflux disease": ("K21.9", "GERD without esophagitis"),
    "migraine": ("G43.909", "Migraine, unspecified, not intractable"),
    "anemia": ("D64.9", "Anemia, unspecified"),
    "pneumonia": ("J18.9", "Pneumonia, unspecified organism"),
    "urinary tract infection": ("N39.0", "Urinary tract infection, site not specified"),
    "hypothyroidism": ("E03.9", "Hypothyroidism, unspecified"),
    "depression": ("F32.9", "Major depressive disorder, single episode, unspecified"),
    "major depressive disorder": ("F32.9", "Major depressive disorder, single episode, unspecified"),
    "anxiety": ("F41.9", "Anxiety disorder, unspecified"),
    "anxiety disorder": ("F41.9", "Anxiety disorder, unspecified"),
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
    "nausea and vomiting": ("R11.2", "Nausea with vomiting, unspecified"),
    "nausea": ("R11.0", "Nausea"),
    "dizziness": ("R42", "Dizziness and giddiness"),
    "back pain": ("M54.9", "Dorsalgia, unspecified"),
    "joint pain": ("M25.50", "Pain in unspecified joint"),
    "arthralgia": ("M25.50", "Pain in unspecified joint"),
    "insomnia": ("G47.00", "Insomnia, unspecified"),
}


def map_icd10(groups: EntityGroups) -> list[Icd10Out]:
    suggestions: dict[str, Icd10Out] = {}
    for entity in groups.conditions:
        _add_code(suggestions, entity, CONDITION_CODES, source="condition")
    for entity in groups.symptoms:
        _add_code(suggestions, entity, SYMPTOM_CODES, source="symptom")
    return list(suggestions.values())


def _add_code(
    suggestions: dict[str, Icd10Out],
    entity: EntityOut,
    code_map: dict[str, tuple[str, str]],
    *,
    source: str,
) -> None:
    key = (entity.normalized or entity.text).strip().lower()
    hit = code_map.get(key)
    if hit is None:
        return

    code, description = hit
    score = confidence.icd10_confidence(entity, source=source)
    if score <= 0:
        return

    suggestion = Icd10Out(code=code, description=description, confidence=score)
    current = suggestions.get(code)
    if current is None or suggestion.confidence > current.confidence:
        suggestions[code] = suggestion
