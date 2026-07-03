export type Framework = "pytorch" | "tensorflow" | "jax";

export type EntityCategory = "condition" | "symptom" | "medication" | "procedure";

export interface Entity {
  category: EntityCategory;
  text: string;
  normalized: string | null;
  span_start: number | null;
  span_end: number | null;
  confidence: number;
}

export interface IcdCode {
  code: string;
  description: string;
  confidence: number;
}

export interface EntityGroups {
  conditions: Entity[];
  symptoms: Entity[];
  medications: Entity[];
  procedures: Entity[];
}

export interface AnalyzeResponse {
  entities: EntityGroups;
  icd_codes: IcdCode[];
  patient_summary: string;
  model_used: string;
  confidence: number;
  disclaimer: string;
}

export interface HistoryItem extends AnalyzeResponse {
  id: string;
  note_id: string;
  framework: Framework | null;
  note_title: string | null;
  note_preview: string;
  created_at: string;
}

export type AnalyzeInput = { kind: "text"; note: string } | { kind: "file"; file: File };

export interface BenchmarkFrameworkResult {
  framework: Framework;
  model_name: string;
  status: "available" | "placeholder";
  mean_ms: number;
  p50_ms: number;
  p95_ms: number;
  mean_confidence: number;
  mean_entities: number;
  mean_icd_codes: number;
  rss_mb: number | null;
  rss_delta_mb: number | null;
}

export interface BenchmarkRun {
  id: string;
  notes_count: number;
  iterations: number;
  results: BenchmarkFrameworkResult[];
  created_at: string;
}

export interface ModelInfo {
  framework: Framework;
  model_name: string;
  status: "available" | "placeholder";
  description: string;
}
