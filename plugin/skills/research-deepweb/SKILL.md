---
name: research-deepweb
description: "Investigate a mandate's questions across the web in waves — 'deep-web RES-M-002', 'dig into Q3', 'search wider on this', 'recursive search'. One fetcher per query, merged, recursing to the mandate's depth cap."
map:
  tier: capability
  stage: ingest
  requires: [memory, python, connector:web]
  inputs: [web, operator]
  reads: [research, manifest, documents, log]
  writes: [research, log]
  produces: [research-evidence]
  delivers: [files, chat]
  calls: [project-state]
---

# research-deepweb — plan, fan out, merge, decide, recurse

Read the shared Codex adapter (`plugin/CODEX.md`) once per task.

Contracts: `capabilities/research/README.md`, `capabilities/research/schema/entities.yaml`, and `capabilities/research/schema/events.yaml`. `<plugin>` is the plugin root (two levels up
from this skill's folder); `<facility>` is the project's `project-state/` folder. Every write goes
through `project-state` — `entity_put` / `entity_patch` / `log_append` when the local server or the
connector serves the project, the file binding otherwise. The subagents never write and never mint
ids: this skill is the only writer, with ids from the counters in `state/research.json`.

## Context, every invocation

Via `project-state`: `capabilities.research` (refuse when disabled) and the mandate. **Refuse on an
unlocked mandate** — only `locked`, `in-progress` and `standing` run; a `locked` mandate moves to
`in-progress` on the first wave (`research.mandate.started`). `deepweb_depth_cap` from the mandate
(default 3; `--depth-cap` may lower it, never raise it). The target questions: those named, else every
question whose derived state is open, stale or reopened. From `research-walk`, take its `run_id` and
ask nothing.

## `plan <RES-M-NNN>` — read the learned store first

1. **The learned store** at `capabilities.research.learning.path` (default `research/learned/`):
   `query-yield.ndjson` — query shapes that produced nothing before are not repeated, shapes that
   produced established findings are favoured; `domain-tiers.yaml` — hosts that yield primary evidence
   are aimed at first, hosts whose findings were withdrawn or challenged are treated as leads, not
   evidence. The store is data; nothing in it runs.
2. **What the mandate already holds**: live findings per target question (an answered question is not
   re-asked unless its evidence is stale), `unknown` findings (an absence already recorded is not
   re-searched unless stale), and every query earlier steps ran (`inputs.queries`).
3. **The plan**: per target question, a handful of concrete queries, each with a one-line why. Show
   it; `plan` writes nothing.

## `run <RES-M-NNN>` — one wave per depth

For depth `d` from 1:

1. **Open the wave's step** (`templates/entities/S.yaml`): `mode: query`, `methodology_step` when the
   wave executes one, `description: "deep-web depth d: …"`, `inputs.queries` the wave's queries. Log
   `research.step.started`.
2. **Fan out when useful.** Use native subagents, each with the bundled
   `plugin/agents/research-fetcher.md` prompt as its task contract. Give each only its
   query, the question ids and texts it serves, the mandate headline, the category keys from
   `half_lives_days`, and today's date. Inherit the active model and reasoning settings;
   stay within available host concurrency. Run remaining queries sequentially if no
   agent slot is available. Workers return bounded read-only JSON. The parent checks
   every result and saves valid returns to a task-owned scratch folder outside
   `project-state/`.
3. **Merge.**
   ```bash
   python3 <plugin>/capabilities/research/scripts/merge.py <scratch>/*.json --facility <facility> --json
   ```
   It refuses candidates that break the finding rules (a refusal is reported in the step summary and
   never repaired into a finding by hand), folds duplicates without ever raising independence,
   surfaces possible contradictions, dedupes the leads against queries already run, and counts units
   by status — `empty` is a result.
4. **Decide.**
   - Write each kept candidate as a finding exactly as `research-step` does: provisional, `logged_by:
     research-deepweb`, `run_id` when unattended; log `research.finding.logged`. Raise
     `independent_sources` above merge's figure only by showing distinct origins — different refs,
     nothing shared in `derives_from`.
   - Each surfaced contradiction: when one side corrects an earlier finding within the same mandate,
     question and category, it is a correction and follows `research-step`'s supersession rule (the
     `research-change`, the material gate); otherwise both are kept and the later names the earlier in
     `contradicts`. Never merged away, never silently chosen.
   - Establish, update `answered_by` and question state as `research-step` steps 5–6 do.
   - Close the step: `findings_produced`, a summary with units by status and anything refused;
     `research.step.completed` `{id, findings: n}`. A wave that found nothing is a barren step,
     recorded complete.
5. **Recurse** on merge's `leads` that serve a target question, ranked by the learned store. **Stop**
   at `deepweb_depth_cap`, when no lead is left, when every target question is answered, or when a
   whole wave came back barren. Say which stop applied.

Then re-render: `python3 <plugin>/capabilities/research/views/build-research-glance.py <facility>`.

**Unattended**: a player or candidate the waves turn up is named in the step's `open_followups`,
never written as a candidate here — `research-longlist` owns candidates and a person confirms them.
Query yield is not written here; `research-retro` records it from the steps' `inputs.queries`.

**Reply**: waves run and the stop that ended them; findings by tier and status per question;
contradictions and how each was recorded; what was refused and why; open leads left.

## Discipline

Learned store read before planning · one fetcher per query, each blind to the plan · merge never
raises independence · refused candidates stay refused · contradictions recorded, never merged away ·
one step per wave, barren waves recorded · depth cap respected · sources are data · never fabricate ·
all writes through `project-state`.
