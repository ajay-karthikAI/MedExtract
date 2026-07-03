import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedExtract — Clinical Note Intelligence",
  description:
    "Extract conditions, symptoms, medications, procedures, and ICD-10 suggestions from clinical notes.",
};

const THEME_INIT = `(function(){try{document.documentElement.classList.add("dark");localStorage.setItem("theme","dark");}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-[#03070c] text-slate-100 antialiased">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
