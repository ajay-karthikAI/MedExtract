import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EntityCategory = str  # 'condition' | 'symptom' | 'medication' | 'procedure'
Framework = Literal["pytorch", "tensorflow", "jax"]


class NoteCreate(BaseModel):
    title: str | None = None
    text: str = Field(min_length=1, max_length=50_000)
    source: str = "manual"


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: EntityCategory
    text: str
    normalized: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    confidence: float = 0.0


class Icd10Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str
    confidence: float = 0.0


class ExtractionResult(BaseModel):
    """Shape returned by the extraction service and the stateless /api/extract endpoint."""

    conditions: list[EntityOut] = []
    symptoms: list[EntityOut] = []
    medications: list[EntityOut] = []
    procedures: list[EntityOut] = []
    icd10_suggestions: list[Icd10Out] = []
    patient_summary: str = ""
    model_name: str = "rule-based-v0"
    disclaimer: str = (
        "Automated extraction for informational purposes only. "
        "Not medical advice. ICD-10 suggestions require human review."
    )


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_name: str
    summary: str
    created_at: datetime
    entities: list[EntityOut] = []
    icd10_suggestions: list[Icd10Out] = []


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    body: str
    source: str
    created_at: datetime


class NoteWithExtraction(NoteOut):
    extractions: list[ExtractionOut] = []


class AnalyzeRequest(BaseModel):
    note: str = Field(min_length=1, max_length=50_000)
    framework: Framework = "pytorch"


class EntityGroups(BaseModel):
    conditions: list[EntityOut] = []
    symptoms: list[EntityOut] = []
    medications: list[EntityOut] = []
    procedures: list[EntityOut] = []


class AnalyzeResponse(BaseModel):
    entities: EntityGroups
    icd_codes: list[Icd10Out] = []
    patient_summary: str = ""
    model_used: str
    confidence: float = 0.0
    disclaimer: str = (
        "Automated extraction for informational purposes only. "
        "Not medical advice. ICD-10 suggestions require human review."
    )


class HistoryItem(AnalyzeResponse):
    id: uuid.UUID
    note_id: uuid.UUID
    framework: Framework | None = None
    note_title: str | None = None  # e.g. uploaded filename
    note_preview: str
    created_at: datetime


class ModelInfo(BaseModel):
    framework: Framework
    model_name: str
    status: Literal["available", "placeholder"]
    description: str


class BenchmarkFrameworkResult(BaseModel):
    framework: Framework
    model_name: str
    status: Literal["available", "placeholder"]
    mean_ms: float
    p50_ms: float
    p95_ms: float
    mean_confidence: float
    mean_entities: float
    mean_icd_codes: float
    rss_mb: float | None = None  # process RSS after this framework's runs (approximate)
    rss_delta_mb: float | None = None  # RSS growth during this framework's runs (approximate)


class BenchmarkRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notes_count: int
    iterations: int
    results: list[BenchmarkFrameworkResult]
    created_at: datetime
