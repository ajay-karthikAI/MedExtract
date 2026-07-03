import type { Entity } from "./types";

export interface AnnotatableEntity {
  id: string;
  entity: Entity;
}

export interface EntityAnnotation extends AnnotatableEntity {
  start: number;
  end: number;
}

export type AnnotationSegment =
  | { kind: "text"; text: string; start: number; end: number }
  | { kind: "entity"; text: string; annotation: EntityAnnotation };

function validSpan(text: string, start: number | null, end: number | null): start is number {
  return start !== null && end !== null && start >= 0 && end > start && end <= text.length;
}

function findOccurrences(text: string, needle: string): Array<{ start: number; end: number }> {
  const query = needle.trim();
  if (!query) return [];
  const lowerText = text.toLowerCase();
  const lowerQuery = query.toLowerCase();
  const spans: Array<{ start: number; end: number }> = [];
  let index = lowerText.indexOf(lowerQuery);
  while (index >= 0) {
    spans.push({ start: index, end: index + query.length });
    index = lowerText.indexOf(lowerQuery, index + Math.max(1, query.length));
  }
  return spans;
}

export function buildEntityAnnotations(
  text: string,
  entities: AnnotatableEntity[],
): EntityAnnotation[] {
  const candidates: EntityAnnotation[] = [];

  for (const item of entities) {
    const { entity } = item;
    if (validSpan(text, entity.span_start, entity.span_end)) {
      candidates.push({ ...item, start: entity.span_start, end: entity.span_end ?? entity.span_start });
      continue;
    }

    const terms = [entity.text, entity.normalized ?? ""].filter(Boolean);
    const seen = new Set<string>();
    for (const term of terms) {
      for (const span of findOccurrences(text, term)) {
        const key = `${span.start}:${span.end}`;
        if (seen.has(key)) continue;
        seen.add(key);
        candidates.push({ ...item, ...span });
      }
      if (seen.size > 0) break;
    }
  }

  return candidates
    .sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start))
    .reduce<EntityAnnotation[]>((accepted, candidate) => {
      const overlaps = accepted.some((item) => item.start < candidate.end && candidate.start < item.end);
      if (!overlaps) accepted.push(candidate);
      return accepted;
    }, [])
    .sort((a, b) => a.start - b.start || a.end - b.end);
}

export function buildAnnotationSegments(
  text: string,
  annotations: EntityAnnotation[],
): AnnotationSegment[] {
  const segments: AnnotationSegment[] = [];
  let cursor = 0;

  for (const annotation of annotations) {
    if (annotation.start > cursor) {
      segments.push({
        kind: "text",
        text: text.slice(cursor, annotation.start),
        start: cursor,
        end: annotation.start,
      });
    }
    segments.push({
      kind: "entity",
      text: text.slice(annotation.start, annotation.end),
      annotation,
    });
    cursor = annotation.end;
  }

  if (cursor < text.length) {
    segments.push({ kind: "text", text: text.slice(cursor), start: cursor, end: text.length });
  }

  return segments;
}
