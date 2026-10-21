"use client";

import { Info } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { ExplainerBody } from "@/components/site/Explainer";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { BASIS_LABEL, useBasis } from "@/lib/basis";
import { copy } from "@/lib/content";
import type { Basis } from "@/lib/types";

const BASES: Basis[] = ["corrected", "as_scored"];

/** Corrected / As scored, kept in the URL; announces the change; opens the "Why two numbers?" explainer. */
export function BasisToggle() {
  const basis = useBasis();
  const pathname = usePathname();
  const router = useRouter();
  const params = useSearchParams();
  const [announced, setAnnounced] = useState("");

  const switchTo = (b: Basis) => {
    const next = new URLSearchParams(params);
    if (b === "as_scored") next.set("basis", b);
    else next.delete("basis");
    router.replace(next.size ? `${pathname}?${next}` : pathname, { scroll: false });
    setAnnounced(`Showing ${BASIS_LABEL[b]} basis`);
  };

  return (
    <div className="flex items-center gap-1">
      <div role="group" aria-label="Scoring basis" className="flex rounded-lg border p-0.5 text-sm">
        {BASES.map((b) => (
          <button
            key={b}
            type="button"
            aria-pressed={basis === b}
            onClick={() => switchTo(b)}
            className={`min-h-11 rounded-md px-3 sm:min-h-8 ${
              basis === b ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {BASIS_LABEL[b]}
          </button>
        ))}
      </div>
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="icon" className="size-11 sm:size-9" aria-label={copy.explainer.title}>
            <Info aria-hidden="true" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-80 p-4">
          <ExplainerBody />
        </PopoverContent>
      </Popover>
      <span className="sr-only" aria-live="polite">
        {announced}
      </span>
    </div>
  );
}
