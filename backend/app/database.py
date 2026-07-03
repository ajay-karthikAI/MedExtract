from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_database_prerequisites() -> None:
    """Install database prerequisites needed by SQL defaults before create_all."""
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))


def run_startup_migrations() -> None:
    """Small idempotent schema repairs for dev volumes created before migrations.

    This project intentionally avoids a full migration tool for the portfolio demo,
    but existing Docker volumes may predate newer columns/tables. These statements
    keep `docker compose up` usable after incremental schema changes.
    """
    statements = [
        "ALTER TABLE notes ADD COLUMN IF NOT EXISTS title TEXT",
        "ALTER TABLE notes ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'manual'",
        "ALTER TABLE notes ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS model_name TEXT NOT NULL DEFAULT 'rule-based-v0'",
        "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS framework TEXT",
        "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS summary TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE extractions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE entities ADD COLUMN IF NOT EXISTS normalized TEXT",
        "ALTER TABLE entities ADD COLUMN IF NOT EXISTS span_start INTEGER",
        "ALTER TABLE entities ADD COLUMN IF NOT EXISTS span_end INTEGER",
        "ALTER TABLE entities ADD COLUMN IF NOT EXISTS confidence REAL NOT NULL DEFAULT 1.0",
        "ALTER TABLE icd10_suggestions ADD COLUMN IF NOT EXISTS confidence REAL NOT NULL DEFAULT 0.5",
        """
        CREATE TABLE IF NOT EXISTS benchmark_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            notes_count INTEGER NOT NULL,
            iterations INTEGER NOT NULL,
            results JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_extractions_note_id ON extractions(note_id)",
        "CREATE INDEX IF NOT EXISTS idx_entities_extraction_id ON entities(extraction_id)",
        "CREATE INDEX IF NOT EXISTS idx_entities_category ON entities(category)",
        "CREATE INDEX IF NOT EXISTS idx_icd10_extraction_id ON icd10_suggestions(extraction_id)",
        "CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_benchmark_runs_created_at ON benchmark_runs(created_at DESC)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
