"use client";

import { useCallback, useEffect, useState } from "react";
import { CategoryGrid, IcdList, SummaryCard } from "@/components/AnalysisResults";
import { getHistory } from "@/lib/api";
import { entityCount, formatDate, frameworkLabel } from "@/lib/display";
import type { HistoryItem } from "@/lib/types";

function HistoryRow({ item }: { item: HistoryItem }) {
  const [open, setOpen] = useState(false);

  return (
    <article className="border-b border-[var(--rule)] last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="focus-ring grid min-h-12 w-full gap-3 px-3 py-2 text-left text-[12px] hover:bg-[var(--paper-muted)] md:grid-cols-[170px_110px_minmax(0,1fr)_110px_80px]"
        aria-expanded={open}
      >
        <span>{formatDate(item.created_at)}</span>
        <span className="text-[var(--ink-muted)]">{frameworkLabel(item.framework)}</span>
        <span className="truncate" title={item.note_preview}>{item.note_preview}</span>
        <span className="text-right text-[var(--ink-muted)]">{entityCount(item.entities)} entities</span>
        <span className="text-right">{item.confidence.toFixed(2)}</span>
      </button>

      {open && (
        <div className="grid gap-3 border-t border-[var(--rule)] bg-[var(--paper)] p-3 lg:grid-cols-[1fr_1fr]">
          <div className="space-y-3">
            <SummaryCard summary={item.patient_summary} />
            <CategoryGrid groups={item.entities} />
          </div>
          <IcdList codes={item.icd_codes} />
        </div>
      )}
    </article>
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
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-4 border-b border-[var(--rule)] pb-3">
        <div>
          <h1 className="text-[18px] font-semibold">Analysis history</h1>
          <p className="mt-1 text-[12px] text-[var(--ink-muted)]">
            Previous synthetic-note analyses, newest first{items ? ` · ${items.length} shown` : ""}.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="focus-ring border border-[var(--rule)] px-3 py-1.5 text-[11px] font-semibold text-[var(--ink-muted)] hover:text-[var(--ink)]"
        >
          REFRESH
        </button>
      </header>

      {error && (
        <div className="border border-[var(--alert)] bg-[var(--alert-bg)] px-4 py-3 text-[12px] text-[var(--alert)]">
          {error}
        </div>
      )}

      <section className="chart-paper overflow-hidden">
        <div className="grid gap-3 border-b border-[var(--rule)] bg-[var(--paper-muted)] px-3 py-2 text-[11px] font-bold uppercase tracking-[0.08em] text-[var(--ink-muted)] md:grid-cols-[170px_110px_minmax(0,1fr)_110px_80px]">
          <span>Date</span>
          <span>Framework</span>
          <span>Preview</span>
          <span className="text-right">Entities</span>
          <span className="text-right">Conf</span>
        </div>
        {items === null && !error && <p className="p-4 text-[12px] text-[var(--ink-muted)]">Loading history...</p>}
        {items !== null && items.length === 0 && <p className="p-4 text-[12px] text-[var(--ink-muted)]">No analyses yet.</p>}
        {items?.map((item) => <HistoryRow key={item.id} item={item} />)}
      </section>
    </div>
  );
}
