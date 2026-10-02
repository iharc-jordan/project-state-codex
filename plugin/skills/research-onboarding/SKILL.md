---
name: research-onboarding
description: "Set up the research capability on a project — 'enable research', 'set up research here', 'start a research project', 'migrate our .research-state'. Enables, scaffolds, drafts 1–3 mandates to argue with; never locks."
map:
  tier: capability
  stage: ingest
  requires: [memory, python]
  inputs: [operator, files]
  reads: [manifest, documents, research]
  writes: [manifest, research, documents, people, lessons, log]
  delivers: [chat]
  calls: [project-state, research-mandate]
---

# research-onboarding — the enable flow

Read the shared Codex adapter (`plugin/CODEX.md`) once per task.

Make research active for one project and put a first question on the table. There is **no
REQUIRED field**: intel needs a `focus` because a harvest without a lens produces confident
irrelevance; research's lens is the mandate, and an unlocked mandate cannot run. Contracts: `capabilities/research/README.md`, `capabilities/research/schema/entities.yaml`, and `capabilities/research/schema/events.yaml`. `<plugin>` is the plugin root (two levels up
from `capabilities/research/`; within the installed plugin). `<facility>` is the project's
`project-state/` folder.

Every write goes through `project-state` — `entity_put` / `entity_patch` / `log_append` when the
local server or the connector serves the project, else the file binding.

## Step 1 — Preconditions

- Locate the host `project-state/` (walk up from cwd). No facility → point at `project-intake` /
  `project-scaffolder` and stop.
- `capabilities.research` already enabled → a second enable refuses (spec §14). Report status
  instead: mandates by status, and whether the digest's `research.not-initialized` still fires;
  offer Step 4 only.
- **Work type.** No primary `axis: work` pack (`project.kind` empty) → recommend the
  `work-research` pack: it gives the project its phase ladder (questions → method → data
  collection → analysis → findings), which this capability's evidence machinery assumes. Adding
  it is the operator's call, made through project-state. Do not require it.

## Step 2 — Gather (one pass, defaults shown)

Show `templates/manifest-block.yaml` in words and ask only what the operator wants to change:
`defaults.primary_source_min_ratio` (0.5), `deliverable_format` (html), `citation_style`
(inline) · `half_lives_days` — the §4.9 table; record an override only with a reason ("our
pricing moves quarterly → 60") · `walk` budget, `max_actions`, `barren_run` (3) ·
`learning.path` (`research/learned`; point it at a shared path to carry lessons across
projects) and `share_calibration` · `crossings.intel` (`auto` = promotion allowed when intel is
enabled here). The half-life table is always written out in full, never implied.

## Step 3 — Enable

Call the memory layer: `project-state enable research` with the gathered config. That verb —
not this skill — takes the manifest lock, writes the `capabilities.research` block stamped with
the plugin `version:`, scaffolds `research/{mandates,steps,findings,challenges,candidates,
changes,runs,topics,reports,learned}` with `.gitkeep`s, seeds `research/agenda.yaml` from
`templates/agenda.yaml` and `state/research.json` (counters at zero, no walk marker), arms the
`research-default` matrix entries, and logs `capability.enabled`. Then run
`python3 <plugin>/capabilities/research/validator/scripts/check.py <facility>` — it must be clean.

## Step 4 — Draft one to three mandates to argue with

Read the brief: the manifest's description and objectives, registered documents, and what sits
in `documents/inbox/`. Propose **one to three** candidate mandates in chat, each with a headline,
two to five structured questions, a `methodology_type` (narrative · longlist · comparative ·
deep-web-investigation), a first methodology, and which registered documents look relevant.
Say what is weak about each — the argument is the point. Standing concerns (a theme to watch,
not a question to close) are proposed as bounded mandates the operator can later make standing,
and as P0–P3 lines for `research/agenda.yaml`.

For each one the operator keeps, hand over to `research-mandate propose` (status `draft`,
`research.mandate.drafted`), then show what stands between it and a lock:
`check.py <facility> --lock RES-M-NNN` — every failure it names is a question for the operator.
**Never lock.** Locking is a person's decision, taken later with `research-mandate lock`. Write
agenda lines only on confirmation.

## Step 5 — Report

The enabled block, the drafts written and what each still lacks, and next steps: argue the
drafts into shape (`/research-mandate iterate`), lock one, drop source documents into
`documents/inbox/` for `/research-ingest`. The digest now carries the research checks — there is
no separate research briefing. Render the first At a glance page so the app shows this project,
not the fixture sample:
`python3 <plugin>/capabilities/research/views/build-research-glance.py <facility>`.

## `migrate <.research-state folder>` — from the standalone deep-research facility

A project that used the retired deep-research plugin moves in with the migration script (spec
§11.2). Research must be enabled first (Steps 1–3). **Plan first, always**:

```bash
python3 <plugin>/capabilities/research/scripts/migrate_research_state.py <old .research-state> <facility>
```

Show the plan: the id map (`MND→RES-M`, `STEP→RES-S`, `FND→RES-F`, `CHL→RES-C`, `CND→RES-L`)
that lands in `research/migration-map.yaml`; per-mandate directories flattened; `SRC` records to
be registered through the curator with their relevance moved onto each mandate's
`source_relevance`; `CON` → `people/`, `PUB` → `publications/`, `LESSON` → `lessons-learned/`;
old `activity.ndjson` events renamed to `research.*` and appended to the host log; counters to
`state/research.json`; the learned store moved. Migrated findings arrive `epistemic_status:
reported` (`hypothesis` for speculative tier), `status: established`, with `migrated_from:`.
History lost to in-place edits in the old facility cannot be recovered; the plan says so, and so
do you — never invent a supersession chain. Then, on the operator's word:

```bash
python3 <plugin>/capabilities/research/scripts/migrate_research_state.py <old .research-state> <facility> --write --actor <operator email>
```

The old tree is left in place. Afterwards: `check.py <facility>` clean; `check.py --gate` on each
mandate — a blocking challenge that stopped composition before must still stop it; render the
glance. Report the old folder and any separately configured legacy host trigger
for the operator to review. The `research-default` matrix carries project
cadence; migration does not install a Codex automation.

## Discipline

No REQUIRED field, no guessing one · drafts to argue with, never a lock · recommend
`work-research`, never require it · migration plans before it writes and never touches the old
tree · lost history is said, not reconstructed · all writes through `project-state`.
