"""Patient-facing summary generation from structured analysis evidence."""

from app.schemas import EntityGroups, EntityOut


def generate_patient_summary(groups: EntityGroups) -> str:
    parts: list[str] = []
    if groups.symptoms:
        parts.append(f"The note mentions symptoms including {_names(groups.symptoms)}.")
    if groups.conditions:
        parts.append(f"The note mentions health conditions including {_names(groups.conditions)}.")
    if groups.medications:
        parts.append(f"Medications discussed include {_names(groups.medications)}.")
    if groups.procedures:
        parts.append(f"Tests or procedures mentioned include {_names(groups.procedures)}.")
    if not parts:
        return (
            "We could not automatically identify specific medical details in this note. "
            "Please review it with your care team."
        )
    parts.append(
        "This is an automatic summary of the note, not medical advice - "
        "please talk to your doctor about anything that is unclear."
    )
    return " ".join(parts)


def _names(items: list[EntityOut]) -> str:
    values = [item.normalized or item.text for item in items]
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + " and " + values[-1]
