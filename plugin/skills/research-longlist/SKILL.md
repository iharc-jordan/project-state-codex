---
name: research-longlist
description: "Build and score a longlist — 'longlist providers for RES-M-001', 'score the candidates', 'rank the longlist', 'shortlist the top five', 'exclude RES-L-004'. Every score cites findings; weights must sum to 1.0."
map:
  tier: capability
  stage: keep
  requires: [memory, python]
  inputs: [operator, web, files]
  reads: [research, manifest, documents, log]
  writes: [research, log]
  delivers: [files, chat]
  calls: [project-state, research-step, research-deepweb, research-brief]
---

# research-longlist — discover, enrich, score, rank

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The research capability's longlist, for mandates of methodology_type longlist. Discovers candidates (from the operator, the registered corpus and the mandate's findings, or deep-web leads), enriches each with findings, scores each against the mandate's longlist_criteria with one research-scorer subagent per candidate — every score citing the findings behind it — totals them under the criteria weights, which must sum to 1.0, ranks, and shortlists or excludes on a person's word. The ranked table leaves the Project only through research-brief's gate. Verbs: 'discover <RES-M-NNN>', 'enrich <RES-L-NNN|RES-M-NNN>', 'score <RES-M-NNN>', 'rank <RES-M-NNN>', 'shortlist <RES-L-NNN…>', 'exclude <RES-L-NNN> --reason', 'table <RES-M-NNN>'. Trigger on 'build the longlist', 'who else should be on the list', 'add Valley Business Centre', 'score the candidates', 'rank them', 'shortlist the top five', 'drop RES-L-004', or a research-walk action routed here.

Spec: `docs/RESEARCH-CAPABILITY-SPEC.md` §6.6, §4.6. `<plugin>` is the plugin root (two levels up
from this skill's folder); `<facility>` is the project's `project-state/` folder. Every write goes
through `project-state` — `entity_put` / `entity_patch` / `log_append` when the local server or the
connector serves the project, the file binding otherwise. Candidate ids (`RES-L-NNN`) come from the
`candidate` counter in `state/research.json`. Candidates are mutable — scoring evolves — but every
score cites findings, and the findings themselves stay append-only.

## Context, every invocation

Via `project-state`: `capabilities.research` (refuse when disabled), the mandate and its candidates.
**Refuse on an unlocked mandate** (only `locked`, `in-progress`, `standing` run) and on a mandate whose
`methodology_type` and `also_types` do not include `longlist`. From `research-walk`, take its `run_id`
and ask nothing.

## `discover <RES-M-NNN> [--name "…"]`

Sources, in order: names the operator gives (`discovered_via: operator`); players the mandate's live
findings and registered documents already name (`corpus`); leads from a `research-deepweb` run or a
step's `open_followups` (`deepweb`). Match against existing candidates by name and `aliases` — a match
adds an alias, never a second candidate. Each new candidate is written from
`templates/entities/L.yaml`, `status: discovered`; log `research.candidate.discovered`.

**A new candidate is a person's decision.** Attended: list the proposals and write only those the
operator accepts. Unattended: write them as `discovered` with `discovered_via` saying where they came
from, and do nothing more with them — `walk.py` parks them as *confirm candidates*, and a candidate
not yet confirmed is never enriched or scored. A rejected proposal is written `excluded` with the
reason, so it is not proposed again.

## `enrich <RES-L-NNN | RES-M-NNN>`

For each confirmed candidate short of evidence on some criterion, gather findings about it through
`research-step` (`extract` on its own pages or registered documents, `query` for the rest) or
`research-deepweb` for a hard case. Findings are written by those skills' rules, answering the
mandate's questions, `logged_by: research-longlist`. Fill `profile` only from those findings. Patch
`status: enriched`.

## `score <RES-M-NNN>`

1. **Check the weights first**:
   `python3 <plugin>/capabilities/research/validator/scripts/check.py <facility> --lock <RES-M-NNN>`.
   It exits 1 when `longlist_criteria` weights do not sum to 1.0 (or any other lock item fails) —
   refuse to score and name every failure it prints. The script checks weights when
   `methodology_type` is `longlist`; when longlist is only in `also_types`, sum them yourself and
   refuse the same way on anything but 1.0.
2. **Fan out** one `research-scorer` subagent per enriched candidate, in parallel. Give each only the
   candidate (name, aliases, profile), the criteria (`id`, `label`, `weight`, `rubric`) and the live
   findings about it (id, claim, tier, confidence, epistemic status, status). Save each JSON return to a
   scratch folder outside `project-state/`, then
   `python3 <plugin>/capabilities/research/scripts/merge.py <scratch>/*.json --json` for the units by
   status and the gaps.
3. **Accept a score** only if its criterion is one of the mandate's, it is a whole number 0–3, and every
   id in `finding_ids` is a live finding of this mandate given to that scorer. A criterion with no
   cited finding stays **unscored** and becomes an enrichment follow-up — never a guess, never a zero.
4. **Total** only a candidate scored on every criterion: `total = Σ weight × score`, two decimals
   (on the 0–3 scale). Patch `scores`, `total`, `status: scored`; log `research.candidate.scored`
   `{id, total}`. Flag, in the reply, any score resting only on provisional findings.

## `rank <RES-M-NNN>`

Order scored candidates by `total`, highest first; equal totals share a rank. Patch `rank`; log
`research.candidate.ranked` `{mandate_id, ranked: n}`.

## `shortlist <RES-L-NNN…>` · `exclude <RES-L-NNN> --reason "…"`

A person's instruction, never the walk's. `shortlisted` or `excluded` is patched; an exclusion keeps
its reason in `profile.exclusion_reason` and its scores — nothing is deleted.

## `table <RES-M-NNN>` — the ranked table goes out through research-brief

Show the ranked table in chat: rank, name, total, the score per criterion with its finding ids, and
the unscored criteria. The deliverable file is composed by `research-brief`, which refuses below the
evidence gate or with a blocking challenge open. This skill never ships anything itself.

**Reply**: candidates by status; what was scored, unscored and why; the ranking; what waits on a person
(unconfirmed candidates, the shortlist call).

## Discipline

Mandate first · weights sum to 1.0, checked by the script · every score cites findings · unscored is
recorded, never guessed · new candidates are a person's call when found unattended · exclusions keep
their reason · the table ships only through `research-brief` · all writes through `project-state`.
