"use client";

import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* private browsing */
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="focus-ring h-8 border border-[var(--rule)] bg-[var(--paper)] px-3 text-[11px] font-semibold text-[var(--ink-muted)] transition hover:text-[var(--ink)]"
      aria-label="Toggle dark mode"
    >
      {dark ? "DARK" : "LIGHT"}
    </button>
  );
}
