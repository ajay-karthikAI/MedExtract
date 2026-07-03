"""Benchmark the framework pipelines against each other.

POST /benchmarks/run executes every framework over the synthetic sample notes
(timed on the same serving path the API uses), persists the run to PostgreSQL,
and returns it. GET /benchmarks lists stored runs, newest first.

Memory numbers are best-effort: process-level RSS, so a framework's delta
mostly reflects lazy model loading on its first run in the process — near zero
if the model was already loaded by earlier requests.
"""

import os
import resource
import statistics
import subprocess
import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.analyze import FRAMEWORKS
from app.services import pipelines
from app.services.paths import sample_notes_dir

router = APIRouter(tags=["benchmarks"])

# Used when data/sample_notes/ isn't shipped with the deployment (e.g. Docker).
_FALLBACK_NOTES = [
    "Chief complaint: chest pain and shortness of breath. PMH: hypertension, "
    "type 2 diabetes. Medications: lisinopril, metformin. Plan: ECG and chest x-ray.",
    "Recurrent headache with nausea and light sensitivity. History of migraine. "
    "Taking sumatriptan. MRI scheduled.",
    "Two days of dysuria and urinary frequency. Urinalysis consistent with "
    "urinary tract infection. Start nitrofurantoin.",
]


def _load_notes() -> list[str]:
    notes_dir = sample_notes_dir()
    notes = [
        p.read_text()
        for p in sorted(notes_dir.glob("note_*.txt"))
        if p.is_file()
    ]
    return notes or _FALLBACK_NOTES


def _rss_mb() -> float | None:
    """Current process RSS in MB; None if unavailable."""
    try:
        # Linux containers usually have /proc even when procps/ps is absent.
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except Exception:
        pass

    try:
        # macOS reports bytes; Linux reports KB. This is max RSS, not current,
        # but it is a useful fallback when /proc is unavailable.
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        divisor = 1024 * 1024 if os.uname().sysname == "Darwin" else 1024
        return round(rss / divisor, 1)
    except Exception:
        pass

    try:
        out = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(os.getpid())],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return round(int(out.stdout.strip()) / 1024, 1)
    except Exception:
        return None


def _confidence(result: schemas.ExtractionResult) -> float:
    entities = result.conditions + result.symptoms + result.medications + result.procedures
    scores = [e.confidence for e in entities] + [c.confidence for c in result.icd10_suggestions]
    return sum(scores) / len(scores) if scores else 0.0


def _benchmark_framework(
    framework: schemas.Framework, notes: list[str], iterations: int
) -> schemas.BenchmarkFrameworkResult:
    rss_before = _rss_mb()
    pipelines.extract(notes[0], framework)  # warm-up: lazy model load + JIT, untimed

    times_ms: list[float] = []
    confidences: list[float] = []
    entity_counts: list[int] = []
    icd_counts: list[int] = []
    for _ in range(iterations):
        for note in notes:
            started = time.perf_counter()
            result = pipelines.extract(note, framework)
            times_ms.append((time.perf_counter() - started) * 1000)
            confidences.append(_confidence(result))
            entity_counts.append(
                len(result.conditions)
                + len(result.symptoms)
                + len(result.medications)
                + len(result.procedures)
            )
            icd_counts.append(len(result.icd10_suggestions))

    rss_after = _rss_mb()
    info = pipelines.model_info(framework)
    times_sorted = sorted(times_ms)
    return schemas.BenchmarkFrameworkResult(
        framework=framework,
        model_name=info.model_name,
        status=info.status,
        mean_ms=round(statistics.mean(times_ms), 2),
        p50_ms=round(statistics.median(times_sorted), 2),
        p95_ms=round(times_sorted[max(0, int(len(times_sorted) * 0.95) - 1)], 2),
        mean_confidence=round(statistics.mean(confidences), 3),
        mean_entities=round(statistics.mean(entity_counts), 2),
        mean_icd_codes=round(statistics.mean(icd_counts), 2),
        rss_mb=rss_after,
        rss_delta_mb=(
            round(max(rss_after - rss_before, 0.0), 1)
            if rss_after is not None and rss_before is not None
            else None
        ),
    )


@router.post("/benchmarks/run", response_model=schemas.BenchmarkRunOut)
def run_benchmarks(
    iterations: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)
):
    """Run all frameworks over the sample notes and persist the results."""
    notes = _load_notes()
    results = [_benchmark_framework(fw, notes, iterations) for fw in FRAMEWORKS]
    run = models.BenchmarkRun(
        notes_count=len(notes),
        iterations=iterations,
        results=[r.model_dump() for r in results],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/benchmarks", response_model=list[schemas.BenchmarkRunOut])
def list_benchmarks(limit: int = 20, db: Session = Depends(get_db)):
    stmt = (
        select(models.BenchmarkRun)
        .order_by(models.BenchmarkRun.created_at.desc())
        .limit(min(limit, 100))
    )
    return db.scalars(stmt).all()
