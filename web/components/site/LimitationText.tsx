import Link from "next/link";
import { Fragment } from "react";

import { itemHref } from "@/lib/links";

/** A limitation exactly as written in summary.json, with each FG-xxxx linked to its item. */
export function LimitationText({ text }: { text: string }) {
  const parts = text.split(/(FG-\d{4})/);
  return (
    <>
      {parts.map((part, i) =>
        /^FG-\d{4}$/.test(part) ? (
          <Link key={i} href={itemHref(part, "corrected")} className="font-mono underline underline-offset-4">
            {part}
          </Link>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}
