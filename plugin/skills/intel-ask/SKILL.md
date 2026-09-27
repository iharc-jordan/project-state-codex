---
name: intel-ask
description: "Answer a competitive question from the intel evidence base, with citations — 'what do we know about X', 'how do we compare on Y', 'ask intel'. Answers only from retrieved claims and signals, labelled; never from memory."
map:
  tier: capability
  stage: generate
  inputs: [operator]
  reads: [intel, manifest]
  writes: [intel, log]
  produces: [intel-competitive]
  delivers: [chat]
---

# intel-ask — the evidence base, conversationally

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Grounded question-answering over the intel capability's evidence base (OCI §7.7 ask-competitive-intel). Answers from RETRIEVED claims (by entity, category, scope, freshness) and, where no claim exists, from signals — labelled as signals, which carry no epistemic status — never from model memory: an answer with no retrieval is non-conformant even when correct. Surfaces staleness inline ('as of 2026-06, now stale'), labels inferred and hypothesis content, says 'we have no evidence on that' when the store is silent and proposes a scoped research run. Usage: 'intel-ask "<question>" [--keep]' — --keep writes intel/answers/YYYY-MM-DD-<slug>.md with every citation and logs intel.question.answered. Trigger on 'how does X price enterprise', 'who is strongest in <segment>', 'which competitor shows up most in our losses', 'what changed with X this quarter', 'how do I position against X to a CIO', or any question about a tracked entity.

Every answer is a retrieval with citations. The model's own knowledge of a competitor is
not evidence; it is the thing this skill exists to replace. Spec: `docs/INTEL-CI-SPEC.md`
§5.5, OCI v0.1 §7.7.

## Method

1. **Resolve the subject(s)** to intel entities (name, alias, id). Unknown entity → say so
   and offer `/intel-onboarding seed` or `/intel-harvester entity`.
2. **Retrieve claims** via `project-state`: by entity, category (from the question — pricing,
   integration, customer…), scope (segment / geography / persona when the question names
   one), then derive freshness from `half_lives_days`. Prefer fresh over aging over stale;
   prefer higher confidence; never drop a stale claim silently — cite it with its date and
   the word *stale*.
3. **Fall back to signals** only where no claim covers the question; label them *(signal —
   no epistemic status)* and offer to lift them into claims.
4. **Compose** the answer from what was retrieved: verified facts in the register of fact;
   `reported` as "X reports…"; `inferred` / `hypothesis` with "likely", "appears", or the
   explicit label; `unknown` as *we have no evidence on that*.
5. **Conflicts surface**: a contested category is answered as contested, both claims dated.
6. **Offer the gap as an action**: an unanswerable or thin question proposes
   `/intel-harvester competitor <id>` scoped to the category, or `/intel-harvester question`.

## Output

Chat: the answer, then a *Sources* line listing every claim id cited with freshness, then
*Not known* if anything was. With `--keep`: write `intel/answers/YYYY-MM-DD-<slug>.md`
(question · answer · claims · freshness at answer time · what was not known), log
`intel.question.answered` `{path, claims}`.

## Discipline

Retrieval or nothing · staleness inline · unknown is an answer · contested stays contested ·
no side effects — `--keep` writes a file inside the Project and that is all.
