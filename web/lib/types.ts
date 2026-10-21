// Response types for the read-only results API; they mirror src/filingguard/api/routes.py.

export type Basis = "corrected" | "as_scored";
export type Condition = "baseline" | "treatment";
export type Outcome = "correct" | "missed" | "unsupported";
export type Decision = "pass" | "flag" | "block";

export interface Rate {
  k: number;
  n: number;
  rate: number | null;
  wilson95: [number, number] | null;
}

export interface StatusRate extends Rate {
  status: string;
}

export interface UnsupportedBar {
  discordant_unsupported_to_not: number;
  discordant_not_to_unsupported: number;
  exact_two_sided_p: number;
  baseline_unsupported: number;
  best_possible_p_if_every_one_blocked: number;
  status: string;
}

export interface AbstainBar extends StatusRate {
  baseline: Rate;
}

export interface PrecisionBar {
  precision: Rate;
  recall: Rate;
  status: string;
}

export interface FaultBar extends StatusRate {
  source: string;
}

export interface PassBars {
  "unsupported_claim_rate_falls_p_lt_0.05": UnsupportedBar;
  abstain_rate_controls_le_10pct_treatment: AbstainBar;
  "verifier_precision_ge_0.85": PrecisionBar;
  test_set_fault_rate_le_5pct: FaultBar;
}

export interface ConditionSummary {
  outcomes: Partial<Record<Outcome, number>>;
  unsupported_claim_rate: Rate;
  correct_handling: Rate;
  answer_coverage: Rate;
  abstain_rate_controls: Rate;
  injection_followed: Rate;
}

export interface Seeded {
  macro_detection_T1_T3_T4_T5_T6_quote_off: number;
  macro_threshold: number;
  macro_status: string;
  by_transform_quote_off: Record<string, Rate>;
  by_transform_full: Record<string, Rate>;
  false_block_rate: { corrected: StatusRate; as_scored: StatusRate; threshold: number };
}

export interface Timing {
  n: number;
  p50: number;
  p95: number;
  mean: number;
}

export interface Summary {
  split: string;
  n_items: number;
  bases: string;
  pass_bars: Record<Basis, PassBars>;
  seeded_errors: Seeded;
  conditions: Record<Basis, Record<Condition, ConditionSummary>>;
  latency: { sample: number; run: number; end_to_end_s: Timing; verifier_rule_s: Timing };
  spend: { total_usd: number; cap_usd: number };
  limitations: string[];
  generated_from: string;
}

export interface ScoreView {
  outcome: Outcome;
  label: string | null;
  notes: string[];
}

export interface ItemRow {
  id: string;
  company: string;
  attack_type: string;
  subtype: string;
  question: string;
  baseline: ScoreView;
  treatment: ScoreView;
  verdict: Decision;
  reason_codes: string[];
  corrected: boolean;
}

export interface ItemPage {
  total: number;
  page: number;
  page_size: number;
  basis: Basis;
  items: ItemRow[];
}

export interface ItemFilters {
  attack_type?: string;
  outcome?: Outcome;
  label?: string;
  verdict?: Decision;
  basis?: Basis;
  condition?: Condition;
  page?: number;
  page_size?: number;
}

export interface Reason {
  code: string;
  basis: string;
  blocking: boolean;
  detail: string;
}

export interface ItemDetail {
  id: string;
  company: string;
  attack_type: string;
  subtype: string;
  question: string;
  answer: {
    text: string;
    abstained: boolean;
    claims: {
      text: string | null;
      value: number | null;
      unit: string | null;
      scale: string | null;
      period: string | null;
      concept: string | null;
      citation_index: number | null;
    }[];
    citations: {
      doc_id: string;
      chunk_id: string;
      start: number | null;
      end: number | null;
      quote: string;
      quote_found: boolean;
    }[];
    parse_error: string | null;
  };
  retrieved: { rank: number; chunk_id: string; item: string | null; source: string; score: number }[];
  outcomes: Record<Basis, Record<Condition, ScoreView>>;
  verdict: Record<"full" | "quote_off", { decision: Decision; reasons: Reason[] }>;
  correction: { pattern: string; evidence: Record<string, unknown>; reason: string; approval: string } | null;
  scale_not_followed: boolean;
  unparseable: boolean;
  injection: string | null;
}
