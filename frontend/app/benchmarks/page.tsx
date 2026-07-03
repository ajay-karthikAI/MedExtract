"use client";

import { useCallback, useEffect, useState } from "react";
import { getBenchmarks, runBenchmark } from "@/lib/api";
import { formatDate, FRAMEWORKS } from "@/lib/display";
import type { BenchmarkFrameworkResult, BenchmarkRun } from "@/lib/types";

const ordered = (results: BenchmarkFrameworkResult[]) =>
  FRAMEWORKS.map((f) => results.find((r) => r.framework === f.value)).filter(
    (r): r is BenchmarkFrameworkResult => r !== undefined,
  );

function MetricPanel({
  title,
  unit,
  hint,
  results,
  value,
  format,
}: {
  title: string;
  unit: string;
  hint?: string;
  results: BenchmarkFrameworkResult[];
  value: (r: BenchmarkFrameworkResult) => number | null;
  format: (v: number) => string;
}) {
  const rows = ordered(results).map((r) => ({ r, v: value(r) }));
  const max = Math.max(...rows.map(({ v }) => v ?? 0), 0);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="mb-4">
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
          {title} <span className="font-normal text-slate-400 dark:text-slate-500">({unit})</span>
        </h3>
        {hint && <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">{hint}</p>}
      </header>
      <div className="space-y-3">
        {rows.map(({ r, v }) => {
          const fw = FRAMEWORKS.find((f) => f.value === r.framework)!;
          return (
            <div key={r.framework} className="flex items-center gap-3">
              <span className="flex w-24 shrink-0 items-center gap-1.5 text-xs font-medium text-slate-600 dark:text-slate-300">
                <span className={`h-2 w-2 rounded-full ${fw.dot}`} aria-hidden />
                {fw.label}
              </span>
              <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                {v !== null && max > 0 && (
                  <span
                    className={`block h-full rounded-full ${fw.bar}`}
                    style={{ width: `${Math.max((v / max) * 100, 2)}%` }}
                  />
                )}
              </span>
              <span className="w-16 shrink-0 text-right text-sm tabular-nums text-slate-900 dark:text-slate-100">
                {v === null ? "—" : format(v)}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RunDetail({ run }: { run: BenchmarkRun }) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricPanel
          title="Inference time"
          unit="ms/note, mean"
          hint="Lower is better · same serving path as /analyze-note"
          results={run.results}
          value={(r) => r.mean_ms}
          format={(v) => v.toFixed(1)}
        />
        <MetricPanel
          title="Confidence"
          unit="mean"
          hint="Mean over entities + ICD codes per note"
          results={run.results}
          value={(r) => r.mean_confidence}
          format={(v) => `${Math.round(v * 100)}%`}
        />
        <MetricPanel
          title="Entities extracted"
          unit="per note, mean"
          results={run.results}
          value={(r) => r.mean_entities}
          format={(v) => v.toFixed(1)}
        />
        <MetricPanel
          title="ICD-10 suggestions"
          unit="per note, mean"
          results={run.results}
          value={(r) => r.mean_icd_codes}
          format={(v) => v.toFixed(1)}
        />
        <MetricPanel
          title="Memory growth"
          unit="MB RSS, approx."
          hint="Lower is better · mostly one-time model loading; ~0 if already loaded"
          results={run.results}
          value={(r) => r.rss_delta_mb}
          format={(v) => v.toFixed(0)}
        />
      </div>

      <section className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400 dark:border-slate-800 dark:text-slate-500">
              <th className="px-5 py-3 font-medium">Framework</th>
              <th className="px-5 py-3 font-medium">Model</th>
              <th className="px-5 py-3 text-right font-medium">Mean ms</th>
              <th className="px-5 py-3 text-right font-medium">p50 ms</th>
              <th className="px-5 py-3 text-right font-medium">p95 ms</th>
              <th className="px-5 py-3 text-right font-medium">Confidence</th>
              <th className="px-5 py-3 text-right font-medium">Entities</th>
              <th className="px-5 py-3 text-right font-medium">ICD</th>
              <th className="px-5 py-3 text-right font-medium">RSS MB</th>
            </tr>
          </thead>
          <tbody>
            {ordered(run.results).map((r) => {
              const fw = FRAMEWORKS.find((f) => f.value === r.framework)!;
              return (
                <tr key={r.framework} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                  <td className="px-5 py-3">
                    <span className="flex items-center gap-2 font-medium text-slate-800 dark:text-slate-200">
                      <span className={`h-2 w-2 rounded-full ${fw.dot}`} aria-hidden />
                      {fw.label}
                      {r.status === "placeholder" && (
                        <span className="rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-700 ring-1 ring-inset ring-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-900">
                          placeholder
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="max-w-56 truncate px-5 py-3 font-mono text-xs text-slate-500 dark:text-slate-400" title={r.model_name}>
                    {r.model_name}
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums">{r.mean_ms.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{r.p50_ms.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{r.p95_ms.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums">
                    {Math.round(r.mean_confidence * 100)}%
                  </td>
                  <td className="px-5 py-3 text-right tabular-nums">{r.mean_entities.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums">{r.mean_icd_codes.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums">
                    {r.rss_mb === null ? "—" : r.rss_mb.toFixed(0)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <p className="text-xs leading-relaxed text-slate-400 dark:text-slate-500">
        Benchmarked over {run.notes_count} synthetic sample notes × {run.iterations} iterations
        on the API serving path (CPU). Entity/ICD counts and confidence measure model behavior,
        not correctness — a higher count is not automatically better. Memory is process-level
        RSS and approximate.
      </p>
    </div>
  );
}

export default function BenchmarksPage() {
  const [runs, setRuns] = useState<BenchmarkRun[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    getBenchmarks()
      .then((data) => {
        setRuns(data);
        setSelectedId((current) => current ?? data[0]?.id ?? null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load benchmarks"));
  }, []);

  useEffect(load, [load]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const run = await runBenchmark();
      setRuns((current) => [run, ...(current ?? [])]);
      setSelectedId(run.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Benchmark run failed");
    } finally {
      setRunning(false);
    }
  }

  const selected = runs?.find((r) => r.id === selectedId) ?? runs?.[0] ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Framework benchmarks
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
            PyTorch, TensorFlow, and JAX pipelines compared on the same notes through the same
            API path. Results are stored, so runs are comparable over time.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {runs && runs.length > 1 && (
            <select
              value={selected?.id ?? ""}
              onChange={(e) => setSelectedId(e.target.value)}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 shadow-sm focus:border-teal-500 focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              aria-label="Select benchmark run"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {formatDate(r.created_at)}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {running && (
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
                <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" />
              </svg>
            )}
            {running ? "Benchmarking…" : "Run benchmark"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          <p className="font-medium">Benchmark error</p>
          <p className="mt-0.5 text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {!error && runs === null && (
        <div className="animate-pulse space-y-4">
          <div className="h-40 rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900" />
          <div className="h-40 rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900" />
        </div>
      )}

      {runs !== null && runs.length === 0 && (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-14 text-center dark:border-slate-800">
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">No benchmark runs yet</p>
          <p className="mt-1 text-sm text-slate-400 dark:text-slate-500">
            Press <span className="font-medium text-slate-500 dark:text-slate-400">Run benchmark</span> to compare
            the three frameworks. The first run loads every model, so it takes a minute.
          </p>
        </div>
      )}

      {selected && <RunDetail run={selected} />}
    </div>
  );
}
