from fastapi import APIRouter

from app import schemas
from app.services import extraction as extraction_service

router = APIRouter(prefix="/api", tags=["extract"])


@router.post("/extract", response_model=schemas.ExtractionResult)
def extract(payload: schemas.ExtractRequest):
    """Stateless extraction — nothing is persisted."""
    return extraction_service.extract(payload.text)
