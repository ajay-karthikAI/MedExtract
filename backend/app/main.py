from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analyze, extract, notes

app = FastAPI(
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


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
