import { CircleAlert, CircleCheck, CircleMinus, CircleX } from "lucide-react";

import { outcomeName, statusName, verdictName } from "@/lib/content";
import { cn } from "@/lib/utils";

const TONE = {
  success: "bg-success-soft text-success",
  danger: "bg-danger-soft text-danger",
  warning: "bg-warning-soft text-warning",
  neutral: "bg-muted text-foreground",
} as const;

function Badge({ tone, icon: Icon, children, className }: {
  tone: keyof typeof TONE;
  icon?: typeof CircleCheck;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium whitespace-nowrap", TONE[tone], className)}>
      {Icon && <Icon aria-hidden="true" className="size-3.5" />}
      {children}
    </span>
  );
}

const STATUS: Record<string, [keyof typeof TONE, typeof CircleCheck]> = {
  met: ["success", CircleCheck],
  "not met": ["danger", CircleX],
  "not testable": ["warning", CircleAlert],
};

/** A pass bar's status: always the word, with an icon shape as a second cue. */
export function StatusBadge({ status }: { status: string }) {
  const [tone, icon] = STATUS[status] ?? ["neutral", CircleMinus];
  return (
    <Badge tone={tone} icon={icon}>
      {statusName(status)}
    </Badge>
  );
}

const OUTCOME: Record<string, [keyof typeof TONE, typeof CircleCheck]> = {
  correct: ["success", CircleCheck],
  missed: ["neutral", CircleMinus],
  unsupported: ["danger", CircleX],
};

export function OutcomeBadge({ outcome }: { outcome: string }) {
  const [tone, icon] = OUTCOME[outcome] ?? ["neutral", CircleMinus];
  return (
    <Badge tone={tone} icon={icon}>
      {outcomeName(outcome)}
    </Badge>
  );
}

const VERDICT: Record<string, [keyof typeof TONE, typeof CircleCheck]> = {
  pass: ["neutral", CircleCheck],
  flag: ["warning", CircleAlert],
  block: ["danger", CircleX],
};

export function VerdictBadge({ verdict }: { verdict: string }) {
  const [tone, icon] = VERDICT[verdict] ?? ["neutral", CircleMinus];
  return (
    <Badge tone={tone} icon={icon}>
      {verdictName(verdict)}
    </Badge>
  );
}

export function FlagBadge({ children }: { children: React.ReactNode }) {
  return <Badge tone="neutral">{children}</Badge>;
}
