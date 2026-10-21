"use client";

import Link from "next/link";

import { AuthorBlock } from "@/components/site/AuthorBlock";
import { getSummary } from "@/lib/api";
import { author, copy, fill } from "@/lib/content";
import { useData } from "@/lib/useData";

export function SiteFooter() {
  const { data: summary } = useData(getSummary);
  return (
    <footer className="mt-16 border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:px-6 md:flex-row md:justify-between">
        <div className="space-y-2">
          <p>{copy.site.footer}</p>
          {summary && <p>{fill(copy.site.spend, { summary })}</p>}
          <AuthorBlock compact />
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-4 gap-y-1">
          <Link href="/method/" className="inline-flex min-h-11 items-center hover:text-foreground md:min-h-0">
            Method
          </Link>
          <Link href="/limitations/" className="inline-flex min-h-11 items-center hover:text-foreground md:min-h-0">
            Limitations
          </Link>
          <a href={author.repo} className="inline-flex min-h-11 items-center hover:text-foreground md:min-h-0">
            {copy.site.code_label}
          </a>
        </nav>
      </div>
    </footer>
  );
}
