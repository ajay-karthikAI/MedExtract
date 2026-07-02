import type { AnalyzeResponse, Framework, HistoryItem, ModelInfo } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function analyzeNote(note: string, framework: Framework): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/analyze-note", {
    method: "POST",
    body: JSON.stringify({ note, framework }),
  });
}

export async function analyzeFile(file: File, framework: Framework): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("framework", framework);
  // No Content-Type header — the browser sets the multipart boundary itself.
  const res = await fetch(`${API_URL}/analyze-file`, { method: "POST", body: form });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `API ${res.status}`);
  }
  return res.json() as Promise<AnalyzeResponse>;
}

export function getModels(): Promise<ModelInfo[]> {
  return request<ModelInfo[]>("/models");
}

export function getHistory(limit = 50): Promise<HistoryItem[]> {
  return request<HistoryItem[]>(`/history?limit=${limit}`);
}
