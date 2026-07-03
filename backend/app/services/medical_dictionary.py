"""Rule-based medical dictionary for common clinical note terms."""

EntityLexicon = dict[str, str]
AbbreviationLexicon = dict[str, tuple[str, str]]

COMMON_CONDITIONS: EntityLexicon = {
    "st-elevation myocardial infarction": "ST-elevation myocardial infarction",
    "st elevation myocardial infarction": "ST-elevation myocardial infarction",
    "myocardial infarction": "myocardial infarction",
    "heart attack": "myocardial infarction",
    "congestive heart failure": "congestive heart failure",
    "heart failure": "congestive heart failure",
    "hypertension": "hypertension",
    "high blood pressure": "hypertension",
    "type 2 diabetes": "type 2 diabetes mellitus",
    "type ii diabetes": "type 2 diabetes mellitus",
    "type 2 diabetes mellitus": "type 2 diabetes mellitus",
    "diabetes mellitus": "diabetes mellitus",
    "diabetes": "diabetes mellitus",
    "asthma": "asthma",
    "copd": "chronic obstructive pulmonary disease",
    "chronic obstructive pulmonary disease": "chronic obstructive pulmonary disease",
    "atrial fibrillation": "atrial fibrillation",
    "afib": "atrial fibrillation",
    "coronary artery disease": "coronary artery disease",
    "hyperlipidemia": "hyperlipidemia",
    "high cholesterol": "hyperlipidemia",
    "gerd": "gastroesophageal reflux disease",
    "gastroesophageal reflux disease": "gastroesophageal reflux disease",
    "migraine": "migraine",
    "anemia": "anemia",
    "pneumonia": "pneumonia",
    "urinary tract infection": "urinary tract infection",
    "uti": "urinary tract infection",
    "hypothyroidism": "hypothyroidism",
    "depression": "major depressive disorder",
    "major depressive disorder": "major depressive disorder",
    "anxiety": "anxiety disorder",
    "anxiety disorder": "anxiety disorder",
    "osteoarthritis": "osteoarthritis",
}

COMMON_SYMPTOMS: EntityLexicon = {
    "chest pain": "chest pain",
    "shortness of breath": "shortness of breath",
    "dyspnea": "shortness of breath",
    "difficulty breathing": "shortness of breath",
    "fatigue": "fatigue",
    "fever": "fever",
    "cough": "cough",
    "headache": "headache",
    "nausea": "nausea",
    "vomiting": "vomiting",
    "dizziness": "dizziness",
    "lightheadedness": "dizziness",
    "palpitations": "palpitations",
    "abdominal pain": "abdominal pain",
    "stomach pain": "abdominal pain",
    "back pain": "back pain",
    "sore throat": "sore throat",
    "wheezing": "wheezing",
    "swelling": "edema",
    "edema": "edema",
    "rash": "rash",
    "joint pain": "arthralgia",
    "arthralgia": "arthralgia",
    "dysuria": "dysuria",
    "burning with urination": "dysuria",
}

COMMON_MEDICATIONS: EntityLexicon = {
    "lisinopril": "lisinopril",
    "prinivil": "lisinopril",
    "zestril": "lisinopril",
    "metformin": "metformin",
    "glucophage": "metformin",
    "atorvastatin": "atorvastatin",
    "lipitor": "atorvastatin",
    "amlodipine": "amlodipine",
    "norvasc": "amlodipine",
    "albuterol": "albuterol",
    "proair": "albuterol",
    "ventolin": "albuterol",
    "omeprazole": "omeprazole",
    "prilosec": "omeprazole",
    "levothyroxine": "levothyroxine",
    "synthroid": "levothyroxine",
    "sertraline": "sertraline",
    "zoloft": "sertraline",
    "ibuprofen": "ibuprofen",
    "advil": "ibuprofen",
    "motrin": "ibuprofen",
    "acetaminophen": "acetaminophen",
    "tylenol": "acetaminophen",
    "aspirin": "aspirin",
    "amoxicillin": "amoxicillin",
    "azithromycin": "azithromycin",
    "zithromax": "azithromycin",
    "nitrofurantoin": "nitrofurantoin",
    "macrobid": "nitrofurantoin",
    "warfarin": "warfarin",
    "coumadin": "warfarin",
    "apixaban": "apixaban",
    "eliquis": "apixaban",
    "insulin": "insulin",
    "prednisone": "prednisone",
    "sumatriptan": "sumatriptan",
    "imitrex": "sumatriptan",
    "hydrochlorothiazide": "hydrochlorothiazide",
    "hctz": "hydrochlorothiazide",
    "furosemide": "furosemide",
    "lasix": "furosemide",
}

COMMON_PROCEDURES: EntityLexicon = {
    "ecg": "electrocardiogram",
    "ekg": "electrocardiogram",
    "electrocardiogram": "electrocardiogram",
    "chest x-ray": "chest radiograph",
    "chest xray": "chest radiograph",
    "cxr": "chest radiograph",
    "x-ray": "radiograph",
    "xray": "radiograph",
    "ct": "computed tomography",
    "ct scan": "computed tomography",
    "computed tomography": "computed tomography",
    "mri": "magnetic resonance imaging",
    "magnetic resonance imaging": "magnetic resonance imaging",
    "echocardiogram": "echocardiogram",
    "echo": "echocardiogram",
    "colonoscopy": "colonoscopy",
    "urinalysis": "urinalysis",
    "ua": "urinalysis",
    "blood work": "laboratory panel",
    "labs": "laboratory panel",
    "cbc": "complete blood count",
    "complete blood count": "complete blood count",
    "spirometry": "spirometry",
    "stress test": "cardiac stress test",
    "cardiac stress test": "cardiac stress test",
    "biopsy": "biopsy",
}

ABBREVIATIONS: AbbreviationLexicon = {
    "stemi": ("condition", "ST-elevation myocardial infarction"),
    "chf": ("condition", "congestive heart failure"),
    "htn": ("condition", "hypertension"),
    "dm2": ("condition", "type 2 diabetes mellitus"),
    "t2dm": ("condition", "type 2 diabetes mellitus"),
    "sob": ("symptom", "shortness of breath"),
    "cp": ("symptom", "chest pain"),
    "n/v": ("symptom", "nausea and vomiting"),
    "hctz": ("medication", "hydrochlorothiazide"),
    "lasix": ("medication", "furosemide"),
    "ecg": ("procedure", "electrocardiogram"),
    "ekg": ("procedure", "electrocardiogram"),
    "cxr": ("procedure", "chest radiograph"),
    "ct": ("procedure", "computed tomography"),
    "mri": ("procedure", "magnetic resonance imaging"),
    "cbc": ("procedure", "complete blood count"),
    "ua": ("procedure", "urinalysis"),
}


def category_lexicons() -> tuple[tuple[str, EntityLexicon], ...]:
    """Return category dictionaries with abbreviation aliases merged in."""
    lexicons = {
        "condition": {**COMMON_CONDITIONS},
        "symptom": {**COMMON_SYMPTOMS},
        "medication": {**COMMON_MEDICATIONS},
        "procedure": {**COMMON_PROCEDURES},
    }
    for term, (category, normalized) in ABBREVIATIONS.items():
        lexicons[category][term] = normalized
    return (
        ("condition", lexicons["condition"]),
        ("symptom", lexicons["symptom"]),
        ("medication", lexicons["medication"]),
        ("procedure", lexicons["procedure"]),
    )


CATEGORY_LEXICONS = category_lexicons()


def normalize(category: str, *, surface: str, normalized: str | None = None) -> str:
    """Normalize a model or rule entity using category dictionaries."""
    candidates = [candidate for candidate in (normalized, surface) if candidate]
    lexicon = dict(CATEGORY_LEXICONS).get(category, {})
    for candidate in candidates:
        hit = lexicon.get(candidate.strip().lower())
        if hit:
            return hit
    fallback = (normalized or surface).strip()
    return fallback.lower()
