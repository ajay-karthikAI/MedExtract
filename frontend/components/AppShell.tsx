"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { getModels } from "@/lib/api";
import type { ModelInfo } from "@/lib/types";

const LINKS = [
  { href: "/", label: "Analyze" },
  { href: "/history", label: "History" },
  { href: "/benchmarks", label: "Benchmarks" },
  { href: "/models", label: "Models" },
] as const;

function ModelStatus() {
  const [models, setModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    getModels().then(setModels).catch(() => setModels([]));
  }, []);

  const label = useMemo(() => {
    if (models.length === 0) return "models pending";
    const available = models.filter((model) => model.status === "available").length;
    return `${available}/${models.length} models available`;
  }, [models]);

  return (
    <div className="hidden items-center gap-2 border-l border-[var(--rule)] pl-4 text-[11px] text-[var(--ink-muted)] md:flex">
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--medication)]" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="chart-shell">
      <header className="chart-topbar sticky top-0 z-40">
        <div className="mx-auto flex h-14 max-w-[1500px] items-center gap-5 px-4 sm:px-6">
          <Link href="/" className="focus-ring text-[15px] font-semibold tracking-[-0.01em]">
            MedExtract
          </Link>

          <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto text-[12px]" aria-label="Primary">
            {LINKS.map((link) => {
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`focus-ring whitespace-nowrap border-b px-3 py-4 transition ${
                    active
                      ? "border-[var(--ink)] text-[var(--ink)]"
                      : "border-transparent text-[var(--ink-muted)] hover:text-[var(--ink)]"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <ModelStatus />
          <ThemeToggle />
        </div>
      </header>

      <main className="mx-auto min-h-[calc(100vh-56px)] max-w-[1500px] px-4 py-4 sm:px-6">
        {children}
      </main>
    </div>
  );
}
