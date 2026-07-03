"use client";

import { useCallback, useEffect, useState } from "react";
import { getBenchmarks, runBenchmark } from "@/lib/api";
import { formatDate, FRAMEWORKS } from "@/lib/display";
import type { BenchmarkFrameworkResult, BenchmarkRun } from "@/lib/types";

const ordered = (results: BenchmarkFrameworkResult[]) =>
  FRAMEWORKS.map((framework) => results.find((result) => result.framework === framework.value)).filter(
    (result): result is BenchmarkFrameworkResult => result !== undefined,
  );

function Bar({ value, max, framework }: { value: number | null; max: number; framework: string }) {
  const token = framework === "pytorch" ? "procedure" : framework === "tensorflow" ? "symptom" : "medication";
  return (
    <span className="block h-2 border border-[var(--rule)]">
      {value !== null && max > 0 && (
        <span
          className="block h-full"
          style={{
            width: `${Math.max((value / max) * 100, 2)}%`,
            background: `var(--${token})`,
          }}
        />
      )}
    </span>
  );
}

function MetricBlock({
  label,
  results,
  value,
  format,
}: {
  label: string;
  results: BenchmarkFrameworkResult[];
  value: (result: BenchmarkFrameworkResult) => number | null;
  format: (value: number) => string;
}) {
  const rows = ordered(results).map((result) => ({ result, metric: value(result) }));
  const max = Math.max(...rows.map((row) => row.metric ?? 0), 0);

  return (
    <section className="chart-paper p-3">
      <h3 className="chart-label mb-3">{label}</h3>
      <div className="space-y-2">
        {rows.map(({ result, metric }) => (
          <div key={result.framework} className="grid grid-cols-[90px_minmax(0,1fr)_64px] items-center gap-3 text-[12px]">
            <span>{result.framework}</span>
            <Bar value={metric} max={max} framework={result.framework} />
            <span className="text-right">{metric === null ? "—" : format(metric)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function RunDetail({ run }: { run: BenchmarkRun }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricBlock label="Mean ms / note" results={run.results} value={(result) => result.mean_ms} format={(value) => value.toFixed(1)} />
        <MetricBlock label="Mean confidence" results={run.results} value={(result) => result.mean_confidence} format={(value) => value.toFixed(2)} />
        <MetricBlock label="Entities / note" results={run.results} value={(result) => result.mean_entities} format={(value) => value.toFixed(1)} />
        <MetricBlock label="ICD hints / note" results={run.results} value={(result) => result.mean_icd_codes} format={(value) => value.toFixed(1)} />
      </div>

      <section className="chart-paper overflow-x-auto">
        <table className="w-full text-left text-[12px]">
          <thead>
            <tr className="border-b border-[var(--rule)] bg-[var(--paper-muted)] text-[11px] uppercase tracking-[0.08em] text-[var(--ink-muted)]">
              <th className="px-3 py-2">Framework</th>
              <th className="px-3 py-2">Model</th>
              <th className="px-3 py-2 text-right">Mean</th>
              <th className="px-3 py-2 text-right">p50</th>
              <th className="px-3 py-2 text-right">p95</th>
              <th className="px-3 py-2 text-right">Conf</th>
              <th className="px-3 py-2 text-right">Entities</th>
              <th className="px-3 py-2 text-right">ICD</th>
              <th className="px-3 py-2 text-right">RSS</th>
            </tr>
          </thead>
          <tbody>
            {ordered(run.results).map((result) => (
              <tr key={result.framework} className="border-b border-[var(--rule)] last:border-b-0">
                <td className="px-3 py-2 font-semibold">{result.framework}</td>
                <td className="max-w-72 truncate px-3 py-2 text-[var(--ink-muted)]" title={result.model_name}>
                  {result.model_name} {result.status === "placeholder" ? "· placeholder" : ""}
                </td>
                <td className="px-3 py-2 text-right">{result.mean_ms.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{result.p50_ms.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{result.p95_ms.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{result.mean_confidence.toFixed(2)}</td>
                <td className="px-3 py-2 text-right">{result.mean_entities.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{result.mean_icd_codes.toFixed(1)}</td>
                <td className="px-3 py-2 text-right">{result.rss_mb === null ? "—" : result.rss_mb.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <p className="text-[11px] leading-5 text-[var(--ink-soft)]">
        {run.notes_count} synthetic notes × {run.iterations} iterations. Counts describe extraction behavior, not clinical correctness.
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

  const selected = runs?.find((run) => run.id === selectedId) ?? runs?.[0] ?? null;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-[var(--rule)] pb-3">
        <div>
          <h1 className="text-[18px] font-semibold">Framework benchmarks</h1>
          <p className="mt-1 text-[12px] text-[var(--ink-muted)]">Same notes, same API path, restrained instrumentation.</p>
        </div>
        <div className="flex items-center gap-2">
          {runs && runs.length > 1 && (
            <select
              value={selected?.id ?? ""}
              onChange={(event) => setSelectedId(event.target.value)}
              className="focus-ring h-8 border border-[var(--rule)] bg-[var(--paper)] px-2 text-[12px]"
            >
              {runs.map((run) => (
                <option key={run.id} value={run.id}>
                  {formatDate(run.created_at)}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="focus-ring bg-[var(--primary)] px-4 py-2 text-[11px] font-semibold text-[var(--primary-ink)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {running ? "RUNNING..." : "RUN BENCHMARK"}
          </button>
        </div>
      </header>

      {error && (
        <div className="border border-[var(--alert)] bg-[var(--alert-bg)] px-4 py-3 text-[12px] text-[var(--alert)]">
          {error}
        </div>
      )}
      {runs === null && !error && <p className="chart-paper p-4 text-[12px] text-[var(--ink-muted)]">Loading benchmarks...</p>}
      {runs !== null && runs.length === 0 && <p className="chart-paper p-4 text-[12px] text-[var(--ink-muted)]">No benchmark runs yet.</p>}
      {selected && <RunDetail run={selected} />}
    </div>
  );
}
