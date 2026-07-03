"""Patient-facing summary generation from structured analysis evidence."""

import re

from app.schemas import EntityGroups, EntityOut


DISCLAIMER = "This is a simplified summary of the note, not medical advice or a diagnosis."

PLAIN_LANGUAGE: dict[str, str] = {
    "st-elevation myocardial infarction": "serious heart attack",
    "myocardial infarction": "heart attack",
    "acute coronary syndrome": "a possible heart blood-flow problem",
    "congestive heart failure": "heart failure",
    "hypertension": "high blood pressure",
    "type 2 diabetes mellitus": "type 2 diabetes",
    "diabetes mellitus": "diabetes",
    "hyperlipidemia": "high cholesterol",
    "gastroesophageal reflux disease": "acid reflux",
    "chronic obstructive pulmonary disease": "chronic lung disease",
    "major depressive disorder": "depression",
    "urinary tract infection": "urinary tract infection",
    "dyspnea": "shortness of breath",
    "edema": "swelling",
    "arthralgia": "joint pain",
    "dysuria": "pain or burning with urination",
    "nausea and vomiting": "nausea and vomiting",
    "electrocardiogram": "heart tracing test",
    "chest radiograph": "chest X-ray",
    "radiograph": "X-ray",
    "computed tomography": "CT scan",
    "magnetic resonance imaging": "MRI scan",
    "echocardiogram": "heart ultrasound",
    "laboratory panel": "lab tests",
    "complete blood count": "blood count test",
    "urinalysis": "urine test",
    "spirometry": "breathing test",
    "cardiac stress test": "heart stress test",
}

FOLLOW_UP_LIMIT = 2
FOLLOW_UP_CUES = (
    "follow up with",
    "follow-up with",
    "follow up in",
    "follow-up in",
    "follow up after",
    "follow-up after",
    "follow-up appointment",
    "follow up appointment",
    "follow-up scheduled",
    "follow up scheduled",
    "return in",
    "return to",
    "return for",
    "recheck",
    "repeat",
    "referral",
    "referred",
    "schedule",
    "scheduled",
    "appointment",
    "rtc",
    "f/u",
)


def generate_patient_summary(groups: EntityGroups, note_text: str = "") -> str:
    parts = [_main_problem_sentence(groups)]

    if groups.symptoms:
        parts.append(f"Symptoms mentioned: {_names(groups.symptoms)}.")
    if groups.medications:
        parts.append(f"Medicines documented in the note: {_names(groups.medications)}.")
    else:
        parts.append("Medicines documented in the note: none identified.")

    care_steps = _care_steps(groups)
    if care_steps:
        parts.append(f"Tests or treatments documented in the note: {_list(care_steps)}.")
    else:
        parts.append("Tests or treatments documented in the note: none identified.")

    parts.append(_follow_up_sentence(note_text))
    parts.append(DISCLAIMER)
    return " ".join(parts)


def _main_problem_sentence(groups: EntityGroups) -> str:
    if groups.conditions:
        return f"Main problems mentioned in the note: {_names(groups.conditions)}."
    if groups.symptoms:
        return f"Main problems mentioned in the note: {_names(groups.symptoms)}."
    if groups.medications or groups.procedures:
        return (
            "Main problems mentioned in the note: none identified from the extracted details."
        )
    return (
        "Main problems mentioned in the note: none identified from the extracted details."
    )


def _names(items: list[EntityOut]) -> str:
    return _list([_plain_name(item) for item in items])


def _care_steps(groups: EntityGroups) -> list[str]:
    return [_plain_name(item) for item in groups.procedures]


def _plain_name(item: EntityOut) -> str:
    value = (item.normalized or item.text).strip()
    return PLAIN_LANGUAGE.get(value.lower(), value)


def _list(values: list[str]) -> str:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            deduped.append(cleaned)
    values = deduped
    if len(values) == 1:
        return values[0]
    if not values:
        return ""
    return ", ".join(values[:-1]) + " and " + values[-1]


def _follow_up_sentence(note_text: str) -> str:
    instructions = _follow_up_instructions(note_text)
    if not instructions:
        return "Follow-up instructions found in the note: none identified."
    return f"Follow-up instructions found in the note: {_list(instructions)}."


def _follow_up_instructions(note_text: str) -> list[str]:
    instructions: list[str] = []
    for sentence in _sentences(note_text):
        if not _is_follow_up_instruction(sentence):
            continue
        instruction = _clean_instruction(sentence)
        if instruction:
            instructions.append(instruction)
        if len(instructions) >= FOLLOW_UP_LIMIT:
            break
    return instructions


def _sentences(note_text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", note_text)
        if sentence.strip()
    ]


def _is_follow_up_instruction(sentence: str) -> bool:
    lowered = sentence.lower()
    if "follow-up of" in lowered or "follow up of" in lowered:
        return False
    return any(cue in lowered for cue in FOLLOW_UP_CUES)


def _clean_instruction(sentence: str) -> str:
    cleaned = re.sub(r"\s+", " ", sentence).strip(" .;")
    cleaned = re.sub(r"^(plan|assessment|instructions?|discharge instructions?)\s*:\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\bRTC\b", "return to clinic", cleaned, flags=re.I)
    cleaned = re.sub(r"\bF/U\b", "follow up", cleaned, flags=re.I)
    cleaned = re.sub(r"\bPRN\b", "as needed", cleaned, flags=re.I)
    return cleaned[:220].rstrip(" ,;")
