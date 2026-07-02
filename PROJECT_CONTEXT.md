# MedExtract — Project Context & Current Issues

_Last updated: 2026-07-02_

## Project context

- **What it is:** A clinical-notes NLP demo app. Free-text (or PDF) doctor notes go in;
  structured entities (conditions, symptoms, medications, procedures), heuristic ICD-10
  suggestions, a patient-friendly summary, and a confidence score come out. Development/research
  scaffold only — **not** a medical device; synthetic data only.
- **Stack:** Next.js 14 + TypeScript + Tailwind (frontend) · FastAPI + SQLAlchemy 2 (backend) ·
  PostgreSQL 16 (persistence) · PyTorch + Hugging Face Transformers (ML pipeline).
- **Repo layout:** `frontend/` (dashboard + history UI), `backend/` (API, dispatch, ORM),
  `ml/pytorch_pipeline/` (working NER pipeline: model/inference/train/evaluate/synthetic),
  `ml/{pytorch,tensorflow,jax}/` (older training skeletons), `db/init/` (schema applied on first
  container start), `data/sample_notes/` (synthetic notes).
- **API surface:** `POST /analyze-note` (`{note, framework}`), `POST /analyze-file`
  (multipart PDF/TXT), `GET /models`, `GET /history`, `GET /health`, plus legacy
  `POST /api/extract` and `/api/notes` routes.
- **Framework dispatch** (`backend/app/services/pipelines.py`): `pytorch` → transformer NER from
  `ml/pytorch_pipeline/` (fine-tuned checkpoint preferred, else pretrained
  `d4data/biomedical-ner-all`); `tensorflow`/`jax` (or any load failure) → rule-based dictionary
  extractor. `GET /models` reports which path actually serves (`available` vs `placeholder`).
- **Persistence:** every analysis writes `notes`, `extractions` (incl. `framework`), `entities`,
  and `icd10_suggestions` rows; `/history` reconstructs full results from the DB.
- **Fine-tuned model:** DistilBERT token classifier trained on 300 synthetic templated notes
  (3 epochs); span-level F1 = 1.0 on held-out synthetic data and generalizes well to the sample
  notes. Checkpoint lives at `ml/pytorch_pipeline/checkpoints/medextract-ner/` (gitignored).
- **Current dev runtime (as of this writing):**
  - PostgreSQL: Docker (`medextract-db-1`), host port **5433**
  - Backend: **local** uvicorn from `backend/.venv` (Python 3.12) on port **8010** — run locally
    because the slim Docker image has no torch; the `medextract-backend-1` container is stopped
  - Frontend: local `next dev` on port **3100**
  - Host ports are overridable via `POSTGRES_PORT` / `BACKEND_PORT` / `FRONTEND_PORT` in `.env`;
    defaults avoid clashes with other services occupying 5432/8000/3000 on this machine
- **Tests:** 13 backend tests (`cd backend && .venv/bin/python -m pytest`) — extraction rules,
  DB-free API validation. Frontend: typecheck only (`npx tsc --noEmit`).

## Current issues

### ML / extraction quality

- [ ] **No negation handling** — "denies fever or cough" still extracts *fever* and *cough* as
  symptoms, in both the rule-based extractor and the fine-tuned transformer.
- [ ] **ICD-10 "classification" is a placeholder** — dictionary lookup scaled by NER confidence
  (`IcdSuggester` in `ml/pytorch_pipeline/model.py`), not a trained classification head.
- [ ] **Fine-tuned model has template-shaped competence** — trained only on synthetic templated
  notes; observed real-note quirks: span includes dose ("lisinopril 10mg"), *troponin* tagged as
  medication (it's a lab test), *HPI*/*cardiology* tagged as procedures, *exertion* as a symptom.
- [ ] **Entity normalization is just lowercasing** — no UMLS/SNOMED/RxNorm linking, so
  "high blood pressure" and "hypertension" are separate entities in transformer output.
- [ ] **Confidence scores are partly heuristic** — rule-based entities use a fixed 0.6; ICD codes
  use fixed 0.35/0.5 bases; the overall score is a plain mean of whatever is present.
- [ ] **TensorFlow and JAX pipelines don't exist** — both frameworks silently serve the rule-based
  extractor (status is honest in `/models`, but there's no real model behind either).
- [ ] **Pretrained fallback model is weak on clinical-note formatting** — `d4data/biomedical-ner-all`
  misses terse section lists like `PMH: hypertension, …` (trained on narrative case reports);
  only the fine-tuned checkpoint handles them.

### Backend / infrastructure

- [ ] **Dockerized backend can't serve the PyTorch pipeline** — the slim image excludes torch, so
  `docker compose up` serves rule-based for all frameworks; there's no "full" image variant with
  ML deps baked in.
- [ ] **Split runtime is easy to break** — backend currently runs as a local process, not in
  compose; starting the backend container while local uvicorn runs will conflict on port 8010,
  and a fresh `docker compose up` quietly downgrades pytorch to placeholder.
- [ ] **No DB migration tooling** — schema comes solely from `db/init/01_schema.sql` on first
  container start; any future column change to an existing volume requires manual ALTERs
  (no Alembic).
- [ ] **No OCR for scanned PDFs** — `/analyze-file` rejects PDFs without a text layer with a 422.
- [ ] **No auth, rate limiting, or request size middleware** — acceptable for a local demo, not
  for any shared deployment.
- [ ] **Legacy routes are dead surface** — `POST /api/extract` and `/api/notes` are no longer used
  by the UI (they predate `/analyze-note`) but remain served and semi-duplicated
  (`notes.py` has its own `_persist_extraction`).
- [ ] **Summary/disclaimer logic is duplicated** — the patient-summary template exists in both
  `backend/app/services/extraction.py` and `ml/pytorch_pipeline/inference.py`.
- [ ] **No DB-backed integration tests** — persistence paths (`/analyze-note`, `/analyze-file`,
  `/history`) are only verified manually; API tests cover validation-only paths.
- [ ] **HF Hub download needed on first pretrained-model load** — offline first run of the pytorch
  path fails to the rule-based fallback; unauthenticated Hub requests are rate-limited (no
  `HF_TOKEN` configured).
- [ ] **Checkpoint is not committed (by design)** — fresh clones must run
  `python -m pytorch_pipeline.train` or accept the weaker pretrained fallback.

### Frontend

- [ ] **No frontend tests** — only `tsc --noEmit`; no component or e2e coverage.
- [ ] **`npm install` reports audit vulnerabilities** — untriaged (`npm audit` in `frontend/`).
- [ ] **Sample notes are duplicated in code** — `NoteForm.tsx` embeds copies of
  `data/sample_notes/` text rather than loading them.
- [ ] **No pagination UI for history** — the page fetches the latest 50; older analyses are
  unreachable from the UI (API supports `limit`/`offset`).

### Dev environment (this machine)

- [ ] **Repo is not a git repository** — no version control initialized; nothing is committed.
- [ ] **System `python3` is 3.9** — too old for the codebase (needs `X | None` syntax);
  `backend/.venv` was rebuilt from `/opt/anaconda3/bin/python3.12`. Recreating the venv with
  plain `python3` will break.
- [ ] **Port squatters** — other local services hold 5432 (`suno_postgres`), 8000 ("Re: Call"),
  and 3000 (a node process); MedExtract's defaults (5433/8010/3100) route around them.
- [ ] **Old ml skeletons linger** — `ml/pytorch/` is superseded by `ml/pytorch_pipeline/` but
  still present alongside the tensorflow/jax skeletons.
