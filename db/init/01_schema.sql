-- MedExtract schema. Applied automatically by the postgres container on first start.
-- Contains no data; sample notes live in data/sample_notes/ and are synthetic.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT,
    body        TEXT NOT NULL,
    source      TEXT NOT NULL DEFAULT 'manual',   -- manual | sample | api
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extractions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id      UUID NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    model_name   TEXT NOT NULL DEFAULT 'rule-based-v0',
    framework    TEXT,                                  -- pytorch | tensorflow | jax | NULL (framework-agnostic)
    summary      TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One row per extracted entity (condition, symptom, medication, procedure).
CREATE TABLE IF NOT EXISTS entities (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id  UUID NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,
    category       TEXT NOT NULL CHECK (category IN ('condition', 'symptom', 'medication', 'procedure')),
    text           TEXT NOT NULL,          -- surface form found in the note
    normalized     TEXT,                   -- canonical form, if known
    span_start     INTEGER,                -- character offsets into notes.body
    span_end       INTEGER,
    confidence     REAL NOT NULL DEFAULT 1.0,
    source         TEXT NOT NULL DEFAULT 'rule' CHECK (source IN ('rule', 'model', 'both', 'ensemble_agreement')),
    warning        TEXT
);

-- Suggested ICD-10 codes (heuristic; for human review only).
CREATE TABLE IF NOT EXISTS icd10_suggestions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id  UUID NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,
    code           TEXT NOT NULL,
    description    TEXT NOT NULL,
    confidence     REAL NOT NULL DEFAULT 0.5
);

CREATE INDEX IF NOT EXISTS idx_extractions_note_id ON extractions(note_id);
CREATE INDEX IF NOT EXISTS idx_entities_extraction_id ON entities(extraction_id);
CREATE INDEX IF NOT EXISTS idx_entities_category ON entities(category);
CREATE INDEX IF NOT EXISTS idx_icd10_extraction_id ON icd10_suggestions(extraction_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC);
