"use client";

import { ExternalLink, Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { BasisToggle } from "@/components/site/BasisToggle";
import { Logo } from "@/components/site/Logo";
import { ThemeToggle } from "@/components/site/ThemeToggle";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useBasis } from "@/lib/basis";
import { author, copy } from "@/lib/content";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/results/", label: "Results" },
  { href: "/items/", label: "Items" },
  { href: "/method/", label: "Method" },
  { href: "/limitations/", label: "Limitations" },
];

/** Pages where the basis changes what is shown; the toggle is hidden elsewhere. */
const BASIS_PAGES = ["/", "/results", "/items", "/item"];

function trim(path: string): string {
  return path.length > 1 ? path.replace(/\/$/, "") : path;
}

export function SiteHeader() {
  const pathname = trim(usePathname());
  const basis = useBasis();
  const [open, setOpen] = useState(false);
  const showBasis = BASIS_PAGES.includes(pathname);
  const withBasis = (href: string) => (basis === "as_scored" ? `${href}?basis=as_scored` : href);
  const active = (href: string) => {
    const h = trim(href);
    return h === "/" ? pathname === "/" : pathname === h || (h === "/items" && pathname === "/item");
  };

  const links = (onNavigate?: () => void) =>
    NAV.map((n) => (
      <Link
        key={n.href}
        href={withBasis(n.href)}
        onClick={onNavigate}
        aria-current={active(n.href) ? "page" : undefined}
        className={`flex min-h-11 items-center rounded-md px-3 text-sm sm:min-h-9 ${
          active(n.href) ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:text-foreground"
        }`}
      >
        {n.label}
      </Link>
    ));

  return (
    <header className="border-b bg-background/90 backdrop-blur supports-backdrop-filter:bg-background/75">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-2 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:py-3">
        <div className="flex items-center justify-between gap-3">
          <Link href={withBasis("/")} aria-label={copy.site.name} className="flex min-h-11 items-center">
            <Logo className="h-6 w-auto" />
          </Link>
          <div className="flex items-center gap-1 lg:hidden">
            <ThemeToggle />
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="size-11" aria-label="Open menu">
                  <Menu aria-hidden="true" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-72 p-4">
                <SheetHeader className="p-0">
                  <SheetTitle>{copy.site.name}</SheetTitle>
                </SheetHeader>
                <nav aria-label="Main" className="flex flex-col gap-1">
                  {links(() => setOpen(false))}
                  <a
                    href={author.repo}
                    className="flex min-h-11 items-center gap-1 rounded-md px-3 text-sm text-muted-foreground hover:text-foreground"
                  >
                    {copy.site.code_label}
                    <ExternalLink aria-hidden="true" className="size-3.5" />
                    <span className="sr-only">(opens GitHub)</span>
                  </a>
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <nav aria-label="Main" className="hidden items-center gap-1 lg:flex">
            {links()}
            <a
              href={author.repo}
              className="flex min-h-9 items-center gap-1 rounded-md px-3 text-sm text-muted-foreground hover:text-foreground"
            >
              {copy.site.code_label}
              <ExternalLink aria-hidden="true" className="size-3.5" />
              <span className="sr-only">(opens GitHub)</span>
            </a>
          </nav>
          {showBasis && <BasisToggle />}
          <div className="hidden lg:block">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </header>
  );
}
