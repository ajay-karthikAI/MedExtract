import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    title: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    created_at: Mapped[datetime] = mapped_column(server_default=sql_text("now()"))

    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    note_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"))
    model_name: Mapped[str] = mapped_column(Text, nullable=False, server_default="rule-based-v0")
    framework: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(server_default=sql_text("now()"))

    note: Mapped[Note] = relationship(back_populates="extractions")
    entities: Mapped[list["Entity"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )
    icd10_suggestions: Mapped[list["Icd10Suggestion"]] = relationship(
        back_populates="extraction", cascade="all, delete-orphan"
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("extractions.id", ondelete="CASCADE")
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[str | None] = mapped_column(Text)
    span_start: Mapped[int | None]
    span_end: Mapped[int | None]
    confidence: Mapped[float] = mapped_column(server_default=sql_text("1.0"))

    extraction: Mapped[Extraction] = relationship(back_populates="entities")


class Icd10Suggestion(Base):
    __tablename__ = "icd10_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("extractions.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(server_default=sql_text("0.5"))

    extraction: Mapped[Extraction] = relationship(back_populates="icd10_suggestions")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=sql_text("gen_random_uuid()")
    )
    notes_count: Mapped[int] = mapped_column(nullable=False)
    iterations: Mapped[int] = mapped_column(nullable=False)
    # Per-framework metrics: [{framework, model_name, status, mean_ms, ...}, ...]
    results: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=sql_text("now()"))
