import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.services import extraction as extraction_service

router = APIRouter(prefix="/api/notes", tags=["notes"])


def _persist_extraction(db: Session, note: models.Note, result: schemas.ExtractionResult) -> None:
    ext = models.Extraction(note=note, model_name=result.model_name, summary=result.patient_summary)
    for entity in (
        result.conditions + result.symptoms + result.medications + result.procedures
    ):
        ext.entities.append(models.Entity(**entity.model_dump()))
    for icd in result.icd10_suggestions:
        ext.icd10_suggestions.append(models.Icd10Suggestion(**icd.model_dump()))
    db.add(ext)


@router.post("", response_model=schemas.NoteWithExtraction, status_code=201)
def create_note(payload: schemas.NoteCreate, db: Session = Depends(get_db)):
    """Persist a note, run extraction on it, and persist the results."""
    note = models.Note(title=payload.title, body=payload.text, source=payload.source)
    db.add(note)
    result = extraction_service.extract(payload.text)
    _persist_extraction(db, note, result)
    db.commit()
    db.refresh(note)
    return note


@router.get("", response_model=list[schemas.NoteOut])
def list_notes(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    stmt = (
        select(models.Note)
        .order_by(models.Note.created_at.desc())
        .limit(min(limit, 200))
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.get("/{note_id}", response_model=schemas.NoteWithExtraction)
def get_note(note_id: uuid.UUID, db: Session = Depends(get_db)):
    stmt = (
        select(models.Note)
        .options(
            selectinload(models.Note.extractions).selectinload(models.Extraction.entities),
            selectinload(models.Note.extractions).selectinload(
                models.Extraction.icd10_suggestions
            ),
        )
        .where(models.Note.id == note_id)
    )
    note = db.scalars(stmt).first()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
