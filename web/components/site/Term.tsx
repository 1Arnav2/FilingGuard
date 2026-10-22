"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { copy, definition, type GlossarySource } from "@/lib/content";

/** A dotted-underlined term whose definition opens on hover, focus or tap. Screen readers get the
 * definition as the term's description; focus never leaves the term. */
export function Term({ source, code, children }: { source: GlossarySource; code: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const text = definition(source, code);
  if (!text) return <>{children}</>;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-describedby={id}
          onPointerEnter={(e) => e.pointerType === "mouse" && setOpen(true)}
          onPointerLeave={(e) => e.pointerType === "mouse" && setOpen(false)}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          className="cursor-help text-left underline decoration-muted-foreground decoration-dotted underline-offset-4"
        >
          {children}
        </button>
      </PopoverTrigger>
      <span id={id} className="sr-only">
        {text}
      </span>
      <PopoverContent
        side="top"
        className="w-72 p-3 text-sm"
        onOpenAutoFocus={(e) => e.preventDefault()}
        onCloseAutoFocus={(e) => e.preventDefault()}
      >
        <p className="leading-relaxed">{text}</p>
        <Link href={`/method/#glossary-${source}`} className="mt-1 inline-block text-xs font-medium underline underline-offset-4">
          {copy.glossary.more}
        </Link>
      </PopoverContent>
    </Popover>
  );
}
