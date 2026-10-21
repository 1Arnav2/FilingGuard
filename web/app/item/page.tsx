"use client";

import { useSearchParams } from "next/navigation";

import ItemDetail from "@/components/ItemDetail";
import { Loading } from "@/components/ui";
import { getItem } from "@/lib/api";
import { useBasis } from "@/lib/basis";
import { useData } from "@/lib/useData";

export default function ItemPage() {
  const basis = useBasis();
  const id = useSearchParams().get("id") ?? "";
  const { data, error } = useData(() => getItem(id), [id]);
  if (!id) return <Loading error="no item id given" />;
  return data ? <ItemDetail item={data} basis={basis} /> : <Loading error={error} />;
}
