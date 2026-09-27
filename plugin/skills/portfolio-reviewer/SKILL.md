---
name: portfolio-reviewer
description: "Answer questions across a portfolio of projects from its compiled index, with citations — 'how is the portfolio doing', 'which projects are at risk', 'summarise our portfolio'. Never from memory."
map:
  tier: capability
  stage: generate
  reads: [portfolio, people, manifest]
  writes: [portfolio, state, log]
  calls: [project-state]
  produces: [portfolio-review]
  delivers: [files, chat]
---

# portfolio-reviewer — query, synthesize, keep

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Query and synthesize across a portfolio's member projects from the compiled index and the member files, never from memory. `query "<question>"` reads the relevant index files first, drills into the cited member files second, and answers with evidence by member and path plus an explicit 'what this answer does not know'; answers worth citing are kept under portfolio/answers/. `synthesize "<theme>"` reads a theme across members and writes one append-only finding with evidence, asks as questions, and lineage — including emerging projects clustered from items members' own triage dismissed, which land in the hopper when acknowledged. Manages the findings ledger and the one human-gated crossing: `promote <PF-F-id> --to <member>` drops a proposal into that member's documents/inbox/. Trigger on 'ask the portfolio', 'who is over-committed', 'what do the members say about X', 'which projects touch Y', 'synthesize', 'promote this finding'. Never re-plans a member; never promotes unattended.

The portfolio's reading of its members, answered from files and stated with evidence.
Observes and asks; never re-plans.

## Verbs

- `query "<question>" [--member <id>] [--keep | --no-keep]` — answer from the index, then
  member files; keep per `answers.keep`.
- `synthesize "<theme or question>" [--members a,b]` — read across members; write a finding.
- `findings [list | ack <id> | dismiss <id> --reason … | resolve <id>]` — the ledger.
- `promote <PF-F-id> --to <member-id> [--as risk|decision|milestone-note]` — the crossing.

## Context, every invocation

`capabilities.portfolio` (`answers.keep`), `state/portfolio.json`, `portfolio/registry.yaml`,
and `portfolio/index/` as compiled at the last collect. If the index is older than the newest
snapshot, say so and offer to run the collector first. Members never collected are named as
such in every answer, never silently omitted.

## query

1. **Choose the index files** the question implies — people and deadlines for load; risks,
   decisions, milestones for status; tags and documents for themes; activity for "what
   changed". Say which were read.
2. **Read them**, then **drill** into the member files the matching rows cite. Never answer
   from a row alone when the file says more; never answer beyond what the files say.
3. **Answer** in this order: the short answer in one sentence; the evidence, each line with
   member and path; a figure when the question implies one (a person-over-time row for load,
   a member-by-kind grid for coverage) following the house encodings; **what this answer does
   not know** — the field, the member, or the declaration that is missing.
4. **Keep** per `answers.keep` (`ask` → offer; `always`; `never`): write
   `portfolio/answers/<date>-<slug>.md` from `templates/answer.md` with question, files read,
   files drilled, basis; log `portfolio.answer.kept`.

## synthesize

Read a theme across members through the index — a tag shared by several members is the usual
starting point — and write **one** finding (`templates/entities/finding.yaml`):
`question`, `summary` (what the members collectively say and what nobody is doing about it),
`evidence` rows with member, path, ref, note, `suggested` asks phrased as questions to a
member's people, `basis`. Counter via `project-state`; log `portfolio.finding.logged`.

Reference flavours: a shared theme nobody owns as one · a decision in one member that answers
a risk in another · a person's load across members · **emerging projects** — items members'
own triage dismissed as out of scope, clustered across members by contact, thread or keyword
(reference rule: ≥5 items, ≥2 members, ≥3 weeks). Acknowledging an `emerging-project` writes a
`proposed` member row with `source_row: finding:<id>` and adds it to the finding's `became`;
admitting it is `project-intake`'s job, seeded from the already-classified documents. When
the intel capability is enabled on this Project, a cluster that is ecosystem news rather than
project work is offered "send to intel" instead.

Never fabricate: no evidence rows, no finding. Never edit a finding's content after creation;
lifecycle fields only.

## promote — the crossing

1. Render `templates/inbox-proposal.md` with the finding, its evidence, and a proposed entity
   in the member's vocabulary.
2. Write it to `<member location>/documents/inbox/portfolio-proposal-<PF-F-id>.md`. **This is
   the only write toward a member.** Nothing else in that member is touched.
3. Set `status: promoted`; log `portfolio.finding.promoted` with the path.
4. Acceptance is the member's: an entity recorded with `source: portfolio:<id>` puts the
   `became` edge on the finding at the next collect. Never promote unattended; never re-drop a
   finding already promoted to the same member.

## Discipline

- The index first, the member file second, memory never.
- Label the basis honestly; inferred is never presented as declared.
- Asks are questions to a member's people, answered inside the member.
- All writes through `project-state`; this skill takes no locks itself.
