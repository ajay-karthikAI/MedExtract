"use client";

import { useMemo, useState } from "react";
import {
  AnnotatedDocument,
  EmptyResults,
  FindingsRail,
  flattenEntityRows,
} from "@/components/AnalysisResults";
import { NoteForm } from "@/components/NoteForm";
import { analyzeFile, analyzeNote } from "@/lib/api";
import type { AnalyzeInput, AnalyzeResponse, Framework } from "@/lib/types";

const DEFAULT_NOTE = `Chief Complaint: Chest pain.

History of Present Illness:
64-year-old male with history of hypertension and type 2 diabetes
presents with sudden onset of chest pain radiating to the left arm
and jaw for the past 45 minutes. Associated with diaphoresis,
nausea, and shortness of breath.

Past Medical History: Hypertension, Type 2 Diabetes Mellitus
Medications: Metformin 1000mg BID, Lisinopril 20mg daily
Allergies: No known drug allergies

Physical Exam:
BP 168/102, HR 110, RR 22, SpO2 95% on room air
Diaphoretic, in mild distress
Cardiac: Tachycardic, regular rhythm
Lungs: Clear bilaterally

Assessment:
Concern for acute coronary syndrome. EKG shows ST elevation in
leads II, III, aVF.`;

export default function AnalyzePage() {
  const [note, setNote] = useState(DEFAULT_NOTE);
  const [analyzedNote, setAnalyzedNote] = useState("");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [framework, setFramework] = useState<Framework>("pytorch");
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rows = useMemo(() => (result ? flattenEntityRows(result.entities) : []), [result]);

  async function handleAnalyze(input: AnalyzeInput, fw: Framework) {
    setLoading(true);
    setError(null);
    setFramework(fw);
    setActiveId(null);
    try {
      const response =
        input.kind === "file"
          ? await analyzeFile(input.file, fw)
          : await analyzeNote(input.note, fw);
      setResult(response);
      setAnalyzedNote(input.kind === "file" ? `Uploaded document: ${input.file.name}` : input.note);
      setEditing(input.kind === "file");
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="border border-[var(--alert)] bg-[var(--alert-bg)] px-4 py-3 text-[12px] text-[var(--alert)]">
          <span className="font-semibold">Analysis failed: </span>
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_minmax(380px,0.9fr)]">
        {result && !editing ? (
          <AnnotatedDocument
            note={analyzedNote}
            rows={rows}
            activeId={activeId}
            onActiveIdChange={setActiveId}
            onEdit={() => setEditing(true)}
          />
        ) : (
          <NoteForm note={note} onNoteChange={setNote} onSubmit={handleAnalyze} loading={loading} />
        )}

        {result ? (
          <FindingsRail result={result} activeId={activeId} onActiveIdChange={setActiveId} />
        ) : (
          <EmptyResults />
        )}
      </div>

      <p className="text-[11px] leading-5 text-[var(--ink-soft)]">
        Automated extraction for informational purposes only. Synthetic notes only.
      </p>
    </div>
  );
}
