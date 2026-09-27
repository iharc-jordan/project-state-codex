---
name: intel-battlecard
description: "Build or refresh a competitor battlecard — 'battlecard for X', 'how do we win against X', 'objection handling vs X'. Positioning, when they/we win, differentiators and traps, from cited claims."
map:
  tier: capability
  stage: generate
  inputs: [operator]
  reads: [intel, manifest]
  writes: [intel, log]
  produces: [intel-competitive]
  calls: [intel-harvester]
---

# intel-battlecard — evidence into seller guidance

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The intel capability's battlecard builder (OCI §7.2 battlecard-builder). Turns claims about one competitor AND about us (the self entity) into compact seller guidance: one-line positioning, when they win / when we win, differentiators that pass the three-part test (true ≥ medium confidence · relevant to this audience's criteria · provable by a doc, demo step or customer ref), discovery questions, traps, objection handling, proof points, a required avoid-saying list, and a talk track — every material line carrying claim ids, health.unsourced_lines == 0. Reads claims, never a profile's prose; refreshes only the stale claims it needs. Usage: 'intel-battlecard INT-E-NNN [--audience id]'. Trigger on 'build a battlecard for X', 'how do we position against X', 'what should reps say when X comes up', 'turn this profile into a battlecard', or the digest's intel.battlecard-behind. Refuses without a self entity with claims. Writes intel/battlecards/ through project-state; never edits a generated card.

A battlecard is a projection of claims, optimized for decisions, not completeness. It is
regenerated, never edited; if a human disagrees with a line, the correction goes into the
claim set and the card is rebuilt. Spec: `docs/INTEL-CI-SPEC.md` §5.2, OCI v0.1 §5.4 / §7.2.

## Preconditions, every invocation

Via `project-state`: `capabilities.intel` enabled; `competitive.self_entity` resolves to an
entity of type `self` **with claims** — refuse otherwise ("no self claims: nothing about us
is provable; run `/intel-harvester competitor self`"). Read every claim whose
`subject.entity` is the target and every claim on `self`. Read the `half_lives_days` table
and derive freshness per claim now. Read the audience from `competitive.audiences` when
`--audience` names one.

## Method

1. **Never re-research what is fresh.** If material claims the card needs are stale, call
   `intel-harvester competitor <id> --stale-only` for those categories only; do not run a
   full research pass. Note in "What this card does not know" what stayed stale.
2. **Projections do not read projections.** Ignore `intel/profiles/`; work from claims.
3. **Differentiators — the three-part test.** For each candidate:
   *true* — traces to a claim of `medium` confidence or better, and a `self` claim;
   *relevant* — connects to a decision criterion this audience uses (from `objection` /
   `win-loss` / `buyer-direct` claims, or the audience declaration);
   *provable* — `provable_by` names a document, a demo step, or a customer reference.
   Fails one → cut or qualify explicitly. Never keep a differentiator on `low` evidence.
4. **Frame comparatively, never pejoratively.** The register is *"X is strong when the
   buyer prioritizes A; we are stronger when B and C matter; here is how to find out which
   applies"* — not "X is bad."
5. **Avoid saying is required.** Populate it with every line that is unsupported, stale,
   misleading, or needlessly negative — including lines our own team repeats. This is the
   one section that removes ammunition, and it is what keeps the card from becoming a
   liability in a buyer's inbox.
6. **Conflicts stay visible.** A contested category is rendered as *contested* with both
   claims and dates, never as the one we prefer.
7. **Health.** `stale_claims_used` counts stale claims cited (cited with their date and
   marked); `unsourced_lines` must be 0 — a material line with no `[INT-C-…]` is a bug.

## Output

Write `intel/battlecards/<INT-E-NNN>[-<audience>].md` from `templates/battlecard.md`;
record the content hash in `state/intel.json → projections`; log
`intel.battlecard.generated` `{subject, audience, health}`. Re-render the Competitive report
(`python3 capabilities/intel/views/build-intel-competitive.py <facility>/project-state`).
Reply with the one-line positioning, the differentiator count (kept / cut), the avoid-saying
count, health, and what the card does not know.

## Human gate

The card is an internal file. Publishing it to a seller surface, posting it, or mailing it
is a separate, explicit action through `project-notifier` / `project-external-comms` (Gmail
always draft), logged as `intel.approval.logged` with the approver and the artifact.

## Discipline

Claims before prose · zero unsourced material lines · stale marked, never dropped ·
contested shown, never resolved · never edit a generated card — regenerate.
