---
name: project-intake
description: "Source-first fast-path initialization from supplied proposals, agreements, schedules, or repository files. Extract only attributed facts, confirm applicable packs, group unresolved required routing questions, and preserve the standard manifest, reporting matrix, automation registry, and scaffold. Never infer objectives, milestones, contacts, eligibility, capabilities, or external surfaces beyond explicit source content. Use for intake, setup from documents, quick init, or re-analysis."
---

> Codex adapter: Read [CODEX.md](../../../CODEX.md) before using this skill.

# project-intake

## Purpose

Replace the question-heavy wizard (project-scaffolder) and 9-chapter interview
(project-onboarding) with a doc-driven fast path:

```
docs + pack → extract → propose → confirm → manifest + matrix + schedule
```

Three phases, one confirmation screen, zero repeated questions.

Apply the adapter's scale routing before gathering. Routine task-local work does
not initialize Project State. Epic intake captures one shared outcome and only
meaningful milestones/references/risks. Program intake may populate the full
facility. Scale is runtime policy, not a manifest field; an explicit initialize
request still uses the established standard tree and schema.

The output is identical to what project-scaffolder + project-onboarding produce —
a valid `project-state/` with a filled manifest, a seeded reporting matrix, and a
compiled `automation/tasks.yaml` — but the path is document-first rather than
conversation-first.

---

## Invocation

```
/project-intake                                  # interactive: asks for docs + pack
/project-intake --pack pic-pcais                 # pack known; asks for docs
/project-intake --docs path/to/folder            # docs known; infers/asks pack
/project-intake --pack pic-pcais --confirm       # auto-confirm if high-confidence
/project-intake re-analyze                       # re-run extraction on existing facility
```

**Trigger phrases:**
- "intake this project"
- "set up from docs" / "configure from documents"
- "quick init" / "init from proposal"
- Drop a document and say "set up project-state from this"

---

## Phase 1 — Gather

### 1a. Accept documents

Accept any combination of:
- Files dropped directly into the conversation
- File paths or directory paths
- URLs pointing to documents
- Pasted text content

Useful document types (accept anything, classify on read):
| Type | What to extract |
|------|----------------|
| Governing document (MPA, SOW, Grant Agreement) | Name, funder, dates, budget, milestones, people, obligations |
| Proposal / application | Project rationale, technical approach, team, milestones |
| Milestone schedule / work plan | Milestone list with dates and owners |
| Previous report or claim | Format and tone reference only (save to references/examples/) |
| Org chart | People + roles |

If no documents are provided: ask once — "Drop your project documents here (proposal, MPA, milestone schedule, or any combination). Or type 'skip' to initialize with pack defaults only."

If user skips: proceed with pack defaults and empty manifest fields (valid-but-thin).

### 1b. Detect and confirm a pack

Use explicit source signals to propose a candidate pack before asking:

| Signal in documents | Candidate pack or follow-up |
|--------------------|---------------|
| "Protein Industries Canada", "PCAIS", "PIC" | `pic-pcais` |
| "NSERC", "IRAP", "Mitacs", "CFI", "SIF" | `grant-canada` |
| "SR&ED", "T661", "experimental development" | *(not a pack)* → set `sred_interest: yes` and hand off to `sred-onboarding` after intake completes |
| Sprint cadence, story points, backlog | `agile-default` |
| "board of directors", "investors", "cap table" | `board-investor` |
| SOW, "Statement of Work", "client deliverables" | `client-services` |

If a candidate pack is detected, present it with its source as a one-line
confirmation. Do not load it until confirmed, and do not run a pack selection
wizard.

If no pack is inferable and none was provided: show a compact pack list and ask for selection (not a wizard — a single prompt):
```
Pack options: pic-pcais / grant-canada / client-services / board-investor / agile-default / open-source / none
Which fits? (you can pick multiple, e.g. "grant-canada agile-default"):
```

Multiple packs are additive — load all selected packs' reporting-matrix-defaults.yaml.

**SR&ED is deliberately absent from the pack list.** `sred-canada` exists, but it is the *bundled*
pack of the `sred` capability and is loaded by that capability's enable step, not selected here.
Selecting it as a project pack produces a half-configured state: matrix entries with no `sred/`
directory, no runtime state, and no filing deadline. When the SR&ED signal fires above, set
`sred_interest: yes` on the intake record and offer `/sred-onboarding` once intake finishes.

### 1c. Extract silently

Run the extraction pass. Do not ask questions during extraction. Extract:

**Project identity**
- `project.name` — short name/code (look for: project title, "Project [Name]", proposal title)
- `project.long_name` — formal title as it appears on the governing document
- `project.funder` — funding/commissioning organization name
- `project.program` — program or contract name
- `project.start_date` — YYYY-MM-DD (look for: "project start", "commencement date", "effective date")
- `project.end_date` — YYYY-MM-DD
- `project.budget_total_cad` — total budget figure if present (optional, skip if not found)
- `project.kind` — classify only when the governing source states enough to
  support one of: grant_consortium | client_engagement | startup | open_source |
  generic; otherwise record a gap

**Milestones** — for each milestone found:
- `id` — assign sequentially M01, M02... if not already numbered
- `title` — as written in the document
- `owner_org` — which organization owns it (look for "Lead: X", "Responsible: X")
- `planned_end` — completion date (YYYY-MM-DD)
- `description` — brief description (first sentence or heading context)
- `completion_criteria` — if explicitly stated

**People / stakeholders**
- Name, organization, role (look for signature blocks, "Parties", role tables, org charts)
- Preserve the source role. Map it to a pack-defined role only when the mapping is
  explicit or unambiguous; otherwise ask in the grouped routing questions.
- Flag which stakeholder_group they belong to: internal.team | funder.{id} | customer.{id} | board | consortium.all

**Cadence overrides** — look for explicit schedule statements that override pack defaults:
- Fixed claim/payment dates ("quarterly payments due April 20, July 20...")
- Fixed meeting cadence ("quarterly Steering Committee meetings")
- Specific review windows ("reports due within 30 days of quarter end")

Record each extracted field with its source: `{value, source: "doc:filename:section"}`.
Record each field not found as a gap: `{key, blocks: [...]}`.

---

## Phase 2 — Propose

Present a single confirmation screen. Nothing has been written yet.

**Codex Markdown format:**

```
── Intake Proposal — [project.name] ─────────────────────────────

EXTRACTED FROM DOCUMENTS
  project.name:        [value]                     [doc: filename]
  project.long_name:   [value]                     [doc: filename]
  project.funder:      [value]                     [doc: filename]
  project.start:       [value]                     [doc: filename]
  project.end:         [value]                     [doc: filename]
  milestones:          [N] found → [M01 title], [M02 title], ...
  people:              [N] found → [Name (role)], ...

CONFIGURED FROM PACK ([pack-id])
  reporting entries:   [N] (from pack defaults)
  [key entries]:       e.g. quarterly claims: Apr 20 / Jul 20 / Oct 20 / Jan 20
                       SC pack: quarterly, docx → gmail.draft + calendar.invite
                       weekly: monday tracker → gmail.draft + slack
                       [etc — show 3-4 most important]

GAPS  (recorded, not blocking)
  [key]                — [why it matters: "affects claim prep"]
  ...

Options:
  [y] Confirm and write
  [e <field>] Edit a field, e.g. "e project.name"
  [p] Show full reporting matrix preview
  [s] Skip all gaps and confirm
```

Keep the same Extracted / Pack defaults / Gaps grouping in Markdown. Label each
extracted field with `[doc: source]`, each pack entry with `[pack-id]`, and each
gap with `[fill later]` before the confirmation prompt.
Milestones render as a compact inline table (id | title | owner | date).
People render as role chips.

### Editing a field

If the user types `e project.name` or clicks an edit button:
- Show the current value and source
- Accept the correction inline
- Update the proposal screen and confirm again

Do not re-run the full extraction for a single edit.

### Full matrix preview

If the user asks to see the full reporting matrix:
Show all entries from the pack defaults with their cadence, format, surface, and generator.
Allow the user to disable individual entries by number before confirming.

---

## Phase 3 — Write

On confirmation, write all files in this order:

### 3a. Initialize directory tree

If `project-state/` does not exist, create:
```
project-state/
  manifest.yaml
  reporting-matrix.yaml
  state.json
  automation/
    tasks.yaml            ← written by project-automator in step 3d
  phases/
  milestones/             ← one file per extracted milestone
  people/
  documents/
    inbox/
  references/
    intake-record.yaml    ← audit trail
  logs/
    activity.ndjson
```

If `project-state/` already exists:
- Abort and offer `project-intake re-analyze` instead
- Do not overwrite existing files

### 3b. Write manifest.yaml

Fill from the extraction record. For every field:
- Extracted value → write the value, add a comment `# source: doc:filename`
- Gap → write the TODO placeholder from the template, add `# gap: <reason>`
- Pack default → leave as-is (pack profiles configure, not manifest)

Stakeholders: write one entry per extracted person, mapped to their stakeholder_group.
Always include `internal.team` as the baseline stakeholder.

`packs_loaded` → the confirmed pack list.

### 3c. Write reporting-matrix.yaml

1. Start with the pack defaults from `packs/{pack}/reporting-matrix-defaults.yaml` for each loaded pack.
2. Apply any cadence overrides extracted from documents (e.g. specific claim dates → override the pack's quarterly `days` array).
3. Merge entries from multiple packs — deduplicate by `report` name if the same report appears in two packs.
4. Write to `project-state/reporting-matrix.yaml`.

### 3d. Project automation projection

After writing the matrix, run `project-automator generate` only when automation
was explicitly confirmed enabled, an applicable active pack requires scheduled
work, and a project timezone is confirmed. Otherwise write/retain a disabled
`automation/tasks.yaml` registry with an empty `tasks` list whose top-level
timezone exactly mirrors `manifest.yaml:automation.timezone`, including `~`.
Do not create scheduled work merely because matrix entries exist.

If scheduling is enabled and no timezone was found in documents or manifest,
ask once — "What timezone for scheduled jobs? (e.g. America/Vancouver)" — before
calling. If scheduling is disabled, leave it unresolved and consistent.

### 3e. Write milestone files

For each extracted milestone, write `project-state/milestones/M<NN>-<slug>.yaml`:
```yaml
schema_version: 1
id: M01
kind: milestone
created: "[ISO-8601]"
created_by: project-intake
last_modified: "[ISO-8601]"
last_modified_by: project-intake
phase: "[current phase id]"
title: "[extracted title]"
description: "[extracted description]"
owner_org: "[extracted or gap: TODO]"
planned_end: "[YYYY-MM-DD or gap: TODO]"
completion_criteria: "[extracted or gap: TODO]"
percent_complete: 0
status: not_started
# source: doc:[filename]
```

### 3f. Write intake record

Write `project-state/references/intake-record.yaml` — the full extraction audit trail:
```yaml
session_date: "[ISO-8601]"
documents_processed: [list of filenames/paths]
packs_loaded: [list]
extraction_summary:
  fields_extracted: N
  fields_from_pack_defaults: N
  gaps: N
fields:
  - key: project.name
    value: "..."
    source: "doc:filename:section"
  - key: M04.owner_org
    value: ~
    source: gap
    reason: "not found in documents"
    blocks: ["claim-prep"]
```

### 3g. Append to activity log

Append to `project-state/logs/activity.ndjson`:
```json
{"ts":"[ISO-8601]","actor":"project-intake","event":"project.intake.completed","id":"evt-<deterministic-id>","summary":"Processed N source documents; extracted N fields with N unresolved gaps; automation <compiled|left disabled>."}
```

Use the adapter's deterministic identity inputs (source document identities,
confirmed pack set, and normalized resulting intake facts). An exact re-analysis
of unchanged inputs returns the existing event and does not append, increment,
or fan out again.

### 3h. Git initialization

If the directory is not already inside a git repo:
1. Run `git init`
2. Write `.gitattributes` with `project-state/logs/*.ndjson merge=union`
3. Leave the facility uncommitted and offer `project-git checkpoint` separately.

If already in a git repo: skip init and add the `.gitattributes` entry if missing.
Never stage or commit as part of intake.

---

## Phase 3 — Output

After all files are written, show a status summary:

```
── Initialized ✓ — [project.name] ──────────────────────────────

  ✅  project-state/manifest.yaml            [N fields set, N gaps]
  ✅  project-state/reporting-matrix.yaml    [N entries from pack-id]
  ✅  project-state/automation/tasks.yaml [N time-fired, N event-hook]
  ✅  project-state/milestones/              [N files]
  ✅  project-state/logs/activity.ndjson     [project.intake.completed]
  ✅  .gitattributes                         [logs merge=union]
  ⬜  git checkpoint                         [operator decides when]

  Gaps recorded (N): run /project-state gaps to review
  Schedule ready:    run /project-automator status to verify

Next:
  /project-automator status      — verify cadence registry
  /project-state gaps            — review and fill recorded gaps
  /project-milestone-manager     — update milestone progress
  /project-orchestrator          — see what's due this week
```

---

## re-analyze mode

`/project-intake re-analyze`

For existing facilities: re-run extraction on documents in `documents/inbox/` (or a
provided path), diff the results against the current manifest, and present only the
fields that have changed or are newly found. Does not overwrite confirmed fields —
presents a diff for user review.

```
── Re-analysis diff ─────────────────────────────────────────────

  NEW FINDINGS (not in current manifest)
    M08.owner_org   →  "Example Lead Org" [doc: schedule-v2.pdf]
    M09.planned_end →  2027-03-15        [doc: schedule-v2.pdf]

  GAPS NOW FILLED (found in new documents)
    project.budget_total_cad  →  $2,400,000  [doc: mpa-signed.pdf]

  UNCHANGED
    All other fields match current manifest.

  Apply these updates? [y] yes / [n] no
```

On confirmation, patches only the changed fields and appends an
`project.intake.reanalyzed` event to the activity log.

---

## Discipline

- **Never write files before Phase 3 confirmation.** Phases 1 and 2 are read-only.
- **Never overwrite an existing `project-state/` without explicit `--force`.** Offer `re-analyze` instead.
- **Never ask questions that documents have already answered.** If the doc contains the project name, don't ask for it.
- **Never ask questions that pack defaults cover.** Reporting cadence is set by the pack; don't confirm each entry.
- **Group unresolved questions.** Ask only fields required by the schema, an
  active pack, or routing; one prompt may accept multiple answers.
- **Non-required gaps don't block.** Record them without inventing values.
- **Do not infer activation.** Objectives, milestones, contacts, eligibility,
  capabilities, automation, connectors, and delivery surfaces require explicit
  source support and any applicable confirmation.
- **Source attribution always.** Every manifest field written by intake carries a comment noting its source.
- **Compile only applicable automation.** Call `project-automator` when the
  confirmed matrix has enabled entries; otherwise leave automation disabled.

---

## Integration

- **project-state** — all writes route through it; intake-record.yaml, activity.ndjson appended
- **project-automator** — called automatically at end of Phase 3 to compile automation/tasks.yaml
- **project-milestone-manager** — milestone files written by intake are ready for progress updates immediately
- **project-orchestrator** — reads the compiled `automation/tasks.yaml`; works
  immediately after intake
- **project-onboarding** — the deep interview path; use when documents are unavailable or a guided tour is preferred
- **project-scaffolder** — the manual wizard path; intake calls its directory-creation logic internally

---

## When to use which init skill

| Situation | Use |
|-----------|-----|
| Have docs (proposal, MPA, SOW, schedule) | **project-intake** ← this skill |
| No docs, want guided questions | project-onboarding |
| No docs, explicit standard initialization | project-scaffolder |
| Known manifest or intake record supplied | project-scaffolder using that supplied record |
| Existing facility, new docs arrived | project-intake re-analyze |
