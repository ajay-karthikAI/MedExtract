"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getModels } from "@/lib/api";
import { FRAMEWORKS } from "@/lib/display";
import type { AnalyzeInput, Framework, ModelInfo } from "@/lib/types";

const SAMPLES: { label: string; text: string }[] = [
  {
    label: "ACS",
    text: `Chief Complaint: Chest pain.

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
leads II, III, aVF.`,
  },
  {
    label: "UTI",
    text: `Chief Complaint: Burning with urination.

HPI:
27-year-old reporting two days of dysuria and urinary frequency.
No fever, no back pain, no nausea.

PMH: None significant.
Medications: None.

Plan:
Urinalysis in office consistent with urinary tract infection.
Start nitrofurantoin 100mg BID for five days. Push fluids.`,
  },
  {
    label: "Migraine",
    text: `Chief Complaint: Recurrent headaches.

HPI:
41-year-old with history of migraine reporting increased headache
frequency over the past month, now two to three episodes weekly,
with nausea and light sensitivity. Sumatriptan provides partial relief.

PMH: Migraine, anxiety.
Medications: Sumatriptan 50mg PRN, ibuprofen PRN.

Plan:
Discussed headache diary and trigger avoidance. MRI if red-flag
symptoms develop.`,
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
  note: string;
  onNoteChange: (note: string) => void;
  onSubmit: (input: AnalyzeInput, framework: Framework) => void;
  loading: boolean;
}

function FrameworkSelector({
  framework,
  setFramework,
  models,
}: {
  framework: Framework;
  setFramework: (framework: Framework) => void;
  models: ModelInfo[];
}) {
  return (
    <div className="border-t border-[var(--rule)] px-4 py-3">
      <p className="chart-label mb-2">Model route</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {FRAMEWORKS.map((fw) => {
          const active = framework === fw.value;
          const model = models.find((m) => m.framework === fw.value);
          return (
            <button
              key={fw.value}
              type="button"
              onClick={() => setFramework(fw.value)}
              className={`focus-ring min-h-12 border px-3 py-2 text-left text-[11px] transition ${
                active
                  ? "border-[var(--ink)] bg-[var(--paper-muted)]"
                  : "border-[var(--rule)] hover:border-[var(--rule-strong)]"
              }`}
            >
              <span className="block font-semibold">{fw.label}</span>
              <span className="mt-1 block truncate text-[var(--ink-muted)]">
                {model?.status === "available" ? "available" : "placeholder"} · {model?.model_name ?? "rule fallback"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function NoteForm({ note, onNoteChange, onSubmit, loading }: NoteFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [framework, setFramework] = useState<Framework>("pytorch");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getModels().then(setModels).catch(() => setModels([]));
  }, []);

  const lineNumbers = useMemo(() => {
    const count = Math.max(note.split("\n").length, 20);
    return Array.from({ length: count }, (_, index) => index + 1);
  }, [note]);

  const canSubmit =
    !loading && (file !== null || (note.trim().length > 0 && note.length <= MAX_CHARS));

  function acceptFile(candidate: File | undefined) {
    if (!candidate) return;
    const ext = "." + (candidate.name.split(".").pop() ?? "").toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setFileError(`"${candidate.name}" is not supported.`);
      return;
    }
    setFileError(null);
    setFile(candidate);
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSubmit) return;
        onSubmit(file ? { kind: "file", file } : { kind: "text", note: note.trim() }, framework);
      }}
      className="chart-paper overflow-hidden"
    >
      <input
        ref={fileInput}
        type="file"
        accept={ACCEPTED.join(",")}
        className="hidden"
        onChange={(event) => {
          acceptFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />

      <div className="flex items-center justify-between border-b border-[var(--rule)] px-4 py-3">
        <div>
          <p className="chart-label">Clinical note</p>
          <p className="mt-1 text-[11px] text-[var(--ink-soft)]">editor · synthetic notes only</p>
        </div>
        <button
          type="submit"
          disabled={!canSubmit}
          className="focus-ring bg-[var(--primary)] px-4 py-2 text-[11px] font-semibold text-[var(--primary-ink)] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? "ANALYZING..." : file ? "ANALYZE DOCUMENT" : "ANALYZE NOTE"}
        </button>
      </div>

      {file ? (
        <div className="flex min-h-[520px] items-center justify-center p-6">
          <div className="w-full max-w-md border border-[var(--rule)] bg-[var(--paper-muted)] p-4">
            <p className="chart-label">Uploaded file</p>
            <p className="mt-2 truncate text-[13px] font-semibold">{file.name}</p>
            <p className="mt-1 text-[12px] text-[var(--ink-muted)]">{formatBytes(file.size)}</p>
            <button
              type="button"
              onClick={() => setFile(null)}
              className="focus-ring mt-4 border border-[var(--rule)] px-3 py-1.5 text-[11px] font-semibold text-[var(--ink-muted)]"
            >
              REMOVE FILE
            </button>
          </div>
        </div>
      ) : (
        <div className="grid min-h-[520px] grid-cols-[48px_1fr]">
          <div className="select-none border-r border-[var(--rule)] bg-[var(--paper-muted)] px-3 py-4 text-right text-[12px] leading-7 text-[var(--ink-soft)]">
            {lineNumbers.map((line) => (
              <div key={line}>{line}</div>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(event) => onNoteChange(event.target.value)}
            maxLength={MAX_CHARS}
            spellCheck={false}
            className="min-h-[520px] w-full resize-y border-0 bg-transparent px-5 py-4 text-[13px] leading-7 text-[var(--ink)] outline-none placeholder:text-[var(--ink-soft)]"
          />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3 border-t border-[var(--rule)] px-4 py-3 text-[11px] text-[var(--ink-muted)]">
        <span className="chart-label mr-1">Inputs</span>
        {SAMPLES.map((sample) => (
          <button
            key={sample.label}
            type="button"
            onClick={() => {
              setFile(null);
              onNoteChange(sample.text);
            }}
            className="focus-ring underline-offset-4 hover:underline"
          >
            {sample.label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          className="focus-ring underline-offset-4 hover:underline"
        >
          upload PDF/TXT
        </button>
        {fileError && <span className="text-[var(--alert)]">{fileError}</span>}
        <span className="ml-auto">{note.length.toLocaleString()} / {MAX_CHARS.toLocaleString()}</span>
      </div>

      <FrameworkSelector framework={framework} setFramework={setFramework} models={models} />
    </form>
  );
}
