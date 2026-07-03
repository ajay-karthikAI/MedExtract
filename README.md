# MedExtract

**Multi-framework clinical NLP system for extracting medical entities, suggesting ICD-10 codes, and generating patient-friendly summaries from clinical notes.**

MedExtract is a portfolio-ready clinical NLP demo that turns free-text clinical notes into structured outputs. It supports a FastAPI backend, a Next.js dashboard, PostgreSQL persistence, benchmark views, and interchangeable PyTorch, TensorFlow, JAX, and rule-based extraction paths.

> **Healthcare AI safety disclaimer:** MedExtract is a development and research project. It is not a medical device, does not provide medical advice, and must not be used for diagnosis, treatment, billing, or clinical decision-making. All extracted entities, ICD-10 suggestions, confidence scores, and patient-facing summaries require review by qualified human professionals.
>
> **Synthetic data disclaimer:** This repository is designed for synthetic and fictional clinical notes only. Do not commit, upload, or process real patient information, protected health information (PHI), or personally identifiable information (PII).

## Highlights

- Extracts conditions, symptoms, medications, and procedures from clinical notes.
- Uses a hybrid local pipeline: rule dictionaries, optional model votes, entity merge/dedupe, local RAG normalization, ICD mapping, and calibrated confidence scoring.
- Suggests ICD-10 codes as human-review hints.
- Generates deterministic patient-friendly summaries from extracted note evidence.
- Supports text entry and PDF/TXT upload workflows.
- Persists analyses, entities, ICD-10 suggestions, and history in PostgreSQL.
- Compares PyTorch, TensorFlow, JAX, and fallback extraction behavior through a benchmark API and UI page.
- Includes synthetic sample notes and a larger synthetic CSV dataset for demo and testing.

## Demo Flow

1. Paste or upload a fictional clinical note.
2. Choose a framework: `pytorch`, `tensorflow`, or `jax`.
3. Review extracted entities grouped by category.
4. Inspect suggested ICD-10 codes and confidence estimates.
5. Read the patient-friendly summary.
6. Revisit prior analyses in history or compare framework latency in benchmarks.

## Architecture

```mermaid
flowchart LR
    user[User / Portfolio Reviewer] --> ui[Next.js Frontend<br/>TypeScript + Tailwind<br/>localhost:3100]
    ui --> api[FastAPI Backend<br/>Python + SQLAlchemy<br/>localhost:8010]
    api --> db[(PostgreSQL<br/>notes, extractions,<br/>entities, ICD-10, benchmarks)]
    api --> rules[Rule Dictionary<br/>conditions, symptoms,<br/>meds, procedures, abbreviations]
    api --> dispatch[Framework Dispatcher]
    dispatch --> pt[PyTorch Votes<br/>optional local pipeline]
    dispatch --> tf[TensorFlow Votes<br/>optional local pipeline]
    dispatch --> jax[JAX Votes<br/>optional local pipeline]
    rules --> merge[Hybrid Merge + Dedupe<br/>source: rule/model/both/ensemble]
    pt --> merge
    tf --> merge
    jax --> merge
    merge --> rag[Local RAG Knowledge Files<br/>ICD descriptions, med aliases,<br/>condition definitions, abbreviations]
    rag --> icd[ICD-10 Mapping<br/>exact + synonym match]
    rag --> summary[Deterministic Patient Summary]
    merge --> confidence[Evidence-Based Confidence<br/>match quality, mentions,<br/>agreement, uncertainty]
    api --> docs[Swagger / OpenAPI<br/>/docs]
```

More detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Hybrid Extraction Pipeline

`/analyze-note`, `/analyze-file`, and `/api/extract` use the same local-first pipeline:

1. Rule-based dictionaries extract exact condition, symptom, medication, procedure, and abbreviation matches.
2. Optional PyTorch, TensorFlow, and JAX pipelines contribute model entity votes when their dependencies/checkpoints are available.
3. Duplicate entities are merged by normalized category/name and labeled by source: `rule`, `model`, `both`, or `ensemble_agreement`.
4. Local RAG knowledge files in `data/knowledge/` retrieve exact snippets for ICD descriptions, medication aliases, condition definitions, and abbreviations.
5. Retrieved snippets improve normalized names and ICD-10 mapping without paid APIs or network calls.
6. Confidence scoring uses evidence strength: exact text match, abbreviation match, model probability, mention count, rule/model agreement, framework agreement, uncertainty language, and ICD match quality.
7. Patient summaries are deterministic, plain-language, and limited to facts extracted from the note plus explicit follow-up instructions found in the note.

The API also returns `framework_votes` so the frontend can show which optional framework pipelines supported each entity. When optional ML dependencies are not installed, MedExtract does not fake model agreement; it falls back to the local rule and knowledge pipeline.

## Repository Layout

```text
MedExtract/
├── backend/                 # FastAPI app, routers, schemas, persistence, extraction services
├── frontend/                # Next.js app, dashboard UI, history, benchmarks
├── db/init/                 # PostgreSQL initialization SQL
├── docs/                    # Portfolio documentation: architecture, API, models
├── data/                    # Synthetic notes, eval data, ICD map, local knowledge files
├── ml/
│   ├── pytorch_pipeline/    # Hugging Face token-classification path
│   ├── tensorflow_pipeline/ # Keras classifier-assisted path
│   ├── jax_pipeline/        # Flax benchmark/research path
│   └── skeletons/           # Older framework training skeletons
├── screenshots/             # Portfolio screenshots and capture notes
└── docker-compose.yml
```

## Setup

### Prerequisites

- Docker Desktop or compatible Docker runtime
- Python 3.12 for local backend development
- Node.js 20+ for local frontend development

### Run With Docker

```bash
cp .env.example .env
docker compose up
```

Use `docker compose up --build` after changing Dockerfiles or dependency manifests.

Default local URLs:

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3100 |
| API | http://localhost:8010 |
| Swagger docs | http://localhost:8010/docs |
| PostgreSQL | localhost:5433 |

The default host ports avoid common local conflicts with `5432`, `8000`, and `3000`. Override them in `.env` with `POSTGRES_PORT`, `BACKEND_PORT`, and `FRONTEND_PORT`. Keep `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` in sync with any port changes.

Compose also sets `ML_DIR=/code/ml` and `DATA_DIR=/code/data` so the backend container can see the mounted framework pipelines and synthetic sample notes. On startup, the backend creates missing tables and applies small idempotent schema repairs for older local PostgreSQL volumes.

### Run Locally

Start PostgreSQL with Docker:

```bash
docker compose up db
```

Run the backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://medextract:medextract@localhost:5433/medextract
uvicorn app.main:app --reload --port 8010
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Optional ML dependencies:

```bash
pip install -r ml/pytorch_pipeline/requirements.txt
pip install -r ml/tensorflow_pipeline/requirements.txt
pip install -r ml/jax_pipeline/requirements.txt
```

The slim Docker backend intentionally excludes large ML dependencies. If a requested framework cannot load, the API reports a `placeholder` model status and serves the rule-based fallback. Install optional ML dependencies only for local model experiments.

## API Overview

Interactive OpenAPI documentation is available at:

```text
http://localhost:8010/docs
```

Core endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness check |
| `POST` | `/analyze-note` | Analyze and persist a clinical note |
| `POST` | `/analyze-file` | Analyze and persist an uploaded PDF/TXT note |
| `GET` | `/models` | Show active model status per framework |
| `GET` | `/history` | List previous analyses |
| `POST` | `/benchmarks/run` | Run all framework pipelines over sample notes |
| `GET` | `/benchmarks` | List stored benchmark runs |
| `POST` | `/api/extract` | Stateless legacy extraction |
| `POST` | `/api/notes` | Legacy note creation + extraction |

Full endpoint documentation: [docs/API.md](docs/API.md)

Example request:

```bash
curl -X POST http://localhost:8010/analyze-note \
  -H "Content-Type: application/json" \
  -d '{
    "framework": "pytorch",
    "note": "Synthetic note: Adult patient reports chest pain and shortness of breath. History of hypertension. Continue lisinopril. ECG ordered."
  }'
```

## Model Comparison

| Framework | Role | Strengths | Current Limitations |
| --- | --- | --- | --- |
| PyTorch | Hugging Face token-classification NER path | Best fit for span-level entity extraction; can use fine-tuned checkpoints | Fresh clones need dependencies/checkpoints; pretrained fallback is weaker on terse clinical-note formatting |
| TensorFlow | Keras note-category classifier + lexicon extractor | Lightweight classifier-assisted confidence scoring | Entity extraction remains lexicon-bound |
| JAX | Flax research/benchmark twin | Useful for comparing multi-framework serving behavior | Research path, not intended for production deployment |
| Rule-based fallback | Zero-dependency placeholder | Always available; predictable for demos and tests | Dictionary coverage only; no learned clinical language understanding |

Full model notes: [docs/MODELS.md](docs/MODELS.md)

## Data

This project includes fictional data only:

- `data/sample_notes/` - short synthetic notes for manual testing and benchmarking.
- `data/synthetic_clinical_notes.csv` - generated synthetic clinical-note dataset with conditions, symptoms, medications, procedures, ICD-10 labels, and patient-friendly summaries.
- `data/private/` is gitignored for local experiments and must not contain real PHI in shared environments.

Do not use real clinical notes unless you have appropriate authorization, privacy controls, security review, data-use agreements, and de-identification procedures outside this demo repository.

## Screenshots

Use [screenshots/](screenshots/) for portfolio images such as:

- Home/analyze screen
- Entity extraction result view
- History page
- Benchmark comparison page
- Swagger API docs

The folder is tracked with capture notes so screenshots can be added without changing documentation structure.

## Testing

Backend tests:

```bash
cd backend
python -m pytest
```

Frontend typecheck:

```bash
cd frontend
npx tsc --noEmit
```

## Limitations

- ICD-10 suggestions are heuristic hints, not certified medical coding.
- Negation handling is incomplete; phrases like "denies fever" may still surface entities.
- Synthetic training and demo notes do not represent real-world clinical variation.
- Entity normalization is basic and does not link to UMLS, SNOMED CT, RxNorm, or LOINC.
- Confidence scores are approximate and should not be interpreted as calibrated probabilities.
- The Docker backend uses a slim dependency set and may fall back to rule-based extraction.
- There is no authentication, rate limiting, audit logging, or production security hardening.
- PDF support requires an embedded text layer; scanned documents are not OCR processed.
- Benchmark memory numbers are process-level estimates, not isolated model memory profiles.

## Portfolio Positioning

MedExtract demonstrates full-stack healthcare AI engineering across:

- Clinical NLP pipeline design
- Multi-framework model serving and fallback behavior
- API design with validation and persistence
- Database-backed analysis history
- Benchmark instrumentation
- Responsible AI documentation for healthcare-adjacent systems

It is intentionally scoped as a transparent, synthetic-data demo rather than a production clinical system.
