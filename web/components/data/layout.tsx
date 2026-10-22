"use client";

import { useEffect } from "react";

import { cn } from "@/lib/utils";
import { copy } from "@/lib/content";

export function PageHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="max-w-3xl space-y-3">
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
      {children && <div className="text-base leading-relaxed text-muted-foreground">{children}</div>}
    </div>
  );
}

export function Section({ id, title, intro, children, className }: {
  id?: string;
  title: string;
  intro?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      id={id}
      tabIndex={id ? -1 : undefined}
      aria-labelledby={id ? `${id}-title` : undefined}
      className={cn("mt-14 scroll-mt-24 focus:outline-none", className)}
    >
      <h2 id={id ? `${id}-title` : undefined} className="text-xl font-semibold tracking-tight">
        {title}
      </h2>
      {intro && <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">{intro}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

export function Panel({ id, className, children }: { id?: string; className?: string; children: React.ReactNode }) {
  return (
    <div id={id} tabIndex={id ? -1 : undefined} className={cn("scroll-mt-24 rounded-xl border bg-card p-5 focus:outline-none", className)}>
      {children}
    </div>
  );
}

/** Small label above a large number, Mercury style. */
export function Figure({ label, value, sub, className }: { label: string; value: React.ReactNode; sub?: React.ReactNode; className?: string }) {
  return (
    <div className={className}>
      <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      {sub && <div className="mt-1 text-sm text-muted-foreground">{sub}</div>}
    </div>
  );
}

export function LoadingState() {
  return (
    <div role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
      <span aria-hidden="true" className="size-2 animate-pulse rounded-full bg-muted-foreground" />
      {copy.states.loading}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="max-w-xl space-y-2 rounded-xl border p-5 text-sm">
      <p className="font-medium">{copy.states.error}</p>
      <p className="font-mono text-xs text-muted-foreground">{error}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="min-h-11 rounded-md border px-3 font-medium hover:bg-muted sm:min-h-9">
          {copy.states.retry}
        </button>
      )}
    </div>
  );
}

/** Scroll to the URL's #anchor once the page's data has rendered (the browser tries before it exists). */
export function useScrollToHash(ready: boolean) {
  useEffect(() => {
    if (!ready || !window.location.hash) return;
    const el = document.getElementById(decodeURIComponent(window.location.hash.slice(1)));
    el?.scrollIntoView();
  }, [ready]);
}

/** Loading, error or the page: one place for the three states. */
export function Load<T>({ data, error, retry, children }: {
  data: T | null;
  error: string | null;
  retry?: () => void;
  children: (data: T) => React.ReactNode;
}) {
  useScrollToHash(data !== null);
  if (error) return <ErrorState error={error} onRetry={retry} />;
  if (data === null) return <LoadingState />;
  return <>{children(data)}</>;
}
