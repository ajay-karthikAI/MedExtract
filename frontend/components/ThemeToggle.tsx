"use client";

// Icon visibility is pure CSS (dark: variants), so no state/hydration concerns:
// the moon shows in light mode, the sun in dark mode.
export function ThemeToggle() {
  function toggle() {
    const dark = document.documentElement.classList.toggle("dark");
    try {
      localStorage.setItem("theme", dark ? "dark" : "light");
    } catch {
      /* private browsing */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Toggle dark mode"
      className="inline-flex h-10 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 text-sm font-medium text-slate-200 transition hover:bg-white/[0.06]"
    >
      <span className="h-2 w-2 rounded-full bg-blue-500 shadow-[0_0_16px_rgba(59,130,246,0.9)]" />
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-[18px] w-[18px] dark:hidden"
        aria-hidden
      >
        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
      </svg>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="hidden h-[18px] w-[18px] dark:block"
        aria-hidden
      >
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
      <span className="hidden sm:inline">Dark</span>
    </button>
  );
}
