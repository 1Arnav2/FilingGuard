"use client";

import { useSearchParams } from "next/navigation";

import type { Basis } from "./types";

export const BASIS_LABEL: Record<Basis, string> = { corrected: "Corrected", as_scored: "As scored" };

/** The basis chosen in the URL (`?basis=`); corrected unless as_scored is asked for. */
export function useBasis(): Basis {
  return useSearchParams().get("basis") === "as_scored" ? "as_scored" : "corrected";
}
