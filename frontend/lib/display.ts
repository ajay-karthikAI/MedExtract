import type { EntityGroups, Framework } from "./types";

// Category accents validated as categorical palettes in both modes (light:
// CVD ΔE 31.3; dark: ΔE 33.6 with rose stepped to 500). Identity is never
// color-alone — every use sits next to a label.
export const CATEGORIES = [
  {
    key: "conditions",
    label: "Conditions",
    dot: "bg-rose-600 dark:bg-rose-500",
    chip: "bg-rose-50 text-rose-800 ring-1 ring-inset ring-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:ring-rose-900",
  },
  {
    key: "symptoms",
    label: "Symptoms",
    dot: "bg-amber-600",
    chip: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-900",
  },
  {
    key: "medications",
    label: "Medications",
    dot: "bg-emerald-600",
    chip: "bg-emerald-50 text-emerald-800 ring-1 ring-inset ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-900",
  },
  {
    key: "procedures",
    label: "Procedures",
    dot: "bg-sky-600",
    chip: "bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-200 dark:bg-sky-950/40 dark:text-sky-300 dark:ring-sky-900",
  },
] as const satisfies readonly { key: keyof EntityGroups; label: string; dot: string; chip: string }[];

// Framework accents validated as categorical palettes in both modes (light:
// CVD ΔE 53.4; dark: ΔE 53.4 with violet stepped to 500). Fixed assignment —
// color follows the framework.
export const FRAMEWORKS: { value: Framework; label: string; dot: string; bar: string }[] = [
  {
    value: "pytorch",
    label: "PyTorch",
    dot: "bg-violet-600 dark:bg-violet-500",
    bar: "bg-violet-600 dark:bg-violet-500",
  },
  { value: "tensorflow", label: "TensorFlow", dot: "bg-orange-600", bar: "bg-orange-600" },
  { value: "jax", label: "JAX", dot: "bg-teal-600", bar: "bg-teal-600" },
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
