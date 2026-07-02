import { CATEGORIES, entityCount, frameworkLabel, percent } from "@/lib/display";
import type { AnalyzeResponse, Entity, EntityGroups, IcdCode } from "@/lib/types";

export function CategoryGrid({ groups }: { groups: EntityGroups }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {CATEGORIES.map(({ key, label, dot, chip }) => {
        const entities: Entity[] = groups[key];
        return (
          <section key={key} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <header className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden />
                <h3 className="text-sm font-semibold text-slate-800">{label}</h3>
              </div>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium tabular-nums text-slate-500">
                {entities.length}
              </span>
            </header>
            {entities.length === 0 ? (
              <p className="text-sm text-slate-300">None detected</p>
            ) : (
              <ul className="flex flex-wrap gap-1.5">
                {entities.map((e, i) => (
                  <li
                    key={`${e.text}-${i}`}
                    title={e.normalized && e.normalized !== e.text.toLowerCase() ? `“${e.text}” in note` : undefined}
                    className={`rounded-full px-2.5 py-1 text-[13px] font-medium ${chip}`}
                  >
                    {e.normalized ?? e.text}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}

export function SummaryCard({ summary }: { summary: string }) {
  return (
    <section className="rounded-2xl border border-teal-200/70 bg-teal-50/60 p-6">
      <header className="mb-2 flex items-center gap-2">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4 text-teal-700"
          aria-hidden
        >
          <path d="M12 21s-7-4.6-9.5-8.5C.6 9.3 2.4 5.5 6 5.5c2 0 3.2 1 4 2.2.8-1.2 2-2.2 4-2.2 3.6 0 5.4 3.8 3.5 7C19 16.4 12 21 12 21z" />
        </svg>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-teal-800">
          Patient-friendly summary
        </h2>
      </header>
      <p className="max-w-3xl leading-relaxed text-slate-700">{summary}</p>
    </section>
  );
}

export function IcdList({ codes }: { codes: IcdCode[] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <header className="mb-4 flex items-baseline gap-2">
        <h3 className="text-sm font-semibold text-slate-800">ICD-10 suggestions</h3>
        <span className="text-xs text-slate-400">heuristic — for human review only</span>
      </header>
      {codes.length === 0 ? (
        <p className="text-sm text-slate-300">No suggestions for this note</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {codes.map((c) => (
            <li key={c.code} className="flex items-center gap-4 py-2.5">
              <span className="w-20 shrink-0 rounded-md bg-slate-100 px-2 py-1 text-center font-mono text-[13px] font-semibold text-slate-700">
                {c.code}
              </span>
              <span className="min-w-0 flex-1 truncate text-sm text-slate-600" title={c.description}>
                {c.description}
              </span>
              <span className="flex w-32 shrink-0 items-center gap-2">
                <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                  <span
                    className="block h-full rounded-full bg-teal-600"
                    style={{ width: percent(c.confidence) }}
                  />
                </span>
                <span className="w-9 text-right text-xs tabular-nums text-slate-500">
                  {percent(c.confidence)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function StatTile({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="mt-1.5">{children}</div>
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
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Entities found">
          <span className="text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
            {entityCount(result.entities)}
          </span>
        </StatTile>
        <StatTile label="ICD-10 suggestions">
          <span className="text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
            {result.icd_codes.length}
          </span>
        </StatTile>
        <StatTile label="Mean confidence">
          <span className="text-3xl font-semibold tabular-nums tracking-tight text-slate-900">
            {percent(result.confidence)}
          </span>
          <span className="mt-2 block h-1.5 overflow-hidden rounded-full bg-slate-100">
            <span
              className="block h-full rounded-full bg-teal-600"
              style={{ width: percent(result.confidence) }}
            />
          </span>
        </StatTile>
        <StatTile label="Model">
          <span className="block truncate font-mono text-sm text-slate-700" title={result.model_used}>
            {result.model_used}
          </span>
          <span className="mt-1 block text-xs text-slate-400">{frameworkLabel(framework)}</span>
        </StatTile>
      </div>

      <SummaryCard summary={result.patient_summary} />
      <CategoryGrid groups={result.entities} />
      <IcdList codes={result.icd_codes} />

      <p className="text-xs leading-relaxed text-slate-400">{result.disclaimer}</p>
    </div>
  );
}
