import { ChevronRight } from "lucide-react";

import { cn } from "@/lib/utils";

/** A native <details> that looks clickable: a chevron that turns when open, a button-like summary. */
export function Disclosure({ summary, count, boxed = false, children }: {
  summary: string;
  count?: number;
  boxed?: boolean;
  children: React.ReactNode;
}) {
  return (
    <details className={cn("group", boxed && "rounded-xl border")}>
      <summary
        className={cn(
          "flex min-h-11 cursor-pointer list-none items-center gap-1.5 text-sm font-medium select-none [&::-webkit-details-marker]:hidden",
          boxed ? "rounded-xl px-5 py-3 hover:bg-muted/50" : "w-fit rounded-md border px-3 hover:bg-muted sm:min-h-8",
        )}
      >
        <ChevronRight aria-hidden="true" className="size-4 shrink-0 transition-transform group-open:rotate-90" />
        {summary}
        {count !== undefined && <span className="text-muted-foreground tabular-nums">({count})</span>}
      </summary>
      <div className={cn(boxed ? "border-t p-5" : "mt-3")}>{children}</div>
    </details>
  );
}
