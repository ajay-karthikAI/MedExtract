import { entityCount, frameworkLabel, percent } from "@/lib/display";
import type { AnalyzeResponse, Entity, EntityGroups, IcdCode } from "@/lib/types";

type CategoryKey = keyof EntityGroups;

const RESULT_CATEGORIES: {
  key: CategoryKey;
  label: string;
  icon: string;
  accent: string;
  iconText: string;
}[] = [
  {
    key: "conditions",
    label: "Conditions",
    icon: "heart",
    accent: "bg-blue-500/15 border-blue-500/20",
    iconText: "text-blue-300",
  },
  {
    key: "symptoms",
    label: "Symptoms",
    icon: "flask",
    accent: "bg-violet-500/15 border-violet-500/20",
    iconText: "text-violet-300",
  },
  {
    key: "medications",
    label: "Medications",
    icon: "pill",
    accent: "bg-teal-500/15 border-teal-500/20",
    iconText: "text-teal-300",
  },
  {
    key: "procedures",
    label: "Procedures / Tests",
    icon: "grid",
    accent: "bg-amber-500/15 border-amber-500/20",
    iconText: "text-amber-300",
  },
];

function Icon({ name, className = "h-4 w-4" }: { name: string; className?: string }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    "aria-hidden": true,
  };
  if (name === "heart") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M12 21s-7-4.6-9.5-8.5C.6 9.3 2.4 5.5 6 5.5c2 0 3.2 1 4 2.2.8-1.2 2-2.2 4-2.2 3.6 0 5.4 3.8 3.5 7C19 16.4 12 21 12 21z" />
      </svg>
    );
  }
  if (name === "flask") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M9 3h6M10 3v5l-5.5 9.5A2.3 2.3 0 0 0 6.5 21h11a2.3 2.3 0 0 0 2-3.5L14 8V3" />
        <path d="M7.5 16h9" />
      </svg>
    );
  }
  if (name === "pill") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="m10.5 20.5 10-10a5 5 0 0 0-7-7l-10 10a5 5 0 0 0 7 7Z" />
        <path d="m8.5 8.5 7 7" />
      </svg>
    );
  }
  if (name === "grid") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />
      </svg>
    );
  }
  if (name === "users") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" />
        <circle cx="9.5" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" />
      </svg>
    );
  }
  if (name === "shield") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
        <path d="m9 12 2 2 4-5" />
      </svg>
    );
  }
  return null;
}

function confidenceValue(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value * 100)));
}

function ConfidenceRing({ confidence }: { confidence: number }) {
  const value = confidenceValue(confidence);
  const circumference = 2 * Math.PI * 18;
  const offset = circumference - (circumference * value) / 100;

  return (
    <div className="relative h-14 w-14 shrink-0">
      <svg viewBox="0 0 44 44" className="h-full w-full -rotate-90">
        <circle cx="22" cy="22" r="18" stroke="rgb(30 41 59)" strokeWidth="4" fill="none" />
        <circle
          cx="22"
          cy="22"
          r="18"
          stroke="rgb(37 99 235)"
          strokeWidth="4"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
        {value}%
      </span>
    </div>
  );
}

function entityName(entity: Entity): string {
  return entity.normalized ?? entity.text;
}

function CategoryCard({ category, entities }: { category: (typeof RESULT_CATEGORIES)[number]; entities: Entity[] }) {
  const visible = entities.slice(0, 5);

  return (
    <section className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
      <header className="mb-4 flex items-center gap-3">
        <div className={`flex h-9 w-9 items-center justify-center rounded-lg border ${category.accent} ${category.iconText}`}>
          <Icon name={category.icon} />
        </div>
        <h3 className="flex-1 text-sm font-semibold text-white">{category.label}</h3>
        <span className="rounded-md bg-white/[0.06] px-2 py-1 text-xs text-slate-300">
          {entities.length} found
        </span>
      </header>
      {visible.length === 0 ? (
        <p className="text-sm text-slate-500">None detected</p>
      ) : (
        <ul className="space-y-2.5">
          {visible.map((entity, index) => (
            <li key={`${entity.text}-${index}`} className="flex items-center gap-3 text-sm">
              <span className="min-w-0 flex-1 truncate text-slate-200" title={entityName(entity)}>
                {entityName(entity)}
              </span>
              <span className="shrink-0 tabular-nums text-slate-300">{percent(entity.confidence)}</span>
            </li>
          ))}
        </ul>
      )}
      {entities.length > visible.length && (
        <button type="button" className="mt-4 text-sm font-medium text-blue-400">
          Show all
        </button>
      )}
    </section>
  );
}

export function CategoryGrid({ groups }: { groups: EntityGroups }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {RESULT_CATEGORIES.map((category) => (
        <CategoryCard key={category.key} category={category} entities={groups[category.key]} />
      ))}
    </div>
  );
}

export function SummaryCard({ summary }: { summary: string }) {
  return (
    <section className="overflow-hidden rounded-lg border border-white/10 bg-white/[0.035]">
      <header className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
        <Icon name="users" className="h-4 w-4 text-cyan-300" />
        <h3 className="text-sm font-semibold text-white">Patient-friendly summary</h3>
      </header>
      <div className="px-5 py-5">
        <p className="text-sm leading-7 text-slate-300">{summary}</p>
        <p className="mt-5 text-sm font-medium leading-7 text-slate-200">
          This is a simplified summary, not a diagnosis.
        </p>
      </div>
      <footer className="flex items-center gap-2 border-t border-white/10 px-5 py-4 text-xs text-slate-500">
        <Icon name="shield" className="h-4 w-4 text-blue-400" />
        Generated by MedExtract
      </footer>
    </section>
  );
}

export function IcdList({ codes }: { codes: IcdCode[] }) {
  const visible = codes.slice(0, 5);

  return (
    <section className="overflow-hidden rounded-lg border border-white/10 bg-white/[0.035]">
      <header className="border-b border-white/10 px-5 py-4">
        <h3 className="text-sm font-semibold text-white">Top ICD-10 suggestions</h3>
      </header>
      <div className="space-y-4 px-5 py-5">
        {visible.length === 0 ? (
          <p className="text-sm text-slate-500">No suggestions for this note</p>
        ) : (
          visible.map((code, index) => (
            <div key={code.code}>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-semibold text-white">{code.code}</span>
                {index === 0 && (
                  <span className="rounded-md bg-blue-600 px-2 py-0.5 text-[11px] font-semibold text-white">
                    Primary
                  </span>
                )}
                <span className="ml-auto text-xs tabular-nums text-slate-500">
                  {percent(code.confidence)}
                </span>
              </div>
              <p className="mt-1 text-xs leading-5 text-slate-400">{code.description}</p>
            </div>
          ))
        )}
        {codes.length > visible.length && (
          <button type="button" className="text-sm font-medium text-blue-400">
            Show more
          </button>
        )}
      </div>
    </section>
  );
}

export function EmptyResults() {
  return (
    <section className="flex min-h-[640px] rounded-lg border border-white/10 bg-[#0b1119]/90 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
      <div className="m-auto max-w-sm text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-500/10 text-blue-300">
          <Icon name="shield" className="h-5 w-5" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-white">Analysis results</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Run an analysis to populate entities, ICD-10 suggestions, confidence, and summary.
        </p>
      </div>
    </section>
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
    <section className="rounded-lg border border-white/10 bg-[#0b1119]/90 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)]">
      <header className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-white">Analysis results</h2>
          <p className="mt-1 text-xs text-slate-500">
            {entityCount(result.entities)} entities · {result.icd_codes.length} ICD hints ·{" "}
            {frameworkLabel(framework)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-slate-500 sm:inline">Confidence overview</span>
          <ConfidenceRing confidence={result.confidence} />
        </div>
      </header>

      <div className="mb-4 flex gap-7 border-b border-white/10 text-sm">
        {["Overview", "Entities", "Codes", "Summary", "Evidence"].map((tab, index) => (
          <button
            key={tab}
            type="button"
            className={`relative pb-3 font-medium ${
              index === 0 ? "text-blue-400" : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab}
            {index === 0 && <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-500" />}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(260px,0.9fr)]">
        <div className="space-y-3">
          {RESULT_CATEGORIES.map((category) => (
            <CategoryCard key={category.key} category={category} entities={result.entities[category.key]} />
          ))}
        </div>
        <div className="space-y-4">
          <IcdList codes={result.icd_codes} />
          <SummaryCard summary={result.patient_summary} />
        </div>
      </div>

      <p className="mt-4 text-xs leading-6 text-slate-500">{result.disclaimer}</p>
    </section>
  );
}
