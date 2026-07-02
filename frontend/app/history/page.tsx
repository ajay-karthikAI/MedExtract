"use client";

import { useCallback, useEffect, useState } from "react";
import { CategoryGrid, IcdList, SummaryCard } from "@/components/AnalysisResults";
import { getHistory } from "@/lib/api";
import { CATEGORIES, entityCount, formatDate, frameworkLabel, percent } from "@/lib/display";
import type { HistoryItem } from "@/lib/types";

function HistoryCard({ item }: { item: HistoryItem }) {
  const [open, setOpen] = useState(false);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-4 px-6 py-4 text-left"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="text-sm font-medium text-slate-700">
              {formatDate(item.created_at)}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
              {frameworkLabel(item.framework)}
            </span>
            {item.note_title && (
              <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700 ring-1 ring-inset ring-teal-200">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-3 w-3"
                  aria-hidden
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6" />
                </svg>
                {item.note_title}
              </span>
            )}
            <span className="hidden font-mono text-xs text-slate-400 sm:inline">
              {item.model_used}
            </span>
          </div>
          <p className="mt-1 truncate text-sm text-slate-500">{item.note_preview}</p>
        </div>

        <div className="hidden shrink-0 items-center gap-3 md:flex">
          {CATEGORIES.map(({ key, dot }) => (
            <span key={key} className="flex items-center gap-1.5 text-xs tabular-nums text-slate-500">
              <span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden />
              {item.entities[key].length}
            </span>
          ))}
          <span className="w-12 text-right text-xs tabular-nums text-slate-400">
            {percent(item.confidence)}
          </span>
        </div>

        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div className="space-y-4 border-t border-slate-100 px-6 py-5">
          <div className="text-xs text-slate-400 sm:hidden">
            <span className="font-mono">{item.model_used}</span> ·{" "}
            {entityCount(item.entities)} entities · {percent(item.confidence)} confidence
          </div>
          <SummaryCard summary={item.patient_summary} />
          <CategoryGrid groups={item.entities} />
          <IcdList codes={item.icd_codes} />
        </div>
      )}
    </article>
  );
}

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-slate-200 bg-white px-6 py-5">
      <div className="h-3.5 w-56 rounded bg-slate-100" />
      <div className="mt-2.5 h-3 w-full max-w-xl rounded bg-slate-100" />
    </div>
  );
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    setItems(null);
    getHistory()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load history"));
  }, []);

  useEffect(load, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
            Analysis history
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Previous analyses, newest first{items ? ` · ${items.length} shown` : ""}.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          <p className="font-medium">Couldn’t load history</p>
          <p className="mt-0.5 text-red-600">{error}</p>
        </div>
      )}

      {!error && items === null && (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {items !== null && items.length === 0 && (
        <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-14 text-center">
          <p className="text-sm font-medium text-slate-500">No analyses yet</p>
          <p className="mt-1 text-sm text-slate-400">
            Run your first analysis from the Analyze tab — results are saved here automatically.
          </p>
        </div>
      )}

      {items !== null && items.length > 0 && (
        <div className="space-y-3">
          {items.map((item) => (
            <HistoryCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
