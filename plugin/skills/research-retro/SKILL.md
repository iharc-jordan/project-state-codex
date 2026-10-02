---
name: research-retro
description: "Learn from a finished research mandate — 'run the retro', 'research retrospective', 'what did RES-M-003 teach us'. Records query yield, domain tiers and calibration as data; proposes lessons for a person to keep."
map:
  tier: capability
  stage: generate
  requires: [memory, python]
  inputs: [operator]
  reads: [research, manifest, lessons]
  writes: [research, lessons, log]
  delivers: [chat, files]
  calls: [project-state]
---

# research-retro — what the research did, as data

Read the shared Codex adapter (`plugin/CODEX.md`) once per task.

A mandate that finishes without a retrospective teaches the next one nothing. The retro turns the
mandate's record into **data the next mandate reads** — never into a skill, a script, a prompt or
a rule. Contracts: `capabilities/research/README.md`, `capabilities/research/schema/entities.yaml`, and `capabilities/research/schema/events.yaml`.
`<plugin>` is the plugin root (two levels up from `capabilities/research/`); `<facility>` is the
project's `project-state/` folder. Every write goes through `project-state` — `entity_put` /
`entity_patch` / `log_append` when the local server or the connector serves the project, else
the file binding.

## Context, every invocation

Via `project-state`: `capabilities.research` (refuse when disabled), `learning.path` (default
`research/learned`) and `share_calibration`, the mandate, and whether the log already holds a
`research.retro.recorded` for it. The retro is for a finished mandate — `complete`,
`closed-negative` or `killed`. On a `standing` or `in-progress` mandate it runs only on request
and is labelled **interim**. Already recorded → say when, and re-run only if asked.

## `research-retro RES-M-NNN`

1. **Compute** — the script does the arithmetic; the skill does not recount:
   ```bash
   python3 <plugin>/capabilities/research/scripts/learn.py <facility> RES-M-NNN --json
   ```
   It returns the steps and the productive ones, the **barren steps** (complete, no findings —
   activity that produced nothing), `query_yield` rows, `domain_tiers` per host, `calibration`
   per confidence level (stated · held · fell), challenges by kind and outcome, and candidate
   `lessons`, each tied to its evidence.
2. **Write the learned records** under `learning.path`:
   - `query-yield.ndjson` — append each `query_yield` row. Append-only; a row already there (same
     `mandate_id`, `step_id`, `query`) is not written twice, so a re-run adds nothing.
   - `domain-tiers.yaml` — per host, this mandate's counts by tier and how many were established,
     withdrawn or challenged, under the host's entry for `RES-M-NNN`; a re-run replaces this
     mandate's entry and leaves other mandates' untouched. It is a prior for the next mandate's
     source choice, **not a verdict** on the host.
   - `calibration.ndjson` — append each calibration row with `recorded_at`; rows identical to this
     mandate's last recorded ones are skipped. When `share_calibration` is false and
     `learning.path` points outside the project, calibration is written to the project's own
     `research/learned/` instead (choice where the spec is silent).

   `research-deepweb` reads these before planning — as data. Nothing here generates or edits a
   skill, a script, a prompt or a validator rule.
3. **Lessons.** Show the script's candidates, each with its evidence (step ids, hosts, challenge
   kinds, the calibration line). You may add a lesson from reading the record only if it cites
   evidence the same way. The operator keeps, rewords or drops each. Each kept lesson becomes
   `lessons-learned/YYYY-MM-DD-<slug>.md` in the core lessons format (title, body, `tags:
   [research]`, severity, `recommended_action`, the mandate and evidence ids in the frontmatter),
   and the core `lesson.captured` is logged for it.
4. **Record** — log `research.retro.recorded` `{mandate, interim, steps, productive, barren,
   query_rows, hosts, calibration_levels, lessons_kept, lessons_proposed, learning_path}`. This
   clears the digest's `research.retro-missing`.

**Unattended** (the walk's retrospective action): steps 1, 2 and 4 run; no lesson is kept
without a person — the candidates go into the event as `lessons_proposed` and wait for
`research-retro lessons RES-M-NNN`.

**Reply**: *k of n steps produced evidence*; the barren steps by mode; the queries that yielded
and those that did not; hosts that fed findings that did not hold; calibration in one line per
level (*high: 3 of 3 held*); the lessons kept. When the record is thin, say so rather than
stretching it into a lesson.

## `research-retro lessons RES-M-NNN`

Read the `lessons_proposed` of the last `research.retro.recorded` for the mandate and run step 3
on them. Log a new `research.retro.recorded` with the counts; the earlier entry is never
rewritten.

## Discipline

Learning is data, never code · the script counts, the skill reads · every lesson cites its
evidence · a person keeps lessons, the walk only proposes them · learned files are append-only
where they are logs and scoped per mandate where they are tables · a domain tier is a prior, not a
verdict · all writes through `project-state`.
