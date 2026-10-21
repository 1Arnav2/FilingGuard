// The six pass bars: the four in summary.pass_bars plus the two seeded thresholds. Titles take their
// thresholds from the summary key names or fields, so no threshold is typed into the page.

import { copy, fill } from "./content";
import type { Basis, PassBars, Summary } from "./types";

const OPS: Record<string, string> = { lt: "<", le: "≤", ge: "≥" };
const NAMES = copy.results.bar_names as Record<string, string>;

/** "Control questions left unanswered ≤ 10% (treatment)" from `abstain_rate_controls_le_10pct_treatment`. */
export function barTitle(key: string): string {
  const m = key.match(/^(.*?)_(p_)?(lt|le|ge)_([\d.]+?)(pct)?(?:_([a-z]+))?$/);
  if (!m) return NAMES[key] ?? key;
  const [, name, p, op, value, isPct, scope] = m;
  const where = scope === "treatment" ? ", with the verifier" : "";
  return `${NAMES[name] ?? name} (${p ? "p " : ""}${OPS[op]} ${value}${isPct ? "%" : ""}${where})`;
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
      title: `${NAMES.seeded_macro} (≥ ${seeded.macro_threshold})`,
      explain: explain.seeded_macro,
      status: { corrected: seeded.macro_status, as_scored: null },
    },
    {
      key: "false_blocks",
      title: `${NAMES.false_blocks} (≤ ${seeded.false_block_rate.threshold})`,
      explain: explain.false_blocks,
      status: { corrected: seeded.false_block_rate.corrected.status, as_scored: seeded.false_block_rate.as_scored.status },
    },
  ];
}
