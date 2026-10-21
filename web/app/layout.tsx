import type { Metadata } from "next";
import { Suspense } from "react";

import Footer from "@/components/Footer";
import Header from "@/components/Header";

import "./globals.css";

export const metadata: Metadata = {
  title: "FilingGuard",
  description: "Before/after results for a hard-gated verifier on LLM answers about SEC 10-K filings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <Suspense>
          <Header />
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        </Suspense>
        <Footer />
      </body>
    </html>
  );
}
