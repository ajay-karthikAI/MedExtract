"use client";

import { useState } from "react";
import { AnalysisResults } from "@/components/AnalysisResults";
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Analyze a clinical note
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          Paste a free-text note or upload a PDF to extract conditions, symptoms, medications,
          and procedures, with suggested ICD-10 codes and a patient-friendly summary. Every
          analysis is saved to your history.
        </p>
      </div>

      <NoteForm onSubmit={handleAnalyze} loading={loading} />

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            className="mt-0.5 h-4 w-4 shrink-0"
            aria-hidden
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          <div>
            <p className="font-medium">Analysis failed</p>
            <p className="mt-0.5 text-red-600 dark:text-red-400">{error}</p>
          </div>
        </div>
      )}

      {result ? (
        <AnalysisResults result={result} framework={framework} />
      ) : (
        !loading &&
        !error && (
          <div className="rounded-2xl border-2 border-dashed border-slate-200 px-6 py-14 text-center dark:border-slate-800">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600"
              aria-hidden
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6M9 13h6M9 17h6" />
            </svg>
            <p className="mt-3 text-sm font-medium text-slate-500 dark:text-slate-400">No analysis yet</p>
            <p className="mt-1 text-sm text-slate-400 dark:text-slate-500">
              Load a sample note above or paste your own, then press{" "}
              <span className="font-medium text-slate-500 dark:text-slate-400">Analyze note</span>.
            </p>
          </div>
        )
      )}
    </div>
  );
}
