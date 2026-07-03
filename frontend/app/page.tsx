"use client";

import { useState } from "react";
import { AnalysisResults, EmptyResults } from "@/components/AnalysisResults";
import { NoteForm } from "@/components/NoteForm";
import { analyzeFile, analyzeNote } from "@/lib/api";
import type { AnalyzeInput, AnalyzeResponse, Framework } from "@/lib/types";

export default function AnalyzePage() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [framework, setFramework] = useState<Framework>("pytorch");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze(input: AnalyzeInput, fw: Framework) {
    setLoading(true);
    setError(null);
    setFramework(fw);
    try {
      setResult(
        input.kind === "file"
          ? await analyzeFile(input.file, fw)
          : await analyzeNote(input.note, fw),
      );
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-[1380px] space-y-3">
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          <span className="font-semibold text-red-100">Analysis failed: </span>
          {error}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(520px,0.92fr)_minmax(560px,1.08fr)]">
        <NoteForm onSubmit={handleAnalyze} loading={loading} />
        {result ? <AnalysisResults result={result} framework={framework} /> : <EmptyResults />}
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-500">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4 text-blue-400"
          aria-hidden
        >
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
          <path d="m9 12 2 2 4-5" />
        </svg>
        <span>Research and informational use only. Synthetic notes only.</span>
      </div>
    </div>
  );
}
