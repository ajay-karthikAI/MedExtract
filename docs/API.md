# MedExtract API Documentation

Base URL for local development:

```text
http://localhost:8010
```

Interactive Swagger/OpenAPI docs:

```text
http://localhost:8010/docs
```

All endpoints are for synthetic or fictional notes only. Do not send PHI or real patient data to this demo service.

## Common Types

### Framework

```text
pytorch | tensorflow | jax
```

### Entity

```json
{
  "category": "condition",
  "text": "hypertension",
  "normalized": "hypertension",
  "span_start": 42,
  "span_end": 54,
  "confidence": 0.82
}
```

Entity categories are returned as grouped arrays:

- `conditions`
- `symptoms`
- `medications`
- `procedures`

### ICD-10 Suggestion

```json
{
  "code": "I10",
  "description": "Essential hypertension",
  "confidence": 0.5
}
```

ICD-10 suggestions are not billing-ready codes. They are heuristic hints for human review.

## Endpoints

### `GET /health`

Checks whether the API process is running.

Response:

```json
{
  "status": "ok"
}
```

### `POST /analyze-note`

Analyzes a note, persists the note and extraction, and returns structured results.

Request:

```json
{
  "framework": "pytorch",
  "note": "Synthetic note: Adult patient reports chest pain and shortness of breath. History of hypertension. Continue lisinopril. ECG ordered."
}
```

Response:

```json
{
  "entities": {
    "conditions": [],
    "symptoms": [],
    "medications": [],
    "procedures": []
  },
  "icd_codes": [],
  "patient_summary": "Plain-language summary text.",
  "model_used": "pytorch-rule-based-v0",
  "confidence": 0.6,
  "disclaimer": "Automated extraction for informational purposes only. Not medical advice. ICD-10 suggestions require human review."
}
```

Example:

```bash
curl -X POST http://localhost:8010/analyze-note \
  -H "Content-Type: application/json" \
  -d '{"framework":"pytorch","note":"Synthetic note: Adult patient reports chest pain and shortness of breath. History of hypertension. Continue lisinopril. ECG ordered."}'
```

### `POST /analyze-file`

Analyzes an uploaded `.txt` or text-layer `.pdf` file and persists the result.

Multipart fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | file | yes | PDF or TXT clinical note |
| `framework` | string | no | `pytorch`, `tensorflow`, or `jax`; defaults to `pytorch` |

Example:

```bash
curl -X POST http://localhost:8010/analyze-file \
  -F "framework=pytorch" \
  -F "file=@synthetic-note.txt"
```

Notes:

- Scanned PDFs without embedded text are rejected.
- Uploaded text must be fictional or synthetic.

### `GET /models`

Returns the active serving status for each framework.

Response:

```json
[
  {
    "framework": "pytorch",
    "model_name": "pytorch-rule-based-v0",
    "status": "placeholder",
    "description": "Rule-based dictionary extractor standing in for a pytorch NER model."
  }
]
```

`status` values:

| Status | Meaning |
| --- | --- |
| `available` | The requested framework pipeline loaded successfully |
| `placeholder` | The framework fell back to the rule-based extractor |

### `GET /history`

Lists prior persisted analyses, newest first.

Query parameters:

| Name | Default | Description |
| --- | ---: | --- |
| `limit` | `20` | Maximum records to return, capped at 200 |
| `offset` | `0` | Pagination offset |

Example:

```bash
curl "http://localhost:8010/history?limit=10&offset=0"
```

### `POST /benchmarks/run`

Runs all frameworks over the synthetic sample notes using the same serving path as the API, then persists the benchmark run.

Query parameters:

| Name | Default | Range | Description |
| --- | ---: | --- | --- |
| `iterations` | `5` | `1` to `50` | Number of passes over the sample-note set |

Example:

```bash
curl -X POST "http://localhost:8010/benchmarks/run?iterations=3"
```

Response includes per-framework:

- model name
- availability status
- mean, p50, and p95 latency in milliseconds
- mean confidence
- mean entity count
- mean ICD-10 suggestion count
- approximate process RSS memory

### `GET /benchmarks`

Lists stored benchmark runs.

Query parameters:

| Name | Default | Description |
| --- | ---: | --- |
| `limit` | `20` | Maximum benchmark runs to return, capped at 100 |

### `POST /api/extract`

Legacy stateless extraction endpoint. It does not persist results and always uses the rule-based extraction service.

Request:

```json
{
  "text": "Synthetic note text"
}
```

### `POST /api/notes`

Legacy note creation endpoint. It persists a note, runs the rule-based extractor, and stores the extraction.

Request:

```json
{
  "title": "Synthetic sample",
  "text": "Synthetic note text",
  "source": "manual"
}
```

### `GET /api/notes`

Lists stored notes.

Query parameters:

| Name | Default | Description |
| --- | ---: | --- |
| `limit` | `50` | Maximum notes to return, capped at 200 |
| `offset` | `0` | Pagination offset |

### `GET /api/notes/{note_id}`

Returns a stored note with its associated extractions.

## Error Behavior

| Status | Typical Cause |
| ---: | --- |
| `422` | Invalid request body, empty note, unsupported upload, PDF with no text layer |
| `404` | Note ID not found for legacy note lookup |
| `500` | Unexpected service or database error |

## Safety Notes

- This API is not authenticated.
- It is intended for local demos and portfolio review only.
- Do not expose it publicly without authentication, rate limiting, audit logging, request size controls, and a formal healthcare security/privacy review.
