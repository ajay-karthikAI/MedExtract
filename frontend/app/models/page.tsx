"use client";

import { useEffect, useState } from "react";
import { getModels } from "@/lib/api";
import type { ModelInfo } from "@/lib/types";

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModels()
      .then(setModels)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load models"));
  }, []);

  return (
    <div className="space-y-4">
      <header className="border-b border-[var(--rule)] pb-3">
        <h1 className="text-[18px] font-semibold">Models</h1>
        <p className="mt-1 text-[12px] text-[var(--ink-muted)]">
          Local framework routes and fallback status.
        </p>
      </header>

      {error && (
        <div className="border border-[var(--alert)] bg-[var(--alert-bg)] px-4 py-3 text-[12px] text-[var(--alert)]">
          {error}
        </div>
      )}

      <section className="chart-paper divide-y divide-[var(--rule)]">
        {(models ?? []).map((model) => (
          <div key={model.framework} className="grid gap-3 px-4 py-3 text-[12px] md:grid-cols-[140px_120px_minmax(0,1fr)]">
            <span className="font-semibold">{model.framework}</span>
            <span className={model.status === "available" ? "text-[var(--medication)]" : "text-[var(--ink-muted)]"}>
              {model.status}
            </span>
            <span className="min-w-0 truncate text-[var(--ink-muted)]" title={model.description}>
              {model.model_name} · {model.description}
            </span>
          </div>
        ))}
        {models === null && !error && <p className="p-4 text-[12px] text-[var(--ink-muted)]">Loading models...</p>}
      </section>
    </div>
  );
}
