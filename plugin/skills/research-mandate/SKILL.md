---
name: research-mandate
description: "Draft, lock or close a research question — 'draft a mandate', 'lock RES-M-002', 'kill this mandate', 'close it negative', 'make it standing', 'promote RES-F-017 to intel'. Locking runs the checklist; a person decides."
map:
  tier: capability
  stage: control
  requires: [memory, python]
  inputs: [operator, files]
  reads: [research, manifest, documents, intel]
  writes: [research, documents, log]
  delivers: [chat, files]
  calls: [project-state, intel-ingest]
---

# research-mandate — the question, and the contract for answering it

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The research capability's mandate lifecycle (spec §4.2, §4.8, §6.3, §6.12). A mandate is the first deliverable: structured questions, a methodology, a deliverable, success criteria and a corpus link, argued into shape as a draft and then locked. Verbs: 'propose', 'iterate <RES-M>', 'lock <RES-M>' (runs the mechanical checklist and refuses on failure), 'kill <RES-M> --reason', 'close-negative <RES-M>' (a null_result_statement is required), 'make-standing <RES-M>', 'complete <RES-M>', 'promote <RES-F> --to intel' (a proposal into the house inbox; never a write into intel). Locking, killing, reopen-versus-close-negative and marking complete are a person's decisions. Trigger on 'draft a research mandate', 'what are we actually asking', 'lock the mandate', 'change the questions', 'stop this research', 'we found nothing — close it', 'keep watching this', 'we're done', 'send this finding to intel', or the digest's research.draft-drifting and walk-gated lock / reopen / complete items.

No step runs against an unlocked mandate. The checklist is a script; the decision is a person's.
`<plugin>` is the plugin root (two levels up from `capabilities/research/`); `<facility>` is the
project's `project-state/` folder. Every write goes through `project-state` — `entity_put` /
`entity_patch` / `log_append` when the local server or the connector serves the project, else the
file binding.

## Context, every invocation

Via `project-state`: `capabilities.research` (refuse when disabled — point at
`research-onboarding`), its `defaults`, `state/research.json` counters, the mandate, and for
`promote` the finding. A person's decision is taken from the operator in this conversation; an
unattended walk never reaches these verbs — it parks them (`research.walk.gated`).

## `propose ["<headline>"] [--type narrative|longlist|comparative|deep-web-investigation]`

Next id from counter `mandate`; fill `templates/entities/M.yaml`: `headline`; `questions` as
`{id: Q1…, text, state: open, answered_by: []}`, each answerable or provably unanswerable;
`methodology` of **≥ 3 concrete steps**; `deliverable` (`format` from `defaults.deliverable_format`,
`structure`, `audience`, `citation_style`); testable `success_criteria`;
`primary_source_min_ratio` from defaults; for longlist, `longlist_criteria` with rubrics and
weights summing to 1.0; for comparative, ≥ 2 `comparison_subjects` and typed
`comparative_dimensions`; `source_relevance` — registered documents scored 0–3 — or
`corpus_independent: true`, stated as a choice. `status: draft`, `iteration: 1`, `owner`. Log
`research.mandate.drafted`. Then run the lock checklist and show every gap as a question.

## `iterate RES-M-NNN`

- **Draft**: edit in place, `iteration` + 1, log `research.mandate.iterated`. Two iterations
  without a lock raises `research.draft-drifting` — say which gap keeps it unlocked.
- **Locked or later**: questions and methodology are frozen; changing them reopens the mandate as
  a new iteration — `status: draft`, `iteration` + 1, re-lock required (a standing mandate is made
  standing again after the lock). **Choice where the spec is silent:** a question findings
  answer is never deleted or renumbered — it is set `dropped`, and new questions take new ids,
  so every finding's `answers` still resolves. This is also the *reopen* side of
  reopen-versus-close-negative.

## `lock RES-M-NNN`

```bash
python3 <plugin>/capabilities/research/validator/scripts/check.py <facility> --lock RES-M-NNN
```

Exit 1 → **refuse**, quoting every failure it names (two methodology steps and empty success
criteria are two failures, both reported), and offer `iterate`. Exit 0 → show the headline,
questions, method and deliverable, and ask the operator to lock. On their yes: `status: locked`,
`locked_at`, `locked_iteration: <iteration>`; log `research.mandate.locked` with the actor.
Locking is not starting: `research.mandate.started` comes from the first step.

## `kill RES-M-NNN --reason "<why>"`

A person's decision. `kill_reason` is required; `status: killed`, `killed_at`; log
`research.mandate.killed`. Steps, findings and challenges stay — killed is a status, not a
deletion.

## `close-negative RES-M-NNN`

A person's decision, usually the gate the walk parks after `walk.barren_run` barren steps with
questions open. Lay out both sides: reopen (`iterate`) or close. To close, compose
`null_result_statement` — what was searched, where, over what period, and what was not found —
from the mandate's barren steps and `unknown` findings, cited; the operator confirms the words.
`status: closed-negative`, `completed_at`; log `research.mandate.closed-negative`. The validator
refuses the status without the statement. An established absence is a result.

## `make-standing RES-M-NNN --cadence nightly|weekly --audience "<who reads the delta>"`

From `locked` or `in-progress`, on the operator's word: `status: standing`, `standing: {cadence,
delta_audience}`; log `research.mandate.made-standing`. This does not schedule: the
`research-default` pack's nightly walk and weekly delta carry the cadence through the matrix
(`project-automator`). A standing mandate never completes; it is stopped by `kill`.

## `complete RES-M-NNN`

Bounded mandates only; a person's decision. Show each question's derived state (answered ·
aging · stale · open · dropped), `check.py <facility> --gate RES-M-NNN`, open blocking
challenges, and whether a deliverable shipped. **Refuse while a blocking challenge is open.**
Open questions or a primary share below the gate are named, and completing past them needs the
operator to say so. `status: complete`, `completed_at`; log `research.mandate.completed`; offer
`/research-retro`.

## `promote RES-F-NNN --to intel [--entity INT-E-NNN|"name"]`

When a finding is about a player intel tracks (spec §6.12). Intel is the only target.

```bash
python3 <plugin>/capabilities/research/scripts/promote.py <facility> RES-F-NNN [--entity …]
```

Exit 1 → relay the refusal (intel not enabled, `crossings.intel: off`, the finding superseded,
withdrawn or still provisional — only established evidence crosses). Otherwise show the proposal
it prints; on the operator's yes, write it to `documents/inbox/research-promotion-<RES-F id>.md`
— **the only write a promotion makes** — and log `research.promotion.proposed` `{finding, target:
intel, path}`. Intel's schema is never touched. `intel-ingest` drains the inbox into an intel
claim that cites the finding. **Once it has**, record the lineage: `entity_patch` the finding's
`became` (a lifecycle field — the only change a finding permits) with `{capability: intel, id:
INT-C-NNN, at: <date>}` (shape chosen here; the spec fixes only the edge).

## Discipline

Mandate first · the checklist is `check.py`, never prose · locking, killing, reopen-or-close and
complete are a person's · locked questions change only by a new iteration · nothing is deleted:
killed, dropped and closed-negative are statuses · promotion is inbox-only and gated · all writes
through `project-state`.
