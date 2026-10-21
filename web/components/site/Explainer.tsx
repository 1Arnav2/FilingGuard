import Link from "next/link";

import { copy } from "@/lib/content";

/** "Why two numbers?": the same copy in the toggle's popover and on the Overview card. */
export function ExplainerBody({ headingLevel = 3 }: { headingLevel?: 2 | 3 }) {
  const Heading = `h${headingLevel}` as const;
  return (
    <div className="space-y-2">
      <Heading className="text-sm font-semibold">{copy.explainer.title}</Heading>
      {copy.explainer.body.map((p) => (
        <p key={p} className="text-sm leading-relaxed text-muted-foreground">
          {p}
        </p>
      ))}
      <Link href="/method/#scoring" className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4 sm:min-h-0">
        {copy.explainer.link}
      </Link>
    </div>
  );
}
