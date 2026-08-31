---
name: project-scaffolder
description: "One-shot initializer for a new project-state/ facility. Use this skill when starting a brand-new funded project — scaffolds the directory tree, manifest, phase manifests, logs, README/SCHEMA/CONCURRENCY/SKILLS docs — and when asked to 'set up a new project', 'create a new project-state', 'scaffold a project', 'initialize project-state', 'start a new funded project', 'bootstrap a grant project', 'new consortium project', 'create the state folder for [project]', 'init project-state in this folder'. Asks clarifying questions about the project, its funder, its consortium, and seeds a manifest that the team fills in. Follow-up work (milestone seeding from proposal, people seeding from MPA) is handed off to the other project-* skills."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Scaffolder

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

## Presentation Protocol

project-state runs on two surfaces. Detect and adapt before Step 1.

### Surface detection

Check the runtime context:
- **Claude Coworker / claude.ai web** → HTML artifact mode. Each wizard step is a rendered HTML artifact with real buttons.
- **Claude Code (CLI)** → Markdown mode. Each step uses Mermaid blocks, tables, and bold numbered options.

Default to HTML artifact mode. If artifact rendering is not available, fall back to markdown mode automatically.

### Design system (HTML artifact mode)

All HTML artifacts share this design system. Generate consistent, minimal UI:

```
Container:  font-family: system-ui; max-width: 680px; margin: 0 auto; padding: 24px
Colors:
  primary-green:    #22c55e  (active step, confirm button, selected border)
  primary-green-bg: #f0fdf4  (selected card background)
  text-main:        #111827
  text-muted:       #6b7280
  border:           #e5e7eb
  badge-production: bg #dcfce7  text #166534
  badge-starter:    bg #fef9c3  text #a16207
  badge-new:        bg #dbeafe  text #1e40af

Components:
  ProgressBar     — flex row of N divs (height 4px, border-radius 2px).
                    Completed steps = primary-green, pending = border-color.
  StepLabel       — "Step N of 6 — [Name]" in 12px text-muted, margin-bottom 20px.
  SectionTitle    — 18px font-weight 600, margin-bottom 4px.
  SectionSubtitle — 14px text-muted, margin-bottom 20px.
  OptionCard      — padding 12px 16px, border 1px solid border-color, border-radius 8px,
                    background #fff, cursor pointer, width 100%, text-align left,
                    display flex, justify-content space-between, align-items center.
                    Left: title (14px 600) + subtitle (13px text-muted, margin-top 2px).
                    Right: badge pill (11px, padding 2px 8px, border-radius 12px).
  SelectedCard    — OptionCard with border 2px solid primary-green, background primary-green-bg.
  NavRow          — display flex, justify-content space-between, margin-top 24px.
                    Back button: outline style (border border-color, bg #fff).
                    Primary button: background primary-green, color #fff, border none,
                    padding 10px 20px, border-radius 8px, font-weight 600.
  FormField       — label (12px text-muted font-weight 500) + input (full width,
                    padding 8px 12px, border 1px border-color, border-radius 6px,
                    font-size 14px, margin-top 4px, margin-bottom 16px).
  ToggleCard      — OptionCard with a toggle pill on the right instead of a badge.
                    Toggle on: background primary-green. Toggle off: background border-color.
  SummaryRow      — display grid, grid-template-columns 160px 1fr, gap 8px,
                    padding 10px 0, border-bottom 1px border-color, font-size 14px.
                    Label: text-muted. Value: text-main font-weight 500.
  StatusRow       — 3-column (icon 24px | filename | note text-muted). Icon: ✅ or ⬜.
```

Mermaid in HTML artifacts: use a `<pre class="mermaid">` block and load mermaid.js from CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({startOnLoad:true, theme:'neutral'})</script>
```

Button click behaviour: clicking any option or the primary button sends a message back to Claude with the selection. Claude then generates the next step artifact.

### Markdown mode (Claude Code)

Each step begins with a progress line:
```
── Step N of 6: [Step Name] ──────────────────────────────────────
```

If the step has a diagram, emit a `\`\`\`mermaid` block immediately after the progress line.

Options are presented as a markdown table with bold `**N**` in the first column. The final line of each step is a prompt:
```
> Type a number (or numbers separated by spaces) to select:
```

---

## Wizard Steps

Run steps 1–6 in sequence, one at a time. Wait for the user's response before generating the next step. Do not skip steps. Do not write any files until the user confirms in Step 6.

---

### Step 1: Pack Selection

**Purpose:** Choose which compliance pack(s) to load. Packs seed the reporting matrix and configure the six profile-driven skills.

**HTML artifact:**
- ProgressBar (1 of 6 active)
- StepLabel
- SectionTitle: "Which compliance pack fits your project?"
- SectionSubtitle: "Packs configure reporting cadence, phase gates, and stakeholder routing. You can select more than one — they compose cleanly."
- 7 OptionCards (one per pack) + 1 for "None / custom":

  | Pack | Subtitle | Badge |
  |------|----------|-------|
  | `pic-pcais` | Protein Industries Canada PCAIS consortium | production |
  | `grant-canada` | Canadian grants — NSERC, IRAP, SIF, CFI, Mitacs + 13 more | starter |
  | `client-services` | Client engagement with QBR cadence | starter |
  | `board-investor` | Board and investor reporting | starter |
  | `agile-default` | Engineering team, sprint cadence | starter |
  | `open-source-community` | Community-governed open-source | starter |
  | None / custom | Bare presets — configure manually | — |

- Note below cards: "Tip: grant-canada + pic-pcais covers the full PIC lifecycle. **SR&ED is not in this list** — it is a capability, not a pack. It brings its own entity kinds, validator and bundled pack, and needs a fiscal year end this step doesn't ask for. Finish here, then run `/sred-onboarding`."
- NavRow: no Back | Continue →

**Markdown output:**
```
── Step 1 of 6: Pack Selection ──────────────────────────────────

Which compliance pack(s) fit your project? Select one or more.

| # | Pack              | Best for                                   | Maturity   |
|---|-------------------|--------------------------------------------|------------|
| 1 | pic-pcais         | Protein Industries Canada PCAIS consortium | 🟢 Prod    |
| 2 | grant-canada      | Canadian grants (NSERC, IRAP, SIF + 12)    | 🟡 Starter |
| 4 | client-services   | Client engagement, QBR cadence             | 🟡 Starter |
| 5 | board-investor    | Board and investor reporting               | 🟡 Starter |
| 6 | agile-default     | Engineering team, sprint cadence           | 🟡 Starter |
| 7 | open-source       | Community-governed open-source             | 🟡 Starter |
| 8 | None / custom     | Bare presets — configure manually          | —          |

> Type a number (e.g. 2 or 2 3 for multiple):
```

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

Spec: `docs/CONTINUOUS-LIFECYCLE-SPEC.md` §4.1.

**`phases.preset` — write it, always.** This is the key FB-003 is about: five presets shipped in
`templates/phase-presets/` and nothing ever wrote the manifest key that selects one, so choosing a
ladder meant hand-editing YAML for ten weeks. Resolution order:

1. The intake record's `phases.preset`, when called from `project-onboarding` Q1.9.
2. The selected pack's declared default preset.
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


**HTML artifact:**
- ProgressBar (2 of 6 active)
- Mermaid diagram of the 6-phase lifecycle with the default phase highlighted:
  ```mermaid
  graph LR
    P1[01 LOI] --> P2[02 Approval] --> P3["03 Planning ◀"] --> P4[04 Execution] --> P5[05 Closeout] --> P6[06 Archive]
    style P3 fill:#22c55e,color:#fff,stroke:#16a34a
  ```
- SectionTitle: "Which phase are you starting in?"
- 4 OptionCards:

  | Phase | Title | When to choose |
  |-------|-------|----------------|
  | `01-loi` | LOI / Pre-proposal | Still writing the application |
  | `02-approval` | Approval | Applied — waiting for funder decision |
  | `03-planning` *(default)* | Planning | Award confirmed, MPA in progress |
  | `04-execution` | Execution | Project already underway |

- NavRow: ← Back | Continue →

**Markdown output:**
```
── Step 2 of 6: Phase Selection ─────────────────────────────────

```mermaid
graph LR
    P1[01 LOI] --> P2[02 Approval] --> P3["03 Planning ◀ default"] --> P4[04 Execution] --> P5[05 Closeout] --> P6[06 Archive]
    style P3 fill:#22c55e,color:#fff,stroke:#16a34a
```

| # | Phase           | When to choose                        |
|---|-----------------|---------------------------------------|
| 1 | 01 — LOI        | Still writing the application         |
| 2 | 02 — Approval   | Applied, waiting for decision         |
| 3 | 03 — Planning ✓ | Award confirmed, MPA in progress      |
| 4 | 04 — Execution  | Project already underway              |

> Type a number [default: 3]:
```

---

### Step 3: Project Identity

**Purpose:** Collect project name, funder, program, PI/PL, and dates. These seed `manifest.yaml`.

**HTML artifact:**
- ProgressBar (3 of 6 active)
- SectionTitle: "Tell me about the project"
- FormFields in two columns where space allows:
  - Project short name (slug, e.g. `atlas`)
  - Project long name (full title)
  - Funder / sponsor organization
  - Program / contract name
  - Project Lead name + email
  - Project start date (date input)
  - Project end date (date input, optional)
  - Proposal / LOI document path (optional, file path hint)
- NavRow: ← Back | Continue →

**Markdown output:**
Present questions one at a time in sequence. After each response, confirm and move to the next:
```
── Step 3 of 6: Project Identity ────────────────────────────────

I'll ask a few questions about the project. Answer each in turn.

  1. Project short name (used as slug, e.g. atlas):
```
Then after each answer: `Got it. Next:`

---

### Step 4: Consortium & Sharing

**Purpose:** Capture consortium members, the Project Lead organization, and the team sharing model.

**HTML artifact:**
- ProgressBar (4 of 6 active)
- SectionTitle: "Consortium and team sharing"
- Sub-section: **Lead organization** — FormField (org name)
- Sub-section: **Consortium members** — repeating group:
  - Org name + role (member / partner / advisor) + contact email
  - "+ Add member" button
- Sub-section: **Team sharing model** — 3 OptionCards:

  | Model | Description |
  |-------|-------------|
  | **Git** *(recommended)* | `project-state/` lives in a git repo. `project-git` handles checkpointing and sync. Append-only logs merge without conflicts. |
  | **Shared drive** | Dropbox / Google Drive / OneDrive. No git. Advisory lockfiles handle concurrency. |
  | **Single user** | One user, local only. No sharing needed. |

- NavRow: ← Back | Continue →

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

**HTML artifact:**
- ProgressBar (5 of 6 active)
- SectionTitle: "Which surfaces does the team use?"
- SectionSubtitle: "You can enable or reconfigure these at any time in manifest.yaml."
- 4 ToggleCards, all off by default:

  | Surface | What it does |
  |---------|-------------|
  | **Slack** | Posts status updates and alerts to configured channels |
  | **Gmail** | Creates drafts — never auto-sends |
  | **Google Calendar** | Proposes meeting holds and deadline reminders |
  | **scsiwyg blog** | Publishes project narrative posts through a review queue |

- Each toggle card, when enabled, expands a FormField for the key config value (channel name / calendar ID / site slug)
- NavRow: ← Back | Continue →

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

---

### Step 6: Review & Confirm

**Purpose:** Show the complete configuration before writing anything. Nothing touches the filesystem until the user confirms here.

**HTML artifact:**
- ProgressBar (6 of 6 active)
- SectionTitle: "Ready to scaffold — review before writing"
- SummaryRows covering all collected inputs:
  - Project: [long name] (`[slug]`)
  - Pack(s): [selected packs]
  - Phase: [selected phase]
  - Funder: [funder]
  - Lead org: [lead org]
  - Consortium: [N members]
  - Surfaces: [enabled list]
  - Sharing: [model]
  - Git: Yes — will `git init` + write `.gitattributes` / No — shared drive
- Mermaid preview of what will be created:
  ```mermaid
  graph TD
      root[project-root/] --> ps[project-state/]
      root --> ga[.gitattributes]
      ps --> mf[manifest.yaml]
      ps --> st[state.json]
      ps --> rm[reporting-matrix.yaml]
      ps --> ph[phases/]
      ps --> docs[documents/]
      ps --> logs[logs/]
      ps --> ms[milestones/ — empty]
      ps --> ppl[people/ — empty]
  ```
- NavRow: ← Edit | **Scaffold Now** (primary green)

**Markdown output:**
```
── Step 6 of 6: Review & Confirm ───────────────────────────────

Review your configuration. Nothing is written until you confirm.

  Project:    [long name] ([slug])
  Pack(s):    [packs]
  Phase:      [phase]
  Funder:     [funder]
  Lead org:   [org]
  Consortium: [N members]
  Surfaces:   [enabled]
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

  **1** Confirm and scaffold
  **2** Go back and change something

>
```

---

### Step 7: Build Output (post-confirm)

Triggered immediately after the user confirms in Step 6. Write all files now.

**HTML artifact:**
- Brief animated progress message: "Scaffolding your project..."
- Then replace with result card:
  - SectionTitle: "Project scaffolded ✓"
  - StatusRows for each created file/directory (✅ written / ⬜ empty / ⚠ TODO):

    | Icon | Path | Note |
    |------|------|------|
    | ✅ | `project-state/manifest.yaml` | 3 TODOs remain (MPA date, review designates, funder contacts) |
    | ✅ | `project-state/state.json` | Phase: [selected] |
    | ✅ | `project-state/reporting-matrix.yaml` | Seeded from [pack] defaults |
    | ✅ | `project-state/automation/tasks.yaml` | Compiled from matrix by project-automator |
    | ✅ | `project-state/logs/activity.ndjson` | `project.scaffolded` event |
    | ✅ | `.gitattributes` | `merge=union` on logs (if git model) |
    | ✅ | Git repo | Initial commit: "project-state: facility scaffolded — [slug]" |
    | ⬜ | `project-state/milestones/` | Empty — seed with `/project-milestone-manager` |
    | ⬜ | `project-state/people/` | Empty — add via `/project-state` |
    | ⬜ | `project-state/lessons-learned/` | Empty — capture with `/project-lessons`; shape in `templates/lesson-learned.md` |

  - SectionTitle: "What would you like to do next?"
  - 4 OptionCards as next-step buttons:

    | # | Action | Skill |
    |---|--------|-------|
    | 1 | Seed milestones from proposal document | `/project-milestone-manager` |
    | 2 | Add team members | `/project-state` |
    | 3 | Checkpoint to git | `/project-git checkpoint` |
    | 4 | Done for now | — |

**Markdown output:**
```
── Scaffolded ✓ ─────────────────────────────────────────────────

| Status | Path                                        | Note                           |
|--------|---------------------------------------------|--------------------------------|
| ✅     | project-state/manifest.yaml                 | 3 TODOs remain                 |
| ✅     | project-state/state.json                    | Phase: [selected]              |
| ✅     | project-state/reporting-matrix.yaml         | Seeded from [pack] defaults    |
| ✅     | project-state/automation/tasks.yaml         | Compiled from matrix           |
| ✅     | project-state/logs/activity.ndjson          | project.scaffolded event       |
| ✅     | .gitattributes                              | merge=union on logs            |
| ✅     | Git repo initialized                        | Initial commit made            |
| ⬜     | project-state/milestones/                   | Empty — seed later             |
| ⬜     | project-state/people/                       | Empty — add later              |
| ⬜     | project-state/lessons-learned/               | Empty — capture later          |

Next steps:
  **1** Seed milestones from proposal    → /project-milestone-manager
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
4. Stage and commit: `git add . && git commit -m "project-state: facility scaffolded — <project.name>"`

If shared-drive model: skip git entirely. Note in Step 7 output: "Git checkpointing is available if you switch to git sharing later."

---

## Discipline

- **Never write files before Step 6 confirmation.** The entire wizard is read-only until the user confirms.
- **Idempotent, CONDITIONALLY.** Invoked directly with no intake record: if `project-state/` already
  exists, abort before Step 1 with a warning and offer `project-state validate` instead. Called WITH
  an intake record (see "Parameterised invocation" below): **adopt** the existing tree — never
  overwrite, never clear — because re-orientation is a supported path where an existing facility is
  the premise, not a mistake. Same rule and same word as capability `enable` step 5. A blanket abort
  broke `project-onboarding`'s re-orientation flow, which calls this skill in Chapter 8 against a
  facility that already exists (FB-001).
- **Never overwrite existing files.**
- **Atomic failure.** If scaffolding aborts mid-way, clean up anything partially created.
- **Surface-aware.** Detect HTML vs. markdown mode before Step 1 and stay consistent throughout all steps.
- **One step at a time.** Generate one artifact or one markdown step, wait for response, then generate the next. Do not bundle multiple steps.

---

## Parameterised invocation

This skill has two front doors, and only one of them is the wizard.

**Interactive.** A person runs it directly; Steps 1–6 interview them; nothing is written before
confirmation. If `project-state/` exists, it aborts (see Discipline).

**From an intake record.** `project-onboarding` Chapter 8 calls this skill with its captured intake
record as structured input: *"Call `project-scaffolder` with all captured inputs, passing the working
intake record as structured input. Do not re-ask questions that have already been answered."* In this
mode the wizard does not run — every value it would have asked for is supplied — and an existing
`project-state/` is **adopted** rather than refused, because onboarding also serves re-orientation of
a live facility.

This contract existed and worked for months while documented only in the caller. It is written here
because a callee that refuses its own documented caller is not discoverable from either side alone
(FB-001).

### `seed-matrix`

`project-onboarding` also invokes `project-scaffolder seed-matrix` to seed
`project-state/reporting-matrix.yaml` from the selected packs. Merge semantics: entries whose `id`
already exists are left alone — an operator's edit outranks a pack default. Also undocumented until
2026-08-21, and for the same reason.

---

## Integration

- **project-state** — all subsequent reads/writes route through it (once scaffolded).
- **project-document-curator** — offered in Step 7 next-steps for proposal ingestion.
- **project-milestone-manager** — offered in Step 7 next-steps for milestone seeding.
- **project-phase-gate** — becomes active once scaffolded.
- **project-git** — git initialization is part of scaffolding; `project-git` handles all subsequent checkpointing, pushing, and syncing.
- **project-onboarding** — the deeper context-gathering experience; runs after scaffolding to fill references/ with goals, examples, and stakeholder context.
