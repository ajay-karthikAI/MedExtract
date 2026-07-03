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

function Icon({ name, className = "h-4 w-4" }: { name: string; className?: string }) {
  const common = {
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    "aria-hidden": true,
  };
  if (name === "upload") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="m17 8-5-5-5 5M12 3v12" />
      </svg>
    );
  }
  if (name === "chevron") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="m6 9 6 6 6-6" />
      </svg>
    );
  }
  if (name === "spark") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M12 3v4M12 17v4M4.2 4.2l2.8 2.8M17 17l2.8 2.8M3 12h4M17 12h4M4.2 19.8 7 17M17 7l2.8-2.8" />
      </svg>
    );
  }
  return null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

interface NoteFormProps {
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
    <section className="rounded-lg border border-white/10 bg-[#0b1119]/90 p-5">
      <div className="mb-4 text-sm font-semibold text-white">Models</div>
      <div className="grid gap-3 sm:grid-cols-3">
        {FRAMEWORKS.map((fw) => {
          const active = framework === fw.value;
          const model = models.find((m) => m.framework === fw.value);
          return (
            <button
              key={fw.value}
              type="button"
              onClick={() => setFramework(fw.value)}
              className={`rounded-lg border p-4 text-left transition ${
                active
                  ? "border-blue-500/40 bg-blue-500/10"
                  : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-white">{fw.label}</span>
                <span
                  className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${
                    model?.status === "available"
                      ? "bg-emerald-500/10 text-emerald-300"
                      : "bg-slate-700/70 text-slate-300"
                  }`}
                >
                  {model?.status === "available" ? "Active" : "Ready"}
                </span>
              </div>
              <p className="mt-3 min-h-8 text-xs leading-relaxed text-slate-500">
                {model?.model_name ?? "Rules + dictionary layer"}
              </p>
              <div className="mt-4 h-2 w-24 rounded-full bg-slate-800">
                <div className={`h-full rounded-full ${active ? "w-16 bg-blue-500" : "w-10 bg-slate-600"}`} />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export function NoteForm({ onSubmit, loading }: NoteFormProps) {
  const [note, setNote] = useState(SAMPLES[0].text);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [framework, setFramework] = useState<Framework>("pytorch");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getModels().then(setModels).catch(() => {});
  }, []);

  const lineNumbers = useMemo(() => {
    const count = Math.max(note.split("\n").length, 16);
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
    <div className="space-y-2">
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
        className={`rounded-lg border bg-[#0b1119]/90 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] transition ${
          dragging ? "border-blue-400/70 ring-2 ring-blue-500/20" : "border-white/10"
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

        <div className="mb-4 flex items-center justify-between gap-3">
          <label htmlFor="note" className="text-base font-semibold text-white">
            Clinical note
          </label>
          {!file && (
            <label className="relative">
              <span className="sr-only">Sample note</span>
              <select
                value={SAMPLES.find((sample) => sample.text === note)?.label ?? ""}
                onChange={(event) => {
                  const sample = SAMPLES.find((item) => item.label === event.target.value);
                  if (sample) setNote(sample.text);
                }}
                className="h-9 appearance-none rounded-lg border border-white/10 bg-white/[0.04] pl-3 pr-9 text-sm font-medium text-slate-100 outline-none transition hover:bg-white/[0.07] focus:border-blue-500"
              >
                <option value="" className="bg-slate-950">Samples</option>
                {SAMPLES.map((sample) => (
                  <option key={sample.label} value={sample.label} className="bg-slate-950">
                    {sample.label}
                  </option>
                ))}
              </select>
              <Icon name="chevron" className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            </label>
          )}
        </div>

        <div className="min-h-[430px] overflow-hidden rounded-lg border border-white/10 bg-[#070b11]">
          {file ? (
            <div className="flex h-[430px] items-center justify-center p-6">
              <div className="w-full max-w-md rounded-lg border border-blue-500/20 bg-blue-500/10 p-5">
                <div className="flex items-center gap-4">
                  <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300">
                    <Icon name="upload" className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white">{file.name}</p>
                    <p className="text-xs text-slate-400">{formatBytes(file.size)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFile(null)}
                    className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-[48px_1fr]">
              <div className="select-none border-r border-white/10 bg-white/[0.02] px-4 py-4 text-right font-mono text-[13px] leading-7 text-slate-600">
                {lineNumbers.map((line) => (
                  <div key={line}>{line}</div>
                ))}
              </div>
              <textarea
                id="note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={MAX_CHARS}
                spellCheck={false}
                className="min-h-[430px] w-full resize-y border-0 bg-transparent px-5 py-4 font-mono text-[13px] leading-7 text-slate-100 outline-none placeholder:text-slate-600"
              />
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          className="mt-4 flex w-full items-center justify-between rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3 text-left transition hover:bg-white/[0.04]"
        >
          <span className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-slate-400">
              <Icon name="upload" />
            </span>
            <span>
              <span className="block text-sm font-medium text-slate-200">Upload PDF or TXT</span>
              <span className="block text-xs text-slate-500">Drag and drop a file, or click to browse</span>
            </span>
          </span>
          <span className="hidden text-xs text-slate-500 sm:inline">TXT, PDF up to 25MB</span>
        </button>

        {fileError && <p className="mt-2 text-sm text-red-300">{fileError}</p>}

        <button
          type="submit"
          disabled={!canSubmit}
          className="mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-semibold text-white shadow-[0_18px_40px_rgba(37,99,235,0.35)] transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading ? (
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
              <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" />
            </svg>
          ) : (
            <Icon name="spark" />
          )}
          {loading ? "Analyzing..." : file ? "Analyze document" : "Analyze note"}
        </button>
      </form>

      <FrameworkSelector framework={framework} setFramework={setFramework} models={models} />
    </div>
  );
}
