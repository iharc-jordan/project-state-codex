---
name: intel-winloss
description: "Learn from closed deals — 'we lost the X deal', 'record a win', 'why do we lose to X', 'win-loss analysis'. Keeps the seller's and the buyer's reasons apart; every pattern with its sample size."
map:
  tier: capability
  stage: generate
  requires: [memory, python]
  inputs: [operator, files]
  reads: [intel, tenders, documents, manifest]
  writes: [intel, log]
  produces: [intel-winloss]
  calls: [project-state]
---

# intel-winloss — actual outcomes into reusable learning

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The intel capability's win-loss analyzer (OCI win-loss-analyzer, intel 1.2). Records each closed deal as an INT-W win-loss record — outcome, competitor, segment, the seller's reported reason and the buyer's evidenced reason kept in separate fields, explicit vs inferred decision criteria, objections, product gaps — and writes what it teaches back as claims (win-loss, objection, product-gap, sales-tactic). Aggregates only with the sample behind every pattern, segmented before generalised, with the seller/buyer divergence rate reported as a finding about the sales organisation. Verbs: 'record <deal-ref> [--outcome win|loss|no-decision]', 'evidence <INT-W-NNN>' (add the buyer's debrief after the close), 'analyze [--since --until]'. Trigger on 'we lost the Moose Jaw deal', 'we won Regina', 'log this loss', 'the buyer told us why', 'why do we lose to Northline', 'win-loss review', the tender capability's won / lost transitions, or the intel-quarterly-winloss matrix entry.

Seller-reported loss reasons lean toward price and away from execution. A record that blends the
two teaches the organisation the wrong lesson at scale, so the **seller's reason and the buyer's
are never merged**, and a pattern without its sample is folklore. Spec: `docs/INTEL-CI-SPEC.md`
§14.2; OCI v0.1 §5.5 and §7.5. `<plugin>` is the plugin root (two levels up from this skill).

## Context, every invocation

Via `project-state`: `capabilities.intel` (refuse when disabled), `competitive.winloss`
(`min_sample`, `reason_categories_extra`), `competitive.self_entity`, the win-loss records, and the
deal's context in `competitive.deal_context` order — a **tender** entity when the ref is a tender id
and the tender capability is enabled (outcome, buyer, the debrief if recorded), then
`intel/deals/<ref>/context.md`, then inbox documents tagged with the ref, then a CRM only through a
`deals.read` connector. Record which supplied it in `context_read`.

## `record <deal-ref> [--outcome win|loss|no-decision] [--competitor INT-E-NNN]`

1. **Outcome and close date** from the tender (`awarded` = win, `unsuccessful` = loss, `cancelled`
   = no-decision) or the operator. **Competitor**: who won (on a loss) or was beaten (on a win);
   `~` when unknown — never guessed.
2. **The seller's reason**, verbatim where it exists (the rep's note, a CRM field, what the
   operator says), with a category from the reason taxonomy (`price · product-fit · feature-gap ·
   integration · security-compliance · relationship · incumbent · execution · timing ·
   procurement-terms · budget · trust · other`, plus the manifest's extras). This is
   `reported`, `internal-observation`.
3. **The buyer's reason** only from something the buyer said or wrote — a debrief interview, a
   debrief letter or scoring sheet, an email from the buyer — with its source (`class:
   buyer-direct`, `ref`) and `epistemic_status: reported`. **Never infer the buyer's reason from
   the seller's notes.** No buyer evidence → `buyer_evidenced_reason: ~`, and say so: propose
   booking a debrief and name who to ask (by role).
4. **Decision criteria**, each marked `explicit: true` (the buyer's words) or `false` (ours);
   objections encountered; product gaps.
5. **Write the claims it teaches**, each through `project-state`, `logged_by: intel-winloss`,
   `source.ref` the context file or document: a `win-loss` claim on the competitor when there is
   buyer evidence (`reported`, `buyer-direct`); an `objection` claim per objection; a
   `product-gap` claim on the **self** entity per gap; a `sales-tactic` claim for a competitor
   move observed. Log `intel.claim.logged` for each.
6. **Write the record** `intel/winloss/INT-W-NNN.yaml` from `templates/entities/W.yaml` (counter
   `winloss` in `state/intel.json`), `claims_generated` listing the ids from step 5. Log
   `intel.winloss.recorded` `{id, deal_ref, outcome, competitor, has_buyer_evidence}`.
7. **Preserve the context.** No `intel/deals/<ref>/context.md` yet → write one from
   `templates/deal-context.md` with the outcome and the lines this record rests on; the golden set
   and the deal coach read it later.
8. Re-render the Competitive report
   (`python3 <plugin>/capabilities/intel/views/build-intel-competitive.py <facility>/project-state`).

Reply with the record id, the two reasons side by side, what it wrote as claims, and whether a
debrief is still needed.

## `evidence <INT-W-NNN>` — the buyer's reason, after the close

The record is append-only except its lifecycle fields: add `buyer_evidenced_reason`, append to
`interviews` and `claims_generated` (writing the new claims as in step 5). **The seller's reason is
never touched** — it is the record of what the rep said. The server refuses any other change. Log
`intel.winloss.evidenced`.

## `analyze [--since YYYY-MM-DD] [--until YYYY-MM-DD]` — the quarterly matrix entry

```bash
python3 <plugin>/capabilities/intel/scripts/winloss.py <facility>/project-state --since <from> --until <to> --json
```

Write `intel/reports/winloss-<YYYY-QN>.md` from `templates/winloss-report.md`, using the script's
numbers and nothing else:

- **The sample first** — records, outcomes, how many carry buyer evidence.
- **Divergence** — "sellers and buyers gave different reasons in k of n deals where both are known",
  and where it concentrates (seller said price, buyer said execution). This is a finding about the
  sales organisation; say so.
- **Patterns by segment**, each as the script states it: *lost on price in 2 of 3 municipal deals
  against Northline — 1 on the seller's word only*. A pattern below `min_sample` is labelled
  anecdote. A reason whose share differs sharply between segments (the script's `reversals`) is
  reported per segment and flagged — never as one line.
- **Objections and gaps heard**, with how many deals each came from; **what we do not know**
  (losses with no debrief, segments too small, unnamed competitors); **recommended actions**,
  owned and specific.
- Every line cites its records `[INT-W-…]` and claims `[INT-C-…]`. Never write "we lose on price" or
  any pattern without its k of n.

Record the file's hash in `state/intel.json → projections`, stamp `last_winloss_analysis`, log
`intel.winloss.analyzed` `{path, records, divergence_rate, segments}`. The analysis is a draft for
PL review; sending it anywhere is a gated action.

## Discipline

Seller and buyer reasons never merged · buyer reasons only from the buyer · every pattern with its
sample, segmented before generalised · anecdote labelled · records append-only but for the buyer
evidence that arrives later · the loop compounds: what a deal taught becomes claims the battlecard,
the deal coach and the brief read · all writes through `project-state`.
