// The six pass bars: the four in summary.pass_bars plus the two seeded thresholds. Titles take their
// thresholds from the summary key names or fields, so no threshold is typed into the page.

import { copy, fill } from "./content";
import type { Basis, PassBars, Summary } from "./types";

const OPS: Record<string, string> = { lt: "<", le: "≤", ge: "≥" };
const NAMES = copy.results.bar_names as Record<string, string>;

/** A threshold share (0.85) as a percentage (85%); a value already in percent passes through. */
function percent(value: number): string {
  return `${Number((value * 100).toFixed(2))}%`;
}

/** "Verifier precision (≥ 85%)" from `verifier_precision_ge_0.85`; p-value thresholds stay as p. */
export function barTitle(key: string): string {
  const m = key.match(/^(.*?)_(p_)?(lt|le|ge)_([\d.]+?)(pct)?(?:_([a-z]+))?$/);
  if (!m) return NAMES[key] ?? key;
  const [, name, p, op, value, isPct, scope] = m;
  const where = scope === "treatment" ? ", with the verifier" : "";
  const threshold = p ? `p ${OPS[op]} ${value}` : `${OPS[op]} ${isPct ? `${value}%` : percent(Number(value))}`;
  return `${NAMES[name] ?? name} (${threshold}${where})`;
}

export interface Bar {
  key: string;
  title: string;
  explain: string;
  status: Record<Basis, string | null>;
}

export function bars(s: Summary): Bar[] {
  const explain = copy.results.bars as Record<string, string>;
  const keys = Object.keys(s.pass_bars.corrected) as (keyof PassBars)[];
  const seeded = s.seeded_errors;
  return [
    ...keys.map((key) => ({
      key,
      title: barTitle(key),
      explain: fill(explain[key] ?? "", { summary: s }),
      status: { corrected: s.pass_bars.corrected[key].status, as_scored: s.pass_bars.as_scored[key].status },
    })),
    {
      key: "seeded_macro",
      title: `${NAMES.seeded_macro} (≥ ${percent(seeded.macro_threshold)})`,
      explain: explain.seeded_macro,
      status: { corrected: seeded.macro_status, as_scored: null },
    },
    {
      key: "false_blocks",
      title: `${NAMES.false_blocks} (≤ ${percent(seeded.false_block_rate.threshold)})`,
      explain: explain.false_blocks,
      status: { corrected: seeded.false_block_rate.corrected.status, as_scored: seeded.false_block_rate.as_scored.status },
    },
  ];
}
