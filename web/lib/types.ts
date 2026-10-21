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

export interface TypeSummary {
  n: number;
  outcomes: Partial<Record<Outcome, number>>;
  labels: Record<string, number>;
}

export interface ConditionSummary {
  outcomes: Partial<Record<Outcome, number>>;
  by_type: Record<string, TypeSummary>;
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
  spend: { total_usd: number; cap_usd: number; by_purpose_usd: Record<string, number> };
  bootstrap_by_type_corrected: Record<
    string,
    Record<"unsupported_share" | "correct_share", { change: number; bootstrap95: [number, number] }>
  >;
  limitations: string[];
  generated_from: string;
}

export interface Meta {
  split: { dev: number; test: number; total: number };
  attack_types_test: Record<string, number>;
  companies: number;
  freeze_tags: Record<string, { commit: string; url: string }>;
  repo: string;
  pass_bars_set: { decision: string; title: string; date: string; where: string };
  corrections: { decision: string; rule: string; corrected: number; kept_as_scored: number };
  handcheck: { sheet: string; natural_rows: number; with_note: number };
  inputs_sha256: Record<string, string>;
  generated_by: string;
  generated_from: string;
}

export interface ScoreView {
  outcome: Outcome;
  label: string | null;
  notes: string[];
  abstained: boolean;
  scale_not_followed: boolean;
  unparseable: boolean;
  injection: string | null;
  answer_followed: boolean | null;
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
  unparseable: boolean;
  handchecked: boolean;
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

export interface Figure {
  value: number;
  scale: string | null;
  negative: boolean;
  metric: string | null;
  adjusted: boolean;
  asked: boolean;
  period: string | null;
  period_ok: boolean | null;
}

export interface Judge {
  rejects_premise: boolean | null;
  confirms_change: boolean | null;
  gives_reasons: boolean | null;
  reasons_in_filing: boolean | null;
  says_no_reasons_given: boolean | null;
  reason: string | null;
}

export interface ItemDetail {
  id: string;
  company: string;
  attack_type: string;
  subtype: string;
  question: string;
  gold: {
    expected_behavior: string;
    text: string;
    value: number | null;
    unit: string | null;
    metric: string | null;
    fiscal_year: number | null;
    [key: string]: unknown;
  };
  answer: {
    text: string | null;
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
    unparseable_chars: number | null;
  };
  retrieved: { rank: number; chunk_id: string; item: string | null; source: string; score: number }[];
  figures: Figure[];
  judge: Judge | null;
  outcomes: Record<Basis, Record<Condition, ScoreView>>;
  verdict: Record<"full" | "quote_off", { decision: Decision; reasons: Reason[] }>;
  correction: {
    status: "corrected" | "kept as scored";
    as_scored: (string | null)[];
    corrected: (string | null)[] | null;
    pattern: string | null;
    evidence: Record<string, unknown> | null;
    reason: string;
    approval: string | null;
  } | null;
  handcheck: { why_listed: string; verdict: string | null; note: string | null; pre_filled: string | null } | null;
}
