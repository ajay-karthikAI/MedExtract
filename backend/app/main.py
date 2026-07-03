import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 — register tables on Base before create_all
from app.config import settings
from app.database import Base, engine
from app.routers import analyze, benchmarks, extract, notes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Create any missing tables (e.g. benchmark_runs on volumes that predate it).
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Could not ensure DB tables at startup: %s", exc)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="MedExtract API",
    version="0.1.0",
    description=(
        "Extracts conditions, symptoms, medications, procedures, ICD-10 suggestions, "
        "and a patient summary from clinical notes. Development scaffold — not for "
        "clinical use. Synthetic data only."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes.router)
app.include_router(extract.router)
app.include_router(analyze.router)
app.include_router(benchmarks.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
