"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";

const PRIMARY_LINKS = [
  { href: "/", label: "Analyze", icon: "pulse" },
  { href: "/history", label: "History", icon: "file" },
  { href: "/benchmarks", label: "Benchmarks", icon: "chart" },
] as const;

const SECONDARY_LINKS = [
  { label: "Knowledge Base", icon: "archive" },
  { label: "Models", icon: "network" },
  { label: "Settings", icon: "gear" },
] as const;

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

  if (name === "pulse") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M3 12h4l2.4-6 4.4 12 2.4-6H21" />
      </svg>
    );
  }
  if (name === "file") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z" />
        <path d="M14 2v5h5M9 13h6M9 17h4" />
      </svg>
    );
  }
  if (name === "chart") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M4 19V5M8 19v-7M12 19V8M16 19v-4M20 19V4" />
      </svg>
    );
  }
  if (name === "archive") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M4 7h16M5 7l1 13h12l1-13M9 11h6" />
        <path d="M8 3h8l1 4H7z" />
      </svg>
    );
  }
  if (name === "network") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M12 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM5 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM19 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
        <path d="m10 7-3.5 9M14 7l3.5 9M8 19h8" />
      </svg>
    );
  }
  if (name === "gear") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" />
        <path d="m19.4 15 .6 2-2 3.4-2.1-.5a8 8 0 0 1-1.8 1l-.6 2.1h-4l-.6-2.1a8 8 0 0 1-1.8-1l-2.1.5L3 17l.6-2a8 8 0 0 1 0-2l-.6-2L5 7.6l2.1.5a8 8 0 0 1 1.8-1L9.5 5h4l.6 2.1a8 8 0 0 1 1.8 1l2.1-.5L20 11l-.6 2a8 8 0 0 1 0 2Z" />
      </svg>
    );
  }
  if (name === "zap") {
    return (
      <svg viewBox="0 0 24 24" {...common}>
        <path d="m13 2-8 12h6l-1 8 9-13h-6z" />
      </svg>
    );
  }
  return null;
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-blue-500/20 bg-blue-500/10 text-blue-400 shadow-[0_0_32px_rgba(37,99,235,0.25)]">
        <Icon name="pulse" className="h-6 w-6" />
      </div>
      <div className="leading-tight">
        <span className="block text-lg font-semibold tracking-tight text-white">MedExtract</span>
        <span className="block text-xs text-slate-500">Clinical note intelligence</span>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#03070c] text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[280px] border-r border-white/10 bg-[#070d13]/95 px-4 py-6 shadow-[24px_0_80px_rgba(0,0,0,0.35)] lg:flex lg:flex-col">
        <Brand />

        <nav className="mt-10 space-y-1">
          {PRIMARY_LINKS.map(({ href, label, icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex h-12 items-center gap-4 rounded-lg px-4 text-sm font-medium transition ${
                  active
                    ? "border border-blue-500/20 bg-blue-500/10 text-blue-400"
                    : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-100"
                }`}
              >
                <Icon name={icon} />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="my-7 h-px bg-white/10" />

        <nav className="space-y-1">
          {SECONDARY_LINKS.map(({ label, icon }) => (
            <button
              key={label}
              type="button"
              className="flex h-12 w-full items-center gap-4 rounded-lg px-4 text-left text-sm font-medium text-slate-400 transition hover:bg-white/[0.04] hover:text-slate-100"
            >
              <Icon name={icon} />
              {label}
            </button>
          ))}
        </nav>

        <div className="mt-auto space-y-6">
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <div className="text-xs text-slate-400">Analyses this month</div>
            <div className="mt-3 flex items-end justify-between">
              <span className="text-xl font-semibold text-white">32 / 500</span>
              <span className="text-xs text-slate-500">6%</span>
            </div>
            <div className="mt-4 h-2 rounded-full bg-slate-800">
              <div className="h-full w-[6%] rounded-full bg-blue-500" />
            </div>
            <button
              type="button"
              className="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-500/10 text-sm font-medium text-blue-400 transition hover:bg-blue-500/15"
            >
              <Icon name="zap" className="h-4 w-4" />
              Upgrade plan
            </button>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-sm font-semibold text-white">
              AK
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-white">Ajay Karthikeyan</div>
              <div className="text-xs text-slate-500">Pro Plan</div>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-[280px]">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-[#05090f]/90 backdrop-blur-xl">
          <div className="flex h-[78px] items-center justify-between gap-4 px-4 sm:px-8">
            <div className="flex items-center gap-2 lg:hidden">
              <Brand />
            </div>
            <nav className="hidden h-full items-center gap-6 sm:flex">
              {PRIMARY_LINKS.map(({ href, label }) => {
                const active = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`relative flex h-full items-center px-4 text-sm font-medium transition ${
                      active ? "text-white" : "text-slate-400 hover:text-slate-100"
                    }`}
                  >
                    {label}
                    {active && (
                      <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-blue-500 shadow-[0_0_24px_rgba(59,130,246,0.9)]" />
                    )}
                  </Link>
                );
              })}
            </nav>
            <div className="ml-auto flex items-center gap-3">
              <ThemeToggle />
              <Link
                href="/"
                className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-5 text-sm font-semibold text-white shadow-[0_12px_32px_rgba(37,99,235,0.35)] transition hover:bg-blue-500"
              >
                New analysis
              </Link>
            </div>
          </div>
        </header>

        <main className="min-h-[calc(100vh-78px)] px-4 py-5 sm:px-8">{children}</main>
      </div>
    </div>
  );
}
