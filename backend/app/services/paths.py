from pathlib import Path

from app.config import settings


def _find_existing(relative: str) -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / relative
        if candidate.exists():
            return candidate
    return None


def ml_dir() -> Path:
    if settings.ml_dir:
        return Path(settings.ml_dir)
    return _find_existing("ml") or Path(__file__).resolve().parents[3] / "ml"


def sample_notes_dir() -> Path:
    if settings.data_dir:
        return Path(settings.data_dir) / "sample_notes"
    return _find_existing("data/sample_notes") or Path(__file__).resolve().parents[3] / "data" / "sample_notes"


def icd10_mapping_path() -> Path:
    if settings.data_dir:
        return Path(settings.data_dir) / "icd10_mapping.json"
    return _find_existing("data/icd10_mapping.json") or Path(__file__).resolve().parents[3] / "data" / "icd10_mapping.json"


def knowledge_file_path(filename: str) -> Path:
    if settings.data_dir:
        return Path(settings.data_dir) / "knowledge" / filename
    return (
        _find_existing(f"data/knowledge/{filename}")
        or Path(__file__).resolve().parents[3] / "data" / "knowledge" / filename
    )
