"use client";

import AttackTypes from "@/components/AttackTypes";
import { Loading } from "@/components/ui";
import { getSummary } from "@/lib/api";
import { useBasis } from "@/lib/basis";
import { useData } from "@/lib/useData";

export default function AttackTypesPage() {
  const basis = useBasis();
  const { data, error } = useData(getSummary);
  return data ? <AttackTypes summary={data} basis={basis} /> : <Loading error={error} />;
}
