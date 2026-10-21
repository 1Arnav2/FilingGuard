"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { BASIS_LABEL, useBasis } from "@/lib/basis";
import type { Basis } from "@/lib/types";

const NAV = [
  { href: "/", label: "Scorecard" },
  { href: "/attack-types/", label: "By attack type" },
  { href: "/items/", label: "Items" },
  { href: "/method/", label: "Method" },
];

export default function Header() {
  const basis = useBasis();
  const pathname = usePathname();
  const router = useRouter();
  const withBasis = (href: string) => (basis === "as_scored" ? `${href}?basis=as_scored` : href);
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href.replace(/\/$/, "")));

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <Link href={withBasis("/")} className="text-lg font-semibold tracking-tight">
            FilingGuard
          </Link>
          <p className="text-sm text-slate-500">Hard-gated verifier for LLM answers on SEC 10-K filings</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <nav className="flex flex-wrap gap-1 text-sm">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={withBasis(n.href)}
                className={`rounded px-2 py-1 ${isActive(n.href) ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div role="group" aria-label="Scoring basis" className="flex w-fit rounded border border-slate-300 text-sm">
            {(["corrected", "as_scored"] as Basis[]).map((b) => (
              <button
                key={b}
                type="button"
                aria-pressed={basis === b}
                onClick={() => router.replace(b === "as_scored" ? `${pathname}?basis=as_scored` : pathname)}
                className={`px-3 py-1 ${basis === b ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {BASIS_LABEL[b]}
              </button>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}
