import type { Metadata } from "next";
import { Nav } from "@/components/Nav";
import { ThemeToggle } from "@/components/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedExtract — Clinical Note Intelligence",
  description:
    "Extract conditions, symptoms, medications, procedures, and ICD-10 suggestions from clinical notes.",
};

// Runs before paint: stored preference wins, otherwise system preference.
const THEME_INIT = `(function(){try{var t=localStorage.getItem("theme");var d=t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;if(d)document.documentElement.classList.add("dark");}catch(e){}})();`;

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 text-white shadow-sm">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-5 w-5"
          aria-hidden
        >
          <path d="M3 12h4l2.5-6 4.5 12 2.5-6H21" />
        </svg>
      </div>
      <div className="leading-tight">
        <span className="block text-[17px] font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          MedExtract
        </span>
        <span className="block text-xs text-slate-500 dark:text-slate-400">
          Clinical note intelligence
        </span>
      </div>
    </div>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="flex min-h-screen flex-col bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
        <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-900/85">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
            <Logo />
            <div className="flex items-center gap-3">
              <Nav />
              <span className="hidden rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 sm:inline dark:border-amber-500/30 dark:bg-amber-950/40 dark:text-amber-300">
                Demo · synthetic data only
              </span>
              <ThemeToggle />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>

        <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto max-w-6xl px-6 py-5 text-xs leading-relaxed text-slate-400 dark:text-slate-500">
            MedExtract is a research scaffold — not a medical device and not medical advice.
            Extractions and ICD-10 suggestions are heuristic and require review by a qualified
            clinician. Never enter real patient data.
          </div>
        </footer>
      </body>
    </html>
  );
}
