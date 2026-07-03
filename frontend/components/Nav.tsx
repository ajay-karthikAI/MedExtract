"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Analyze" },
  { href: "/history", label: "History" },
  { href: "/benchmarks", label: "Benchmarks" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-1 rounded-full bg-slate-100 p-1 dark:bg-slate-800">
      {LINKS.map(({ href, label }) => {
        const active = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
              active
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-950 dark:text-slate-100"
                : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
