"use client";

import { useEffect, useRef, useState } from "react";
import { getModels } from "@/lib/api";
import { FRAMEWORKS } from "@/lib/display";
import type { AnalyzeInput, Framework, ModelInfo } from "@/lib/types";

const SAMPLES: { label: string; text: string }[] = [
  {
    label: "Cardiology",
    text: `Chief complaint: Chest pain and shortness of breath.

HPI: 58-year-old presenting with intermittent chest pain for two days, worse with exertion, accompanied by shortness of breath and fatigue. Denies fever or cough.

PMH: Hypertension, type 2 diabetes, hyperlipidemia.

Medications: Lisinopril 10mg daily, metformin 500mg BID, atorvastatin 20mg nightly.

Plan: ECG and chest x-ray today. Troponin and CBC ordered. Cardiology referral if abnormal. Continue current medications.`,
  },
  {
    label: "UTI",
    text: `Chief complaint: Burning with urination.

HPI: 27-year-old reporting two days of dysuria and urinary frequency. No fever, no back pain, no nausea.

PMH: None significant.

Medications: None.

Plan: Urinalysis in office consistent with urinary tract infection. Start nitrofurantoin 100mg BID for five days. Push fluids. Return or call if fever or back pain develops.`,
  },
  {
    label: "Migraine",
    text: `Chief complaint: Recurrent headaches.

HPI: 41-year-old with history of migraine reporting increased headache frequency over the past month, now two to three episodes weekly, with nausea and light sensitivity. Sumatriptan provides partial relief. Denies fever, vision changes, or weakness.

PMH: Migraine, anxiety.

Medications: Sumatriptan 50mg PRN, ibuprofen PRN.

Plan: Discussed headache diary and trigger avoidance. Consider prophylactic therapy at next visit. MRI if red-flag symptoms develop.`,
  },
];

const MAX_CHARS = 50_000;
const ACCEPTED = [".pdf", ".txt"];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

interface NoteFormProps {
  onSubmit: (input: AnalyzeInput, framework: Framework) => void;
  loading: boolean;
}

export function NoteForm({ onSubmit, loading }: NoteFormProps) {
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [framework, setFramework] = useState<Framework>("pytorch");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getModels().then(setModels).catch(() => {});
  }, []);

  const selectedModel = models.find((m) => m.framework === framework);
  const canSubmit =
    !loading && (file !== null || (note.trim().length > 0 && note.length <= MAX_CHARS));

  function acceptFile(candidate: File | undefined) {
    if (!candidate) return;
    const ext = "." + (candidate.name.split(".").pop() ?? "").toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setFileError(`"${candidate.name}" is not supported — upload a PDF or TXT file.`);
      return;
    }
    setFileError(null);
    setFile(candidate);
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit(file ? { kind: "file", file } : { kind: "text", note: note.trim() }, framework);
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        acceptFile(e.dataTransfer.files?.[0]);
      }}
      className={`rounded-2xl border bg-white p-6 shadow-sm transition ${
        dragging ? "border-teal-400 ring-2 ring-teal-500/20" : "border-slate-200"
      }`}
    >
      <input
        ref={fileInput}
        type="file"
        accept={ACCEPTED.join(",")}
        className="hidden"
        onChange={(e) => {
          acceptFile(e.target.files?.[0]);
          e.target.value = "";
        }}
      />

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <label htmlFor="note" className="text-sm font-semibold text-slate-800">
          Clinical note
        </label>
        {!file && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Samples:</span>
            {SAMPLES.map((s) => (
              <button
                key={s.label}
                type="button"
                onClick={() => setNote(s.text)}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 font-medium text-slate-600 transition hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700"
              >
                {s.label}
              </button>
            ))}
            {note && (
              <button
                type="button"
                onClick={() => setNote("")}
                className="px-2 py-1 font-medium text-slate-400 transition hover:text-slate-600"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {file ? (
        <div className="flex items-center gap-4 rounded-xl border border-teal-200 bg-teal-50/50 px-5 py-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-teal-700 shadow-sm">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-5 w-5"
              aria-hidden
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <path d="M14 2v6h6" />
            </svg>
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-800">{file.name}</p>
            <p className="text-xs text-slate-500">
              {formatBytes(file.size)} · text will be extracted server-side
            </p>
          </div>
          <button
            type="button"
            onClick={() => setFile(null)}
            className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-500 transition hover:bg-white hover:text-slate-800"
          >
            Remove
          </button>
        </div>
      ) : (
        <>
          <textarea
            id="note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={11}
            maxLength={MAX_CHARS}
            placeholder="Paste a synthetic clinical note here — chief complaint, HPI, PMH, medications, plan… (never enter real patient data)"
            className="w-full resize-y rounded-xl border border-slate-200 bg-slate-50/50 p-4 text-sm leading-relaxed text-slate-800 placeholder:text-slate-400 focus:border-teal-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          />
          <div className="mt-1 flex items-center justify-between">
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-medium text-slate-500 transition hover:bg-slate-50 hover:text-teal-700"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-3.5 w-3.5"
                aria-hidden
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" />
              </svg>
              Upload a PDF or TXT — or drag it anywhere onto this card
            </button>
            <span className="text-[11px] tabular-nums text-slate-300">
              {note.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}
            </span>
          </div>
        </>
      )}

      {fileError && <p className="mt-2 text-sm text-red-600">{fileError}</p>}

      <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
            Inference framework
          </div>
          <div
            role="radiogroup"
            aria-label="Inference framework"
            className="inline-flex rounded-xl bg-slate-100 p-1"
          >
            {FRAMEWORKS.map((f) => (
              <button
                key={f.value}
                type="button"
                role="radio"
                aria-checked={framework === f.value}
                onClick={() => setFramework(f.value)}
                className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
                  framework === f.value
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          {selectedModel && (
            <div className="mt-1.5 flex items-center gap-1.5 text-xs text-slate-400">
              <span className="font-mono">{selectedModel.model_name}</span>
              {selectedModel.status === "placeholder" && (
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-medium text-slate-500">
                  placeholder
                </span>
              )}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500/40 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading && (
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
              <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                className="opacity-25"
              />
              <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" />
            </svg>
          )}
          {loading ? "Analyzing…" : file ? "Analyze document" : "Analyze note"}
        </button>
      </div>
    </form>
  );
}
