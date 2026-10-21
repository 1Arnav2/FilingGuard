"use client";

import { useEffect, useState } from "react";

import { getSummary } from "@/lib/api";
import { usd } from "@/lib/format";
import type { Summary } from "@/lib/types";

export default function Footer() {
  const [summary, setSummary] = useState<Summary | null>(null);
  useEffect(() => {
    getSummary().then(setSummary, () => setSummary(null));
  }, []);

  return (
    <footer className="mt-12 border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500">
        {summary ? (
          <p>
            {summary.split} split, {summary.n_items} items, frozen. Numbers from{" "}
            <code className="font-mono">{summary.generated_from}</code>. Model spend {usd(summary.spend.total_usd)} of{" "}
            {usd(summary.spend.cap_usd, 2)} cap. This dashboard makes no model calls.
          </p>
        ) : (
          <p>Numbers from committed results files. This dashboard makes no model calls.</p>
        )}
      </div>
    </footer>
  );
}
