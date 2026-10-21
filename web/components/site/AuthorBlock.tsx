import { author, copy } from "@/lib/content";

/** "Built by" with GitHub and LinkedIn links from web/content/author.json; an empty link is hidden. */
export function AuthorBlock({ id, compact = false }: { id?: string; compact?: boolean }) {
  const links = [
    { href: author.github, label: "GitHub" },
    { href: author.linkedin, label: "LinkedIn" },
  ].filter((l) => l.href);
  return (
    <div id={id} className={compact ? "text-sm" : "space-y-2"}>
      <p className={compact ? "inline" : "text-sm text-muted-foreground"}>
        {copy.overview.author_title} <span className="font-medium text-foreground">{author.name}</span>
      </p>
      <ul className={compact ? "ml-2 inline-flex gap-3" : "flex gap-4"}>
        {links.map((l) => (
          <li key={l.label}>
            <a href={l.href} className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4 sm:min-h-0">
              {l.label}
              <span className="sr-only"> profile of {author.name}</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
