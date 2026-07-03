# MedExtract Architecture

MedExtract is organized as a full-stack clinical NLP demo with a typed frontend, a FastAPI service layer, PostgreSQL persistence, and swappable extraction pipelines.

## System Diagram

```mermaid
flowchart TB
    subgraph Client
        browser[Browser]
        frontend[Next.js App<br/>TypeScript + Tailwind]
        browser --> frontend
    end

    subgraph API
        fastapi[FastAPI Application]
        analyze[Analyze Router<br/>/analyze-note<br/>/analyze-file<br/>/models<br/>/history]
        benchmark[Benchmark Router<br/>/benchmarks/run<br/>/benchmarks]
        legacy[Legacy API Routers<br/>/api/extract<br/>/api/notes]
        fastapi --> analyze
        fastapi --> benchmark
        fastapi --> legacy
    end

    subgraph NLP
        dispatch[Pipeline Dispatcher<br/>backend/app/services/pipelines.py]
        pytorch[PyTorch<br/>HF token classification]
        tensorflow[TensorFlow<br/>Keras classifier + lexicon]
        jax[JAX<br/>Flax benchmark path]
        fallback[Rule-based fallback<br/>backend/app/services/extraction.py]
        dispatch --> pytorch
        dispatch --> tensorflow
        dispatch --> jax
        dispatch --> fallback
    end

    subgraph Persistence
        postgres[(PostgreSQL)]
        notes[notes]
        extractions[extractions]
        entities[entities]
        codes[icd10_suggestions]
        runs[benchmark_runs]
        postgres --> notes
        postgres --> extractions
        postgres --> entities
        postgres --> codes
        postgres --> runs
    end

    frontend --> fastapi
    analyze --> dispatch
    benchmark --> dispatch
    analyze --> postgres
    benchmark --> postgres
    legacy --> postgres
```

## Request Lifecycle

1. The user submits a fictional note through the Next.js frontend or directly through the API.
2. FastAPI validates the request with Pydantic schemas.
3. The analyze router calls the framework dispatcher with `pytorch`, `tensorflow`, or `jax`.
4. The dispatcher loads the requested pipeline when dependencies are available.
5. If the pipeline cannot load, MedExtract falls back to the rule-based extractor and reports the model as `placeholder`.
6. Results are normalized into the shared response schema:
   - conditions
   - symptoms
   - medications
   - procedures
   - ICD-10 suggestions
   - patient-friendly summary
   - confidence
7. The backend persists the note, extraction, entities, and ICD-10 suggestions to PostgreSQL.
8. The frontend renders grouped results and allows users to revisit history.

## Persistence Model

```mermaid
erDiagram
    notes ||--o{ extractions : has
    extractions ||--o{ entities : contains
    extractions ||--o{ icd10_suggestions : suggests

    notes {
        uuid id
        text title
        text body
        text source
        timestamp created_at
    }

    extractions {
        uuid id
        uuid note_id
        text model_name
        text framework
        text summary
        timestamp created_at
    }

    entities {
        uuid id
        uuid extraction_id
        text category
        text text
        text normalized
        int span_start
        int span_end
        float confidence
    }

    icd10_suggestions {
        uuid id
        uuid extraction_id
        text code
        text description
        float confidence
    }
```

## Deployment Shape

Docker Compose starts:

| Service | Internal Port | Default Host Port | Purpose |
| --- | ---: | ---: | --- |
| `db` | `5432` | `5433` | PostgreSQL 16 |
| `backend` | `8000` | `8010` | FastAPI service |
| `frontend` | `3000` | `3100` | Next.js application |

The backend container is intentionally lightweight. Large ML dependencies can be installed for local experiments, while the fallback extractor keeps the demo runnable without GPU or model downloads.

## Safety Boundary

MedExtract is a synthetic-data research scaffold. It should be treated as a portfolio system that demonstrates architecture, API design, and NLP workflow patterns, not as deployable clinical software.
