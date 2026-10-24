"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { copy } from "@/lib/content";
import { ITEMS } from "@/lib/data";
import { itemHref } from "@/lib/links";

/** Older links (`/item/?id=FG-xxxx`) open the item's own page, keeping the rest of the query. */
export default function ItemRedirect() {
  const params = useSearchParams();
  const router = useRouter();
  const id = params.get("id") ?? "";
  const known = ITEMS.some((item) => item.id === id);
  useEffect(() => {
    if (!known) return;
    const view = Object.fromEntries(params);
    router.replace(itemHref(id, view.basis === "as_scored" ? "as_scored" : "corrected", view));
  }, [known, id, params, router]);
  if (known) return null;
  return (
    <div role="alert" className="space-y-2">
      {id && <h1 className="text-2xl font-semibold">{id}</h1>}
      <p>{id ? copy.item.not_found : copy.item.no_id}</p>
      <Link href="/items/" className="underline underline-offset-4">
        {copy.item.back}
      </Link>
    </div>
  );
}
