"use client";

import Method from "@/components/Method";
import { Loading } from "@/components/ui";
import { getMeta, getSummary } from "@/lib/api";
import { useData } from "@/lib/useData";

export default function MethodPage() {
  const summary = useData(getSummary);
  const meta = useData(getMeta);
  if (!summary.data || !meta.data) return <Loading error={summary.error ?? meta.error} />;
  return <Method summary={summary.data} meta={meta.data} />;
}
