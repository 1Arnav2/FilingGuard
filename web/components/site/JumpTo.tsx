"use client";

import { copy } from "@/lib/content";

export interface JumpSection {
  id: string;
  label: string;
}

function go(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${id}`);
  el.scrollIntoView();
  el.focus({ preventScroll: true });
}

/** Section navigation for long pages: a sticky link row on wide screens, a select on narrow ones. */
export function JumpTo({ sections }: { sections: JumpSection[] }) {
  return (
    <>
      <nav
        aria-label={copy.site.jump}
        className="sticky top-0 z-20 -mx-4 mt-8 hidden border-b bg-background/90 px-4 backdrop-blur supports-backdrop-filter:bg-background/75 sm:-mx-6 sm:px-6 lg:block"
      >
        <ul className="flex flex-wrap gap-x-1 py-2 text-sm">
          <li className="flex items-center pr-2 text-xs font-medium text-muted-foreground">{copy.site.jump}</li>
          {sections.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.id}`}
                onClick={(e) => {
                  e.preventDefault();
                  go(s.id);
                }}
                className="flex min-h-9 items-center rounded-md px-2.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <label className="mt-6 flex flex-col gap-1 text-xs font-medium text-muted-foreground lg:hidden">
        {copy.site.jump}
        <select
          defaultValue=""
          onChange={(e) => {
            go(e.target.value);
            e.target.value = "";
          }}
          className="min-h-11 rounded-lg border bg-background px-2 text-sm text-foreground"
        >
          <option value="" disabled>
            Choose a section
          </option>
          {sections.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </label>
    </>
  );
}
