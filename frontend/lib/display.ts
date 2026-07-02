import type { EntityGroups, Framework } from "./types";

// Category accents validated as a categorical palette (CVD ΔE 31.3, all checks
// pass on white). Identity is never color-alone — every use sits next to a label.
export const CATEGORIES = [
  {
    key: "conditions",
    label: "Conditions",
    dot: "bg-rose-600",
    chip: "bg-rose-50 text-rose-800 ring-1 ring-inset ring-rose-200",
  },
  {
    key: "symptoms",
    label: "Symptoms",
    dot: "bg-amber-600",
    chip: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200",
  },
  {
    key: "medications",
    label: "Medications",
    dot: "bg-emerald-600",
    chip: "bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-emerald-200",
  },
  {
    key: "procedures",
    label: "Procedures",
    dot: "bg-sky-600",
    chip: "bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-200",
  },
] as const satisfies readonly { key: keyof EntityGroups; label: string; dot: string; chip: string }[];

export const FRAMEWORKS: { value: Framework; label: string }[] = [
  { value: "pytorch", label: "PyTorch" },
  { value: "tensorflow", label: "TensorFlow" },
  { value: "jax", label: "JAX" },
];

export function frameworkLabel(fw: string | null): string {
  return FRAMEWORKS.find((f) => f.value === fw)?.label ?? "—";
}

export function entityCount(groups: EntityGroups): number {
  return (
    groups.conditions.length +
    groups.symptoms.length +
    groups.medications.length +
    groups.procedures.length
  );
}

export function percent(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}
