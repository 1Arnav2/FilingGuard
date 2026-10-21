"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { copy } from "@/lib/content";

/** The old /attack-types/ URL: By attack type is now a section of Results. */
export function AttackTypesRedirect() {
  const router = useRouter();
  const basis = useSearchParams().get("basis");
  const target = `/results/${basis === "as_scored" ? "?basis=as_scored" : ""}#by-attack-type`;
  useEffect(() => router.replace(target), [router, target]);
  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-semibold">By attack type</h1>
      <p>
        {copy.states.redirect}{" "}
        <Link href={target} className="underline underline-offset-4">
          Go to Results
        </Link>
      </p>
    </div>
  );
}
