# MedExtract

A clinical notes NLP application that extracts structured medical information from free-text doctor notes.

> ⚠️ **Disclaimer:** MedExtract is a development/research scaffold. It is **not** a medical device, does not provide medical advice, and must not be used for clinical decision-making. ICD-10 suggestions are heuristic hints for human review only. This repository contains **synthetic sample notes only — never commit real patient data (PHI)**.

## What it does

Given a free-text clinical note, MedExtract extracts:

1. **Medical conditions** (e.g., hypertension, type 2 diabetes)
2. **Symptoms** (e.g., chest pain, shortness of breath)
3. **Medications** (e.g., metformin, lisinopril)
4. **Procedures** (e.g., ECG, chest X-ray)
5. **Suggested ICD-10 codes** (heuristic, for human review)
6. **A plain-English patient summary**

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Next.js    │ ──▶ │   FastAPI    │ ──▶ │  PostgreSQL  │
│  frontend   │     │   backend    │     │              │
│  :3100      │     │   :8010      │     │   :5433      │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  ml/ models  │
                    │ pytorch / tf │
                    │    / jax     │
                    └──────────────┘
```

## Repo layout

```
MedExtract/
├── backend/            # FastAPI app (API, extraction service, ORM models)
├── frontend/           # Next.js + TypeScript + Tailwind UI
├── db/init/            # PostgreSQL schema (applied on first container start)
├── ml/
│   ├── pytorch/        # PyTorch NER experiments
│   ├── tensorflow/     # TensorFlow experiments
│   └── jax/            # JAX experiments
├── data/sample_notes/  # Synthetic notes (NO real patient data)
└── docker-compose.yml
```

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3100
- API docs (Swagger): http://localhost:8010/docs
- PostgreSQL: localhost:5433 (`medextract` / see `.env`)

Host ports default to 5433/8010/3100 to avoid clashing with services commonly
already running on 5432/8000/3000. Override with `POSTGRES_PORT`,
`BACKEND_PORT`, and `FRONTEND_PORT` in `.env` (keep `NEXT_PUBLIC_API_URL` and
`CORS_ORIGINS` in sync).

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://medextract:medextract@localhost:5433/medextract
uvicorn app.main:app --reload --port 8010
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API overview

| Method | Path                  | Description                                  |
|--------|-----------------------|----------------------------------------------|
| GET    | `/health`             | Liveness check                               |
| POST   | `/analyze-note`       | Analyze a note (`{note, framework}`); persists request + results |
| POST   | `/analyze-file`       | Analyze an uploaded PDF/TXT note (multipart: `file`, `framework`) |
| GET    | `/models`             | Available extraction models per framework    |
| GET    | `/history`            | Past analyses, newest first                  |
| POST   | `/api/notes`          | Submit a note; runs extraction, persists both |
| GET    | `/api/notes`          | List submitted notes                         |
| GET    | `/api/notes/{id}`     | Get a note with its extraction               |
| POST   | `/api/extract`        | Stateless extraction (nothing persisted)     |

Example:

```bash
curl -X POST http://localhost:8010/analyze-note \
  -H 'Content-Type: application/json' \
  -d '{"note": "Patient reports chest pain and shortness of breath. History of hypertension. Continue lisinopril 10mg. ECG ordered.", "framework": "pytorch"}'
```

## Extraction pipeline

Extraction is dispatched per framework (`backend/app/services/pipelines.py`):

- **`framework="pytorch"`** → `ml/pytorch_pipeline/` — Hugging Face Transformers
  token-classification NER (a fine-tuned checkpoint if you've run
  `python -m pytorch_pipeline.train`, otherwise the pretrained
  `d4data/biomedical-ner-all`). Requires `pip install -r ml/pytorch_pipeline/requirements.txt`
  in the backend's environment; the slim Docker image excludes torch, so the
  containerized backend falls back to rule-based for pytorch too.
- **`tensorflow` / `jax`** (and any unavailable pipeline) → the
  **rule/dictionary-based placeholder** in `backend/app/services/extraction.py`,
  which needs zero ML dependencies.

`GET /models` reports which path each framework actually serves
(`available` vs `placeholder`).

## Sample data

`data/sample_notes/` contains fully synthetic notes written for this project. Do not add real clinical text.

## Testing

```bash
cd backend && pytest
```
