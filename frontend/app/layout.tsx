import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedExtract — Clinical Note Intelligence",
  description:
    "Extract conditions, symptoms, medications, procedures, and ICD-10 suggestions from clinical notes.",
};

const THEME_INIT = `(function(){try{if(localStorage.getItem("theme")==="dark"){document.documentElement.classList.add("dark");}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
