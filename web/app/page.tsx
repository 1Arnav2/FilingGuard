"use client";

import { useEffect, useState } from "react";

import Scorecard from "@/components/Scorecard";
import { getSummary } from "@/lib/api";
import { useBasis } from "@/lib/basis";
import type { Summary } from "@/lib/types";

export default function ScorecardPage() {
  const basis = useBasis();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSummary().then(setSummary, (e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="text-rose-700">Could not load results: {error}</p>;
  if (!summary) return <p className="text-slate-500">Loading results…</p>;
  return <Scorecard summary={summary} basis={basis} />;
}
