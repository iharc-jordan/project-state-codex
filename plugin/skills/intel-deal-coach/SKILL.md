---
name: intel-deal-coach
description: "Coach a live deal against competitors — 'we're up against X on the Acme deal', 'how do we win this opportunity', 'deal coach'. Combines intel evidence with the deal's context into next moves."
map:
  tier: capability
  stage: generate
  inputs: [operator, files]
  reads: [intel, tenders, documents, manifest]
  writes: [intel, log]
  produces: [intel-competitive]
  calls: [intel-harvester]
---

# intel-deal-coach — evidence plus this deal, into the next move

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The intel capability's deal coach (OCI deal-compete-coach) — the highest-value competitive skill: evidence plus one live deal's context → what to do next in that opportunity. Reads deal context in competitive.deal_context order: a tender entity when the ref is a tender id, intel/deals/<ref>/context.md, inbox documents tagged with the ref, a CRM only through a deals.read connector. Produces a deal brief — deal read, what matters most, competitive dynamic, explicit vs inferred criteria, our best angle, risks and moves ranked (action · rationale · intended outcome), questions for the next call, talk track, proof to bring, do-not, missing context, confidence — and writes what it learned (objections, tactics) back as reported claims. Usage: 'intel-deal-coach <deal-ref> [--competitor INT-E-NNN]'. Trigger on 'help me win this deal against X', 'how do I handle X at <account>', 'prep me for the competitive call', 'review this deal and tell me how to position'. Never fabricates deal facts; names what it lacks.

A static library cannot do this; it is what the competitive layer exists for. The output is
deal-shaped, not library-shaped: if the brief would read the same for any deal against this
competitor, it has failed regardless of accuracy. Spec: `docs/INTEL-CI-SPEC.md` §5.3,
OCI v0.1 §5.5 / §7.3.

## Context, every invocation

Via `project-state`: `capabilities.intel` enabled; the competitor (from `--competitor`, from
the context file, or from the tender's known bidders — else say *competitor unknown* and
coach on our own position); claims for the competitor and for `self` with freshness derived
now. Then the **deal context**, in `competitive.deal_context` order, recording which
supplied it in `context_read`:

- `tender` — when `<deal-ref>` matches a tender id and the tender capability is enabled:
  `tenders/<id>.yaml` (buyer, procurement type, dates, requirements, workflow status, the
  bid/no-bid decision if recorded). This is a `deals.read` connector in OCI's sense.
- `deals-dir` — `intel/deals/<ref>/context.md` (from `templates/deal-context.md`): the
  seller's notes. Everything in it is `reported`; a verbatim buyer quote is `buyer-direct`.
- `inbox` — registered documents whose tags or filename carry the ref.
- a CRM — only through a connector that exposes `deals.read`; never a product name.

**Every input except the subject is optional.** Absent context thins the brief and is
named in *Missing context*; it is never invented.

## Analysis frame

Deal state · buyer priorities · competitive position (ours / theirs / unclear) · decision
criteria — **explicit (the buyer's words) and inferred (ours) kept separate** · risks ·
opportunities. Prefer this deal's context over generic guidance at every point, and say what
context you lacked.

## MUST

- **Rank moves**, each with `action`, `rationale`, `intended_outcome`. An unranked list of
  ten ideas is a non-answer; three ranked moves beat ten.
- **`missing_context` honest and specific** — "no stated evaluation criteria", "no discovery
  transcript" — never "limited information".
- **Populate `do_not`** — the tactics likely to hurt this deal, with the reason.
- **Fabricate nothing**: no deal fact, no competitor capability, no price, no named buyer
  motive without a claim or a context line behind it.
- **Write claims for what was learned**: an objection heard, a competitor tactic observed, a
  price quoted by the buyer — as `reported`, `source.class: internal-observation` (or
  `buyer-direct` for a verbatim quote), `logged_by: intel-deal-coach`, `source.ref` the
  context file or document. This is how the loop compounds instead of decaying.
- **Do not** produce a full battlecard unless asked; refresh only specific stale material
  claims (`intel-harvester competitor <id> --stale-only`), never a full research pass.

## Output

Write `intel/deals/<ref>/brief.md` from `templates/deal-brief.md`; record its hash in
`state/intel.json → projections`; log `intel.deal-brief.generated` `{deal_ref, competitor,
confidence}` and one `intel.claim.logged` per claim written. Re-render the Competitive
report. Reply with the deal read, the top three moves, the do-not list, and the missing
context.

## Discipline

Context beats content · explicit and inferred criteria never merged · every claim cited ·
absent context named, never filled · the brief is a file in the Project; sending it anywhere
is a gated action.
