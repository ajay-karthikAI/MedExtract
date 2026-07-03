-- Benchmark runs comparing the framework pipelines. Also created automatically
-- at backend startup (Base.metadata.create_all) for pre-existing volumes.

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notes_count  INTEGER NOT NULL,
    iterations   INTEGER NOT NULL,
    results      JSONB NOT NULL,     -- per-framework metrics
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_created_at ON benchmark_runs(created_at DESC);
