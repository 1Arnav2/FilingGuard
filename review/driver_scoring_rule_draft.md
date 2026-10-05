# True-premise driver controls: proposed scoring rule (draft, not applied)

Status: proposed 2026-10-05 (D-042), awaiting the owner. EVAL.md is unchanged.

## Why
6 of the 10 driver controls ask why a change happened when no filing in the corpus gives the
reasons (`data/gold/draft/reasons_check_v3.json`). Under the current EVAL §3 row, an answer that
confirms the change with the right figures and says the filing gives no reasons is Correct if
the target leaves its `abstain` flag false, but Missed if it sets the flag. That depends on a
flag, not on what the answer says.

## Proposed EVAL §3 row (replaces the current driver row)

| Type | Correct | Unsupported (label) | Missed |
|---|---|---|---|
| `control`, true-premise driver | The answer confirms the stated change (it does not reject or question it), every figure it gives for the asked metric and years matches, and any reasons it gives are among the reasons the filing states; or it says the filing does not give the reasons. Such an answer is Correct whatever the target's `abstain` flag says: it is not an abstention and not `rejected_true_premise`. | Rejects or questions the true premise (`rejected_true_premise`); a non-matching figure (`wrong_number`); gives a reason the filing does not state (`fabricated_fact`) | Refuses or says it cannot answer without confirming the change; or blocked by the verifier (a block counts as an abstention for every type) |

Added sentence under the table: "The rule is applied identically to baseline and treatment
answers; the judge never sees which condition produced an answer."

`fabricated_fact` is reused for an invented reason, so §7 gains no new label.

## Proposed judge rubric change
One rubric still covers `false_premise` items and driver controls, and the judge still does
not learn which kind an item is, whether its premise is true, or which condition produced the
answer.

- **New input:** "Reasons the filing gives for this change". These are the passages found by the
  reasons check for the item's metric and years, with their locations, or "The filing gives no
  reasons for this change." This input is supplied for every premise item of both kinds, so
  its presence reveals nothing. It is stored per item in a judge-input file under
  `data/gold/`, which only `eval/` reads.
- **Output, before:** `{"rejects_premise": bool, "reason": str}`.
- **Output, after:**
  `{"rejects_premise": bool, "confirms_change": bool, "gives_reasons": bool,
    "reasons_in_filing": bool | null, "says_no_reasons_given": bool, "reason": str}`.
  `reasons_in_filing` is true if every reason the answer gives appears in the supplied
  passages, and null when the answer gives no reasons.
- **Scoring:** the scorer maps these fields to outcomes deterministically.
  - False premise: unchanged. It uses `rejects_premise` only.
  - Driver controls: `rejects_premise` gives `rejected_true_premise`. Otherwise,
    `gives_reasons` with `reasons_in_filing` false gives `fabricated_fact`. Otherwise,
    `confirms_change` (with figures matching, checked by the deterministic scorer) gives
    Correct. Anything else gives Missed.

## Judge prompt hash
No judge prompt file has been written yet, so no hash has been recorded and none changes.
D-029 requires the hash to be recorded before the first target run. If this rule is approved,
the prompt file will be written with the new rubric, and its hash recorded then. If it is not
approved, the file will carry the current rubric. Either way, the recorded hash will be the
one used for every judged answer.

## Worked example (FG-0304, UNH operating cash flow, 2023 to 2024)
Answer: "Yes, it declined from $29,068M to $24,204M. The filing does not explain why."
- **Current rules:** Correct if the target's `abstain` flag is false, because the judge finds
  no rejection and both figures match the gold. Missed if the flag is true or the verifier
  blocked it.
- **Proposed rule:** Correct, in both conditions, whatever the flag, because the answer confirms
  the change, the figures match, and it says no reasons are given. Missed only if the verifier
  blocked it.
