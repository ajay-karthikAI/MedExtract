"use client";

import { useEffect, useMemo, useRef, type CSSProperties } from "react";
import {
  buildAnnotationSegments,
  buildEntityAnnotations,
  type EntityAnnotation,
} from "@/lib/annotate";
import { entityCount, percent } from "@/lib/display";
import type { AnalyzeResponse, Entity, EntityGroups, IcdCode } from "@/lib/types";

type CategoryKey = keyof EntityGroups;

export type EntityRow = {
  id: string;
  entity: Entity;
  categoryKey: CategoryKey;
  categoryLabel: string;
};

const CATEGORIES: Array<{ key: CategoryKey; label: string; token: string }> = [
  { key: "conditions", label: "Conditions", token: "condition" },
  { key: "symptoms", label: "Symptoms", token: "symptom" },
  { key: "medications", label: "Medications", token: "medication" },
  { key: "procedures", label: "Procedures / Tests", token: "procedure" },
];

const SOURCE_LABEL: Record<Entity["source"], string> = {
  rule: "rule",
  model: "model",
  both: "both",
  ensemble_agreement: "ensemble",
};

function entityName(entity: Entity): string {
  return entity.normalized || entity.text;
}

function confidenceDecimal(value: number): string {
  return value.toFixed(2);
}

function sourceConfidence(entity: Entity): string {
  return `${SOURCE_LABEL[entity.source]} · ${confidenceDecimal(entity.confidence)}`;
}

function categoryToken(category: Entity["category"]): string {
  if (category === "condition") return "condition";
  if (category === "symptom") return "symptom";
  if (category === "medication") return "medication";
  return "procedure";
}

function tokenStyle(token: string): CSSProperties {
  return {
    ["--entity-color" as string]: `var(--${token})`,
    ["--entity-bg" as string]: `var(--${token}-bg)`,
  };
}

export function flattenEntityRows(groups: EntityGroups): EntityRow[] {
  let index = 0;
  return CATEGORIES.flatMap((category) =>
    groups[category.key].map((entity) => ({
      id: `${entity.category}:${entity.normalized || entity.text}:${entity.span_start ?? "x"}:${entity.span_end ?? "x"}:${index++}`,
      entity,
      categoryKey: category.key,
      categoryLabel: category.label,
    })),
  );
}

function ConfidenceCells({ value }: { value: number }) {
  const filled = Math.max(0, Math.min(5, Math.round(value * 5)));
  const low = value < 0.5;
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`confidence ${percent(value)}`}>
      {Array.from({ length: 5 }, (_, index) => (
        <span
          key={index}
          className="h-3 w-1.5 border border-[var(--rule-strong)]"
          style={{
            background:
              index < filled ? (low ? "var(--alert)" : "var(--ink)") : "transparent",
          }}
        />
      ))}
      {low && <span className="ml-1 text-[10px] font-bold text-[var(--alert)]">L</span>}
    </span>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-[var(--rule)] py-3 first:border-t-0 first:pt-0">
      <h3 className="chart-label mb-2">{label}</h3>
      {children}
    </section>
  );
}

function EmptyRow() {
  return <p className="py-1 text-[12px] text-[var(--ink-soft)]">none detected</p>;
}

function EntityRailRow({
  row,
  active,
  onFocus,
}: {
  row: EntityRow;
  active: boolean;
  onFocus: (id: string) => void;
}) {
  const ref = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (active) ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [active]);

  const token = categoryToken(row.entity.category);

  return (
    <button
      ref={ref}
      type="button"
      onMouseEnter={() => onFocus(row.id)}
      onFocus={() => onFocus(row.id)}
      onClick={() => onFocus(row.id)}
      className={`focus-ring grid min-h-8 w-full grid-cols-[12px_minmax(0,1fr)_92px_48px] items-center gap-2 border-l-2 px-1.5 py-1 text-left text-[12px] transition ${
        active ? "bg-[var(--paper-muted)]" : "border-l-transparent hover:bg-[var(--paper-muted)]"
      }`}
      style={{
        borderLeftColor: active ? `var(--${token})` : "transparent",
      }}
    >
      <span className="h-2 w-2 border" style={{ borderColor: `var(--${token})`, background: `var(--${token}-bg)` }} />
      <span className="min-w-0 truncate font-medium" title={entityName(row.entity)}>
        {entityName(row.entity)}
      </span>
      <span className="text-right text-[11px] text-[var(--ink-muted)]">{sourceConfidence(row.entity)}</span>
      <span className="justify-self-end">
        <ConfidenceCells value={row.entity.confidence} />
      </span>
      <span className="col-span-4 truncate pl-5 text-[11px] text-[var(--ink-soft)]">
        evidence: "{row.entity.text}"
      </span>
      {row.entity.warning && (
        <span className="col-span-4 pl-5 text-[11px] text-[var(--alert)]">{row.entity.warning}</span>
      )}
    </button>
  );
}

function entityIdsForCode(code: IcdCode, rows: EntityRow[]): string[] {
  const description = code.description.toLowerCase();
  const hits = rows
    .filter(({ entity }) => entity.category === "condition" || entity.category === "symptom")
    .filter(({ entity }) => {
      const normalized = entityName(entity).toLowerCase();
      return description.includes(normalized) || normalized.split(/\s+/).some((word) => word.length > 4 && description.includes(word));
    })
    .map((row) => row.id);
  return hits.length > 0 ? hits : rows.slice(0, 1).map((row) => row.id);
}

function IcdRail({
  codes,
  rows,
  onFocus,
}: {
  codes: IcdCode[];
  rows: EntityRow[];
  onFocus: (id: string) => void;
}) {
  if (codes.length === 0) return <EmptyRow />;
  return (
    <div className="divide-y divide-[var(--rule)]">
      {codes.map((code, index) => {
        const evidenceIds = entityIdsForCode(code, rows);
        return (
          <button
            key={`${code.code}-${index}`}
            type="button"
            onMouseEnter={() => evidenceIds[0] && onFocus(evidenceIds[0])}
            onFocus={() => evidenceIds[0] && onFocus(evidenceIds[0])}
            onClick={() => evidenceIds[0] && onFocus(evidenceIds[0])}
            className="focus-ring grid min-h-9 w-full grid-cols-[72px_minmax(0,1fr)_74px] items-center gap-2 py-1 text-left text-[12px] hover:bg-[var(--paper-muted)]"
          >
            <span className="font-semibold">{code.code}</span>
            <span className="truncate text-[var(--ink-muted)]" title={code.description}>
              {index === 0 && <span className="mr-2 text-[10px] font-bold tracking-[0.08em]">PRIMARY</span>}
              {code.description}
            </span>
            <span className="text-right text-[11px] text-[var(--ink-muted)]">icd · {confidenceDecimal(code.confidence)}</span>
          </button>
        );
      })}
    </div>
  );
}

export function FindingsRail({
  result,
  activeId,
  onActiveIdChange,
}: {
  result: AnalyzeResponse;
  activeId: string | null;
  onActiveIdChange: (id: string) => void;
}) {
  const rows = useMemo(() => flattenEntityRows(result.entities), [result.entities]);

  return (
    <aside className="chart-paper h-fit p-4">
      <div className="mb-3 border-b border-[var(--rule)] pb-3">
        <p className="chart-label">Extraction report</p>
        <p className="mt-1 text-[12px] text-[var(--ink-muted)]">
          overall {confidenceDecimal(result.confidence)} — mean of entity confidences (heuristic)
        </p>
        <p className="mt-1 text-[11px] text-[var(--ink-soft)]">
          High confidence does not replace clinical review.
        </p>
      </div>

      {CATEGORIES.map((category) => {
        const categoryRows = rows.filter((row) => row.categoryKey === category.key);
        return (
          <Section key={category.key} label={category.label.toUpperCase()}>
            {categoryRows.length === 0 ? (
              <EmptyRow />
            ) : (
              <div className="divide-y divide-[var(--rule)]">
                {categoryRows.map((row) => (
                  <EntityRailRow
                    key={row.id}
                    row={row}
                    active={activeId === row.id}
                    onFocus={onActiveIdChange}
                  />
                ))}
              </div>
            )}
          </Section>
        );
      })}

      <Section label="ICD-10 SUGGESTIONS">
        <IcdRail codes={result.icd_codes} rows={rows} onFocus={onActiveIdChange} />
      </Section>

      <Section label="PATIENT SUMMARY">
        <SummaryCard summary={result.patient_summary} compact />
      </Section>

      <p className="border-t border-[var(--rule)] pt-3 text-[11px] leading-5 text-[var(--ink-soft)]">
        {result.disclaimer}
      </p>
    </aside>
  );
}

export function AnnotatedDocument({
  note,
  rows,
  activeId,
  onActiveIdChange,
  onEdit,
}: {
  note: string;
  rows: EntityRow[];
  activeId: string | null;
  onActiveIdChange: (id: string) => void;
  onEdit: () => void;
}) {
  const annotations = useMemo(
    () => buildEntityAnnotations(note, rows.map(({ id, entity }) => ({ id, entity }))),
    [note, rows],
  );
  const segments = useMemo(() => buildAnnotationSegments(note, annotations), [note, annotations]);
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  useEffect(() => {
    if (!activeId) return;
    refs.current[activeId]?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeId]);

  return (
    <section className="chart-paper min-h-[calc(100vh-104px)] overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-3">
        <div>
          <p className="chart-label">Clinical note</p>
          <p className="mt-1 text-[11px] text-[var(--ink-soft)]">{annotations.length} inline annotations</p>
        </div>
        <button
          type="button"
          onClick={onEdit}
          className="focus-ring border border-[var(--rule)] px-3 py-1.5 text-[11px] font-semibold text-[var(--ink-muted)] hover:text-[var(--ink)]"
        >
          EDIT NOTE
        </button>
      </div>

      <pre className="whitespace-pre-wrap px-5 py-5 text-[13px] leading-7 text-[var(--ink)]">
        {segments.map((segment, index) => {
          if (segment.kind === "text") {
            return <span key={`${segment.start}-${segment.end}-${index}`}>{segment.text}</span>;
          }
          const { annotation } = segment;
          const token = categoryToken(annotation.entity.category);
          const active = activeId === annotation.id;
          return (
            <button
              key={`${annotation.id}-${annotation.start}-${annotation.end}-${index}`}
              ref={(node) => {
                refs.current[annotation.id] = node;
              }}
              type="button"
              role="button"
              tabIndex={0}
              aria-label={`${entityName(annotation.entity)}, ${annotation.entity.category}, confidence ${confidenceDecimal(annotation.entity.confidence)}`}
              onMouseEnter={() => onActiveIdChange(annotation.id)}
              onFocus={() => onActiveIdChange(annotation.id)}
              onClick={() => onActiveIdChange(annotation.id)}
              className="focus-ring mx-0.5 border-b-[1.5px] px-0.5 transition"
              style={{
                ...tokenStyle(token),
                color: "var(--ink)",
                borderBottomColor: `var(--${token})`,
                background: active ? `color-mix(in srgb, var(--${token}-bg) 70%, var(--paper-muted))` : `var(--${token}-bg)`,
              }}
            >
              {segment.text}
            </button>
          );
        })}
      </pre>
    </section>
  );
}

export function EmptyResults() {
  return (
    <section className="chart-paper flex min-h-[calc(100vh-104px)] items-center justify-center p-8 text-center">
      <div>
        <p className="chart-label">Extraction report</p>
        <p className="mt-3 max-w-sm text-[13px] leading-6 text-[var(--ink-muted)]">
          Run an analysis to annotate the note and populate clinically anchored findings.
        </p>
      </div>
    </section>
  );
}

export function SummaryCard({ summary, compact = false }: { summary: string; compact?: boolean }) {
  return (
    <div className={`summary-copy text-[13px] leading-6 text-[var(--ink)] ${compact ? "" : "chart-paper p-4"}`}>
      <p>{summary}</p>
    </div>
  );
}

export function IcdList({ codes }: { codes: IcdCode[] }) {
  if (codes.length === 0) {
    return <div className="chart-paper p-4 text-[12px] text-[var(--ink-muted)]">No ICD-10 suggestions.</div>;
  }
  return (
    <div className="chart-paper divide-y divide-[var(--rule)]">
      {codes.map((code, index) => (
        <div key={`${code.code}-${index}`} className="grid grid-cols-[72px_minmax(0,1fr)_72px] gap-3 px-4 py-2 text-[12px]">
          <span className="font-semibold">{code.code}</span>
          <span className="truncate text-[var(--ink-muted)]">{code.description}</span>
          <span className="text-right">{confidenceDecimal(code.confidence)}</span>
        </div>
      ))}
    </div>
  );
}

export function CategoryGrid({ groups }: { groups: EntityGroups }) {
  const rows = flattenEntityRows(groups);
  return (
    <div className="chart-paper divide-y divide-[var(--rule)]">
      {rows.length === 0 ? (
        <p className="p-4 text-[12px] text-[var(--ink-muted)]">No entities detected.</p>
      ) : (
        rows.map((row) => (
          <div key={row.id} className="grid grid-cols-[120px_minmax(0,1fr)_80px] gap-3 px-4 py-2 text-[12px]">
            <span className="text-[var(--ink-muted)]">{row.categoryLabel}</span>
            <span className="truncate">{entityName(row.entity)}</span>
            <span className="text-right">{confidenceDecimal(row.entity.confidence)}</span>
          </div>
        ))
      )}
    </div>
  );
}

export function AnalysisResults({
  result,
  framework,
}: {
  result: AnalyzeResponse;
  framework: string;
}) {
  return (
    <div className="chart-paper p-4 text-[12px] text-[var(--ink-muted)]">
      {entityCount(result.entities)} entities · {result.icd_codes.length} ICD hints · {framework}
    </div>
  );
}
