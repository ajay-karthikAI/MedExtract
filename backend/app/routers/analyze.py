"""Endpoints for the analyze-note workflow: run extraction on a clinical note,
persist request + response, and expose the model registry and analysis history.
"""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.services import documents, pipelines

router = APIRouter(tags=["analyze"])

FRAMEWORKS: tuple[schemas.Framework, ...] = ("pytorch", "tensorflow", "jax")

NOTE_PREVIEW_CHARS = 160


def _group_entities(entities: list[schemas.EntityOut]) -> schemas.EntityGroups:
    groups = schemas.EntityGroups()
    for e in entities:
        getattr(groups, e.category + "s").append(e)
    return groups


def _overall_confidence(
    entities: list[schemas.EntityOut], icd_codes: list[schemas.Icd10Out]
) -> float:
    scores = [e.confidence for e in entities] + [c.confidence for c in icd_codes]
    return round(sum(scores) / len(scores), 3) if scores else 0.0


def _preview(body: str) -> str:
    return body if len(body) <= NOTE_PREVIEW_CHARS else body[: NOTE_PREVIEW_CHARS - 1] + "…"


def _analyze_and_persist(
    db: Session,
    text: str,
    framework: str,
    *,
    title: str | None = None,
    source: str = "api",
) -> schemas.AnalyzeResponse:
    result = pipelines.extract(text, framework)
    model_used = result.model_name
    entities = result.conditions + result.symptoms + result.medications + result.procedures

    note = models.Note(title=title, body=text, source=source)
    ext = models.Extraction(
        note=note,
        model_name=model_used,
        framework=framework,
        summary=result.patient_summary,
    )
    for entity in entities:
        ext.entities.append(models.Entity(**entity.model_dump()))
    for icd in result.icd10_suggestions:
        ext.icd10_suggestions.append(models.Icd10Suggestion(**icd.model_dump()))
    db.add_all([note, ext])
    db.commit()

    return schemas.AnalyzeResponse(
        entities=_group_entities(entities),
        icd_codes=result.icd10_suggestions,
        patient_summary=result.patient_summary,
        model_used=model_used,
        confidence=_overall_confidence(entities, result.icd10_suggestions),
    )


@router.post("/analyze-note", response_model=schemas.AnalyzeResponse)
def analyze_note(payload: schemas.AnalyzeRequest, db: Session = Depends(get_db)):
    """Extract entities from a note, persist note + results, return the analysis."""
    return _analyze_and_persist(db, payload.note, payload.framework)


@router.post("/analyze-file", response_model=schemas.AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    framework: Literal["pytorch", "tensorflow", "jax"] = Form("pytorch"),
    db: Session = Depends(get_db),
):
    """Extract entities from an uploaded PDF or TXT note; persists like /analyze-note."""
    data = await file.read()
    try:
        text = documents.extract_text(file.filename or "", data)
    except documents.DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _analyze_and_persist(db, text, framework, title=file.filename, source="upload")


@router.get("/models", response_model=list[schemas.ModelInfo])
def list_models():
    return [pipelines.model_info(fw) for fw in FRAMEWORKS]


@router.get("/history", response_model=list[schemas.HistoryItem])
def history(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    """Past analyses, newest first."""
    stmt = (
        select(models.Extraction)
        .options(
            selectinload(models.Extraction.note),
            selectinload(models.Extraction.entities),
            selectinload(models.Extraction.icd10_suggestions),
        )
        .order_by(models.Extraction.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    items: list[schemas.HistoryItem] = []
    for ext in db.scalars(stmt):
        entities = [schemas.EntityOut.model_validate(e) for e in ext.entities]
        icd_codes = [schemas.Icd10Out.model_validate(c) for c in ext.icd10_suggestions]
        items.append(
            schemas.HistoryItem(
                id=ext.id,
                note_id=ext.note_id,
                framework=ext.framework,
                note_title=ext.note.title,
                note_preview=_preview(ext.note.body),
                created_at=ext.created_at,
                entities=_group_entities(entities),
                icd_codes=icd_codes,
                patient_summary=ext.summary,
                model_used=ext.model_name,
                confidence=_overall_confidence(entities, icd_codes),
            )
        )
    return items
