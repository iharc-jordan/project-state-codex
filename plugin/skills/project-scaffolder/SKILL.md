---
name: project-scaffolder
description: "Create a new project-state/ facility — 'set up a new project', 'scaffold a project', 'init project-state here'. Also seed-pack / adopt-seeds for a project's starting milestones and risks."
map:
  tier: P0
  stage: ingest
  requires: [memory, python, local-fs]
  inputs: [operator]
  writes: [manifest, phases, reporting-matrix, milestones, risks, log]
---

# Project Scaffolder

> **When to use.**
>
> One-shot initializer for a new project-state/ facility. Use this skill when starting a brand-new project of any kind — software, campaign, event, operating cycle, grant, client engagement — scaffolds the directory tree, manifest, phase manifests, logs, README/SCHEMA/CONCURRENCY/SKILLS docs — and when asked to 'set up a new project', 'create a new project-state', 'scaffold a project', 'initialize project-state', 'start a new funded project', 'bootstrap a grant project', 'new consortium project', 'create the state folder for [project]', 'init project-state in this folder'. Asks what kind of work it is, who hears about it and how the work moves, then seeds the manifest, reporting matrix and draft milestones/risks from the chosen packs (seed-pack, adopt-seeds). Follow-up work (milestone seeding from proposal, people seeding from MPA) is handed off to the other project-* skills.

## Purpose

Stand up a fresh `project-state/` in a new working directory. Ensures the facility starts correctly-shaped so the other `project-*` skills can operate.

Used once per project at kickoff. The experience runs as a 6-step wizard with a post-confirm build step.

## Trigger phrases

- "set up a new project"
- "scaffold a project"
- "initialize project-state" / "init project-state"
- "create a new project-state"
- "start a new funded project" / "bootstrap a grant project"
- "new consortium project"

---

## Presentation in Codex

Use a concise Markdown progress line, tables for choices, and Mermaid only when it clarifies the selected preset. Prefill answers from available project evidence. A direct setup request authorizes the ordinary local scaffold once required choices and paths are resolved. Ask only for material missing inputs.

## Wizard Steps

Resolve the inputs in Steps 1–6 from the request and available evidence. Present the resulting configuration and continue when the user has already requested scaffolding and all required choices are settled. Ask only about a material missing or conflicting input; do not force a response between steps.

---

### Step 1: What kind of project, and who hears about it

**Purpose:** Answer two of the three project-type questions (defined below): the
**work type** (one primary `axis: work` pack) and **accountability** (zero or more
`axis: accountability` packs). The third — rhythm — is Step 2's preset. Packs seed the reporting matrix,
the draft milestones and risks, and configure the profile-driven skills.

**Build the cards from pack manifests — never from a table in this file.** Read every
`packs/*/manifest.yaml` and keep those with `picker.listed: true`. Group by `pack.axis`; show
`picker.label` as the card title, `picker.blurb` beneath it and `pack.maturity` as the badge. Packs with
`picker.listed: false` (e.g. `open-source-community`) appear only under a collapsed **Advanced** group,
marked *thin*. `axis: capability` packs never appear. Every row of `PROJECT-TYPES-SPEC` §2.5 was a front
door keeping its own copy of this list.

**Markdown output** (rows generated from manifests; this is the shape, not the list):
```
── Step 1 of 6: Project type ────────────────────────────────────

What is this project trying to make happen? (pick one)

| # | Work type          | Best for                                              |
|---|--------------------|-------------------------------------------------------|
| 1 | <picker.label>     | <picker.blurb>                                        |
| … |                    |                                                       |

Who needs to hear how it's going? (pick any; ✓ = pre-selected)

| # | Accountability               | Best for                                   | Maturity |
|---|------------------------------|--------------------------------------------|----------|
| a | ✓ <picker.label>             | <picker.blurb>                             | <badge>  |
| … |                              |                                            |          |
| z | Just me                      | No one outside the team                    | —        |

> Type a number and letters (e.g. "3 a c"), or "advanced" for more:
```

Write the choices as `project.kind: <work pack id>` and `project.packs_loaded: [<work pack>,
<accountability packs…>]` — the work pack first.

---

### Step 2: Phase Selection

**Purpose:** Set the starting phase. The phase determines which gate criteria are active and which phase manifests are marked CURRENT.

**`phases.lifecycle` — write only what the pack settles, and never ask here.** Scaffolding is not the
moment to raise a question the operator cannot yet answer; `project-onboarding` Q1.7 asks it properly,
pre-filled from the same pack data.

Read `defaults.lifecycle` from the manifest of each pack selected in Step 1. Then:

- **Any selected pack declares `terminal`** → write `phases.lifecycle: terminal`. Nothing is being
  guessed: the pack is asserting that projects of its kind end, and for grant packs the preset makes
  `continuous` structurally impossible anyway.
- **Packs declare `continuous`, or disagree, or declare nothing** → **leave it unset.** A `continuous`
  pack default is a *suggestion*, and scaffold time is the point of least information — writing it here
  would create `increments/` on a facility nobody has confirmed continues.
- **No pack selected** → leave it unset.

Do not hardcode a pack-to-lifecycle table in this skill. The mapping lives in pack manifests, per the
packs-configure-not-code principle; `FB-003` is what happens when pack knowledge is encoded in a skill
instead. Unset means terminal, is permanently valid, and is never warned about, so leaving it is always
the safe answer — and the post-closeout diagnostic asks at the moment the answer is actually knowable.

Spec: `plugin/skills/project-phase-gate/SKILL.md`

**`phases.preset` — write it, always.** This is the key FB-003 is about: five presets shipped in
`templates/phase-presets/` and nothing ever wrote the manifest key that selects one, so choosing a
ladder meant hand-editing YAML for ten weeks. Resolution order:

1. The intake record's `phases.preset`, when called from `project-onboarding` Q1.9.
2. The **primary work pack's** `defaults.preset` (the pack `project.kind` names). With no work pack
   loaded, an accountability pack's `defaults.preset` pre-fills instead (e.g. `pic-pcais` →
   `grant-default`). Always presented as a confirmation, never written unseen.
3. Otherwise ASK. This is the interactive front door and a one-line question is cheap; a facility with
   no ladder is not.

Never leave it unset. Unlike `phases.lifecycle`, where unset is a permanently valid answer meaning
terminal, an unset preset means there is no phase ladder to be in.

**`automation.timezone` — write it, and never invent it.** `templates/manifest-v2.yaml` has marked
this REQUIRED since it shipped while shipping the value as `~`, and no skill collected it (FB-002).
Resolution order:

1. The intake record's `automation.timezone`, from `project-onboarding` Q1.8.
2. Otherwise ASK for an IANA name. The host machine's zone may be offered as a suggestion to confirm,
   never written unseen — the facility's timezone is a property of the PROJECT, not of whoever ran the
   command, and a project worked on from two machines in two zones would silently reschedule itself.

Do not write `~`, do not default to UTC. `project-automator` now refuses to compile a schedule without
it, because the window above is local time and a guessed zone fires the nightly jobs at the wrong hour
— confidently wrong beats not starting, which is why the refusal is the correct behaviour and this
question is the thing that stops anyone meeting it.

Both keys are ruled in decision `2026-08-21-twelve-rulings-facility-contract`, items 10 and 11.

**`caches` — the heavy-artifacts register; write what was confirmed, never guess.** Resolution order:

1. The intake record's `caches`, from `project-onboarding` Q1.10: entries, `[]` or unset, as given.
2. Otherwise the Step 5 question below, asked only for a project whose code lives beside the facility.
3. Otherwise leave it unset. Unset is valid and never reported.

When the written register has any entry, the facility sits in a git repository, and that repository
does not already ignore `.cache/` (`git check-ignore -q -- .cache/` exits 1), add the line `.cache/` to it, shown in Step 6
before it is written. This is the only file outside `project-state/` besides `.gitattributes` that the
scaffolder touches, and it never touches the tool's own setting: that change belongs to the code's
owner. Reference: `skills/project-state/references/heavy-artifacts.md` (FB-001, issue #47).


**The rhythm question, when nothing settled the preset.** If neither the intake record nor the primary
work pack's `defaults.preset` settles it, ask in plain words (`PROJECT-TYPES-SPEC` §6.1):

| Answer | Preset |
|---|---|
| "In sprints or iterations" | `agile-default` |
| "Through stages, with sign-off between them" | `stage-gate-default` |
| "Toward a fixed date" | `countdown-default` |
| "In a repeating cycle" | `cycle-default` |
| Advanced | `grant-default`, `client-engagement-default`, `waterfall-default`, `open-source-default`, custom |

**`phases.anchor_date` — ask when the preset requires it.** A preset that declares `requires:
[anchor_date]` (`countdown-default`) cannot be written without it: ask for the launch or event date and
write it with the preset. Then ask each `asks:` entry declared by the loaded packs' manifests, writing
each answer to its dotted `key`; skip an optional one the operator leaves blank. Never invent an answer.

**Starting phase — the options are the preset's own phases.** Read `phases:` from
`templates/phase-presets/<preset>.yaml` and offer each phase's `id` and `label`, defaulting to the
first. (This step used to hardcode the grant ladder — LOI / Approval / Planning / Execution — for every
project, whatever its preset.) For `grant-default` keep the old default of `03-planning` when the award
is confirmed.

**Markdown output** (generated from the preset; `countdown-default` shown):
```
── Step 2 of 6: Phase Selection ─────────────────────────────────

Preset: countdown-default (from work-event)     Anchor date: 2027-03-12

| # | Phase                  | Done when                                               |
|---|------------------------|---------------------------------------------------------|
| 1 | 01 — Plan ✓            | Brief approved, date fixed, budget and owners agreed    |
| 2 | 02 — Build-out         | Everything booked, made or confirmed                    |
| 3 | 03 — Final countdown   | Readiness check passed; run of show locked              |

> Type a number [default: 1]:
```

---

### Step 3: Project Identity

**Purpose:** Collect project name, funder, program, PI/PL, and dates. These seed `manifest.yaml`.

**Markdown output:**
Ask only for required values missing from the request, intake record, or project evidence. Group related missing values when that is easier to answer:
```
── Step 3 of 6: Project Identity ────────────────────────────────

I'll ask a few questions about the project. Answer each in turn.

  1. Project short name (used as slug, e.g. atlas):
```
Then after each answer: `Got it. Next:`

---

### Step 4: Consortium & Sharing

**Purpose:** Capture consortium members, the Project Lead organization, and the team sharing model.

**Markdown output:**
```
── Step 4 of 6: Consortium & Sharing ────────────────────────────

  Lead organization:
  Consortium members (org, role, email — one per line, blank to finish):

  Sharing model:
  | # | Model         | Description                                      |
  |---|---------------|--------------------------------------------------|
  | 1 | Git ✓         | project-state/ in a git repo — recommended       |
  | 2 | Shared drive  | Dropbox / GDrive / OneDrive, no git              |
  | 3 | Single user   | Local only                                       |

> Sharing model [default: 1]:
```

---

### Step 5: Surfaces

**Purpose:** Configure which external surfaces the project uses. Surface config is stored in `manifest.yaml:surfaces` and read by `project-notifier`.

**Markdown output:**
```
── Step 5 of 6: Surfaces ────────────────────────────────────────

Which surfaces does the team use? Toggle on/off.

| # | Surface          | Status | What it does                              |
|---|------------------|--------|-------------------------------------------|
| 1 | Slack            | [ ]    | Posts updates to a channel                |
| 2 | Gmail            | [ ]    | Creates drafts (never auto-sends)         |
| 3 | Google Calendar  | [ ]    | Proposes meeting holds                    |
| 4 | scsiwyg blog     | [ ]    | Publishes posts through a review queue    |

> Type numbers to enable (e.g. 1 2), or press Enter to skip:
```

**Then, for a code project only: heavy downloads.** Skip this entirely, without a word, unless the
primary work pack is `agile-default` or the folder holding `project-state/` has `package.json`,
`pyproject.toml` or `requirements*.txt` files, and skip it when an intake record already settled
`caches`. Scan those files (not `node_modules`) for the tools in
`skills/project-state/references/heavy-artifacts.md`, then ask once:

```
Some tools download something large on first run (a database binary, a browser, model weights).
Found: mongodb-memory-server (apps/web, apps/app), cached in node_modules — a clean install deletes it.

  **1** List it, cached in a git-ignored .cache/ at the repository root
  **2** Nothing heavy here
  **3** Not sure — ask later

>
```

1 writes one entry per confirmed artifact (`artifact`, `tool`, `size`, `path: .cache/<tool>`, `setting`
from the reference's table); 2 writes `caches: []`; 3 leaves it unset. In HTML mode, one ToggleCard per
found artifact plus the same three choices.

---

### Step 6: Review configuration

**Purpose:** Show the complete configuration and expose any unresolved material choice before writing.

**Markdown output:**
```
── Step 6 of 6: Review configuration ────────────────────────────

Review the configuration below. Resolve any missing required value before scaffolding.

  Project:    [long name] ([slug])
  Pack(s):    [packs]
  Phase:      [phase]
  Funder:     [funder]
  Lead org:   [org]
  Consortium: [N members]
  Surfaces:   [enabled]
  Downloads:  [N under .cache/ | none | not asked]
  Sharing:    [model]
  Git:        [yes/no]

```mermaid
graph TD
    root[project-root/] --> ps[project-state/]
    root --> ga[.gitattributes]
    ps --> mf[manifest.yaml] & st[state.json] & rm[reporting-matrix.yaml]
    ps --> ph[phases/] & docs[documents/] & logs[logs/]
    ps --> ms[milestones/ empty] & ppl[people/ empty]
```

  [Ask only if a material choice remains unresolved; otherwise scaffold as requested.]

>
```

---

### Step 7: Build Output

Run once the requested scaffold has complete inputs. Write all files now.

**Markdown output:**
```
── Scaffolded ✓ ─────────────────────────────────────────────────

| Status | Path                                        | Note                           |
|--------|---------------------------------------------|--------------------------------|
| ✅     | project-state/manifest.yaml                 | 3 TODOs remain                 |
| ✅     | project-state/state.json                    | Phase: [selected]              |
| ✅     | project-state/reporting-matrix.yaml         | Seeded from [pack] defaults    |
| ✅     | project-state/outbox/queue/*-seed-*         | Draft milestones + risks       |
| ✅     | project-state/automation/tasks.yaml         | Compiled from matrix           |
| ✅     | project-state/logs/activity.ndjson          | project.scaffolded event       |
| ✅     | .gitattributes                              | merge=union on logs            |
| ✅     | .gitignore                                  | .cache/ (if caches listed)     |
| ✅     | Git repo initialized                        | Initial commit made            |
| ⬜     | project-state/milestones/                   | Empty — seed later             |
| ⬜     | project-state/people/                       | Empty — add later              |
| ⬜     | project-state/lessons-learned/               | Empty — capture later          |

Next steps:
  **1** Review seeded milestones/risks   → approve in the outbox, then adopt-seeds
  **2** Add team members                 → /project-state
  **3** Checkpoint to git                → /project-git checkpoint
  **4** Done for now
```

---

## Git initialization

After files are written (Step 7), initialize git if the git sharing model was selected:

1. Run `git rev-parse --git-dir`. If already inside a repo, skip `git init` — only add the `.gitattributes` entry if missing.
2. Run `git init` in the project root (if no repo exists).
3. Write `.gitattributes` to the project root:
   ```
   # project-state git merge configuration
   # Append-only logs: keep all lines from both sides (never a real conflict)
   project-state/logs/*.ndjson merge=union
   ```
4. If `caches` lists anything and `.cache/` is not already ignored, append `.cache/` to the root
   `.gitignore` (see `caches` under Step 2).
5. Stage and commit: `git add . && git commit -m "project-state: facility scaffolded — <project.name>"`

If shared-drive model: skip git entirely. Note in Step 7 output: "Git checkpointing is available if you switch to git sharing later."

---

## Discipline

- **Resolve inputs before writing.** A direct scaffold request authorizes local setup once required choices and paths are known. Present the configuration and ask only about unresolved material decisions.
- **Idempotent, CONDITIONALLY.** Invoked directly with no intake record: if `project-state/` already
  exists, abort before Step 1 with a warning and offer `project-state validate` instead. Called WITH
  an intake record (see "Parameterised invocation" below): **adopt** the existing tree — never
  overwrite, never clear — because re-orientation is a supported path where an existing facility is
  the premise, not a mistake. Same rule and same word as capability `enable` step 5. A blanket abort
  broke `project-onboarding`'s re-orientation flow, which calls this skill in Chapter 8 against a
  facility that already exists (FB-001).
- **Never overwrite existing files.**
- **Atomic failure.** If scaffolding aborts mid-way, clean up anything partially created.
- **Codex presentation.** Use concise Markdown and bundle resolved steps when that reduces repeated prompts.

---

## Parameterised invocation

This skill has two front doors, and only one of them is the wizard.

**Interactive.** A person runs it directly; Steps 1–6 collect missing values and present the selected configuration. A direct request authorizes the scaffold after required choices are resolved. If `project-state/` exists, it aborts (see Discipline).

**From an intake record.** `project-onboarding` Chapter 8 calls this skill with its captured intake
record as structured input: *"Call `project-scaffolder` with all captured inputs, passing the working
intake record as structured input. Do not re-ask questions that have already been answered."* In this
mode the wizard does not run — every value it would have asked for is supplied — and an existing
`project-state/` is **adopted** rather than refused, because onboarding also serves re-orientation of
a live facility.

This contract existed and worked for months while documented only in the caller. It is written here
because a callee that refuses its own documented caller is not discoverable from either side alone
(FB-001).

### `seed-pack` (supersedes `seed-matrix`)

`project-onboarding` Chapter 8 and Step 7 above call this after the manifest is written. It runs the
deterministic helper shipped with this skill:

```bash
python3 <this skill>/scripts/seed_pack.py seed --state project-state --actor <operator email>
```

1. **Matrix.** Merges `reporting-matrix-defaults.yaml` from every loaded pack into
   `project-state/reporting-matrix.yaml` — primary work pack first. An entry whose `id` already exists is
   left alone: an operator's edit outranks a pack default. Comments and other keys survive.
2. **Seeds.** For each loaded pack that ships `seeds/milestones.yaml` or `seeds/risks.yaml`, queues one
   DRAFT card in `outbox/queue/` with every date expression already resolved against
   `project.start_date`, `project.end_date` and `phases.anchor_date`. A seed whose date is missing is
   queued *undated* and the card names the missing field — it is never dated by guess.
3. **Never** writes a live milestone, risk or KPI (KPI seeds route through `project-goal-tracker`, decision record
   `2026-09-24-project-types-three-axes`), and never seeds a capability pack (its enable step does).

Idempotent: a re-run adds only matrix ids and seed cards that do not exist yet. `--dry-run` prints the
plan and writes nothing. `seed-matrix` remains as an alias for callers that predate seeds: it is
`seed_pack.py seed --no-seeds` — the matrix step only.

### `adopt-seeds <card-id>`

After the operator approves a seed card (it moves to `outbox/approved/`), write what it proposes:

```bash
python3 <this skill>/scripts/seed_pack.py adopt --state project-state --card <card-id> --actor <operator email>
```

Reads the YAML block in the card's artifact — so an operator who edited a date, reworded a title or
deleted a row gets exactly that — and writes `milestones/M<NN>-<slug>.yaml` / `risks/R-<NN>-<slug>.yaml`
numbered after the highest existing id, skipping any slug already present. Refuses a card that is still
queued or was dismissed (review-not-author). Logs `milestone.created` / `risk.created` per entity and
`seeds.adopted` once; marks the card `adopted_at` so a second run writes nothing.

An approved card authorizes adoption of that reviewed proposal when adoption was requested or the approval was given for this workflow. Run `adopt-seeds` once; do not ask again. If a card is merely queued, leave it as a draft for review.

Each adopted milestone records `seed_due` (its expression) and `seed_basis` (the start, end and anchor
dates it was resolved against). That is what lets `project-milestone-manager reanchor()` move the plan
when an event or launch date slips without touching anything a person has re-dated.

---

## Integration

- **project-state** — all subsequent reads/writes route through it (once scaffolded).
- **project-document-curator** — offered in Step 7 next-steps for proposal ingestion.
- **project-milestone-manager** — offered in Step 7 next-steps for milestone seeding.
- **project-phase-gate** — becomes active once scaffolded.
- **project-git** — git initialization is part of scaffolding; `project-git` handles all subsequent checkpointing, pushing, and syncing.
- **project-onboarding** — the deeper context-gathering experience; runs after scaffolding to fill references/ with examples and stakeholder context. Volunteered goals route through `project-goal-tracker`.
