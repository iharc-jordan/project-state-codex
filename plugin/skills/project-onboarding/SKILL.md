---
name: project-onboarding
description: "Set up or re-orient a project — 'set up project-state', 'onboard this project', 'start the setup'. Asks what the work is, who hears about it and how it moves, then seeds a starting plan."
map:
  tier: P0
  stage: ingest
  inputs: [operator]
  reads: [documents]
  writes: [manifest, people, milestones, reporting-matrix]
  calls: [project-inbox, sred-onboarding]
---

# Project Onboarding

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Guided onboarding experience for new project-state instances. Begins with an Inbox Orientation pre-check — if documents/inbox/ contains files, runs project-inbox triage and pre-fills context before the first question. Then runs nine chapters: project identity, document ingestion, project type (what the work is, who hears about it, how it moves), milestone capture, stakeholder mapping, examples, gap handling, substrate initialization, and orientation check. Pre-filled chapters become confirmation passes instead of blank-slate interviews. Writes references/examples/ as first-class substrate entities. Does NOT set goals — objectives + KPIs are owned by the dedicated Goals tab, not onboarding. Use when starting a new project or re-orienting an existing one. Trigger on: 'set up project-state', 'onboard this project', 'initialize my project', 'I am new to project-state', 'configure this project', 'start the setup'.

## Purpose

Orient a new project-state instance around a specific project with enough context that every skill in the suite produces grounded, authentic output rather than plausible-but-generic output.

This skill does two distinct things that `project-scaffolder` does not:

1. **Intake** — collect context through guided conversation, document analysis, and goals elicitation before any files are written
2. **Orient** — write that context into the substrate as first-class entities (`references/examples/`, `references/context.md`) so every downstream skill can read it. (Goals — objectives + KPIs — are set up separately in the Goals tab, not by onboarding.)

`project-scaffolder` is the technical initializer. This skill is the user-facing experience that feeds it with content that makes the result worth having.

## Presentation Protocol

### Surface detection

At invocation, detect the rendering surface:
- **Coworker / claude.ai** — check if HTML artifact rendering is available. If yes, use HTML artifact mode.
- **Claude Code (CLI)** — use markdown mode.

Store the detected surface in the working session as `surface: coworker | claude-code`. Apply consistently across all chapters.

### Design system (shared with project-scaffolder)

```
Colors:
  primary-green    #22c55e     buttons, progress fill, badges
  primary-green-bg #f0fdf4     active card backgrounds
  text-main        #111827     headings and body
  text-muted       #6b7280     labels and metadata
  border           #e5e7eb     card and section borders
  amber-bg         #fffbeb     synthetic-content warning
  red-bg           #fef2f2     gap / missing field warning

Components:
  ProgressBar      — step N of M with chapter name, filled segments
  ChapterCard      — full-width card, chapter title + purpose prose
  QuestionBlock    — question label + freeform input field (in Coworker) or bold prose prompt (in CLI)
  PreFilledField   — value bubble + "Confirm or correct?" label (shown when inbox-orientation has data)
  OptionCard       — selectable pack/option card, outlined → green-bg on select
  SummaryRow       — label | value | source badge (document / conversation / synthetic)
  GapRow           — field name | impact | resolution options [provide now / leave gap / synthesize]
  QualityBar       — label + filled-block progress bar (█░) + N/3 score
  StatusRow        — ✓ / ○ prefix + field + status text
  NavRow           — [Back] [Next] or [Confirm] buttons (Coworker) / numbered prompt (CLI)
```

### HTML artifact mode (Coworker)

Each chapter = one self-contained HTML artifact. Replace the artifact on every chapter advance (do not accumulate).

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    body { font-family: system-ui; max-width: 720px; margin: 2rem auto; color: #111827; }
    .progress { display: flex; gap: 4px; margin-bottom: 1.5rem; }
    .seg { height: 6px; flex: 1; border-radius: 3px; background: #e5e7eb; }
    .seg.done { background: #22c55e; }
    .seg.active { background: #86efac; }
    .chapter-card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; }
    .chapter-label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; }
    .chapter-title { font-size: 1.25rem; font-weight: 700; margin: .25rem 0 .75rem; }
    .question { background: #f9fafb; border-radius: 8px; padding: 1rem 1.25rem; margin: .75rem 0; }
    .question label { font-size: 0.8rem; color: #6b7280; display: block; margin-bottom: .5rem; }
    .prefilled { border-left: 3px solid #22c55e; background: #f0fdf4; padding: .75rem 1rem; border-radius: 6px; }
    .source-badge { font-size: .7rem; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 9px; }
    .gap-row { border-left: 3px solid #ef4444; background: #fef2f2; padding: .5rem .75rem; margin: .5rem 0; border-radius: 4px; }
    .synth-notice { background: #fffbeb; border: 1px solid #fbbf24; border-radius: 6px; padding: .75rem 1rem; font-size: .85rem; }
    .quality-bar { display: flex; align-items: center; gap: .75rem; margin: .5rem 0; font-size: .9rem; }
    .bar-label { width: 120px; color: #374151; }
    .bar-fill { font-family: monospace; color: #22c55e; font-size: 1.1rem; }
    .score { color: #6b7280; font-size: .85rem; }
    .btn { padding: .5rem 1.25rem; border-radius: 6px; font-size: .9rem; cursor: pointer; border: none; }
    .btn-primary { background: #22c55e; color: white; }
    .btn-secondary { background: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; }
    .nav-row { display: flex; gap: .75rem; margin-top: 1.5rem; }
  </style>
</head>
<body>
  <!-- ProgressBar: 9 segments, fill per chapter index -->
  <!-- ChapterCard: chapter label + title + purpose prose -->
  <!-- Chapter-specific content (questions, summary rows, etc.) -->
  <!-- NavRow: Back (if Ch > 0) + Next / Confirm -->
</body>
</html>
```

Key rule: **use PreFilledField instead of QuestionBlock** for any field where `inbox_orientation` has a value with `triage_confidence: high | medium`. Show the pre-filled value and ask "Confirm or correct?" — the user should only need to press Next unless something is wrong.

### Markdown mode (Claude Code)

```
── Chapter N of 9: [Chapter Name] ──────────────────────────────

[Chapter purpose prose]

**[Question label]**
[Pre-filled value if available, labeled [pre-filled from documents]]
> [Question prompt]
```

NavRow = numbered options or a single bold CTA: **Type your answer or press Enter to confirm.**

---

## Trigger phrases

- "set up project-state" / "onboard this project"
- "initialize my project" / "start the setup"
- "I'm new to project-state" / "configure this project"
- "start fresh" / "new project setup"
- Re-orientation: "re-orient project-state" / "update the project context"

## The nine chapters

Run in sequence. Each chapter begins with prose the user sees — explaining what is being collected and why — before asking anything. Collect inputs in the order below. Do not skip chapters; offer to return to any chapter if the user wants to add more later.

At the start of each chapter, render a progress marker using the detected surface:

**HTML artifact mode:** Render a new artifact with a 9-segment ProgressBar (filled = completed chapters, active = current chapter) and a ChapterCard with the chapter name and purpose prose.

**Markdown mode:**
```
── Chapter N of 9: [Chapter Name] ──────────────────────────────
```

**Before starting Chapter 0,** run the Inbox Orientation pre-check (see below). If `references/inbox-orientation.yaml` is present, onboarding becomes a confirmation pass rather than a blank-slate interview.

---

### Chapter 0 — Inbox Orientation (Pre-check)

**Run this before Chapter 0 — Welcome, silently, without displaying a chapter marker.**

**Step 1 — Check for inbox documents:**

```
IF documents/inbox/ contains any files OR documents/index.yaml has any entries with status: inbox:
  → N documents are available. Proceed to Step 2.
ELSE:
  → Skip this pre-check. Go directly to Chapter 0 — Welcome.
```

**Step 2 — Check triage state:**

```
IF references/inbox-orientation.yaml exists:
  → Orientation already generated. Proceed to Step 3.
ELSE IF any entries in documents/index.yaml have triage_state: processed:
  → Some documents triaged but orientation not generated. Run project-inbox orient automatically,
    then proceed to Step 3.
ELSE:
  → Documents present but not triaged yet.
  Present: "I found N documents in documents/inbox/ that haven't been triaged yet.
  Running /project-inbox triage will let me pre-fill much of the onboarding context
  from your documents, skipping questions you've already answered.
  → Run triage now? (recommended) / Skip and continue manually"
  IF user agrees: call project-inbox triage, then proceed to Step 3.
  IF user skips: note in working intake that documents are available but untriaged. Continue.
```

**Step 3 — Present orientation briefing:**

Display:
```
── Inbox Orientation ────────────────────────────────────────────
```

> Before we begin, here's what I've already learned from your documents:

Present the contents of `references/inbox-orientation.yaml` in readable form:

- **Project identity hints**: short name, funder, dates, budget (where found). Mark each with `[from documents]`.
- **Milestone hints**: show count and first 3 titles. Say "Found N milestones — will confirm in Chapter 5."
- **Stakeholder hints**: show names found. Say "Found N contacts — will confirm in Chapter 4."
- **Confidence**: show overall confidence level (high/medium/low) with a plain-English note.
  - high: "High confidence — the governing document provided complete data."
  - medium: "Medium confidence — multiple documents gave partial data; some fields may need verification."
  - low: "Low confidence — limited or ambiguous documents; most fields still need input."

Present:
> Chapters with pre-filled data will ask you to confirm rather than answer from scratch. I'll mark pre-filled fields as `[pre-filled from documents]`. You can always correct them.
>
> Remaining gaps: [list fields from `orientation.gaps`]

**Step 4 — Store orientation in working intake:**

Mark which chapters are pre-filled in the working intake record:
```yaml
inbox_orientation:
  available: true
  confidence: high
  pre_filled_chapters: [2, 4, 5]  # from orientation.pre_filled_chapters
  orientation_path: references/inbox-orientation.yaml
```

Chapters with pre-filled data should:
- Present the pre-filled value prominently
- Ask "Is this correct?" rather than the open question
- Accept a simple "yes" or correction without re-asking all sub-questions

---

### Chapter 0 — Welcome

**Prose to present:**

> Welcome to project-state setup. This process will orient the system around your specific project so that every report, claim draft, milestone update, and stakeholder communication it produces is grounded in your actual context — not generic placeholders.
>
> We'll work through nine short chapters. Some will take two minutes; some will take ten if you have a lot to share. You can go deep or stay shallow — the system will tell you where gaps remain.
>
> **The single most valuable thing you can do right now is share documents.** If you have a proposal, a Master Project Agreement, a Statement of Work, a milestone schedule, a previous report you liked, or anything that describes what this project is and what it should produce — share it before we begin. The system will extract what it can and skip questions you've already answered.
>
> Do you have any documents to share now?

**Collect:**
- Any files, paths, or pasted content the user provides
- Accept: proposals, SOWs, MPAs, milestone schedules, reports, org charts, example outputs, previous claims, anything
- If nothing is provided: acknowledge and continue — "No problem. We'll build context through conversation."

**Process documents immediately** (before Chapter 1):
- For each document, identify its type: `governing_document | proposal | milestone_schedule | stakeholder_list | example_output | previous_report | other`
- Extract whatever is findable: project name, dates, milestones, stakeholder names, funder details, budget figures, goals
- Documents tagged `example_output` or `previous_report` are staged for `references/examples/` — do not extract structure, preserve as-is
- Present a brief extraction summary: "From your documents I found: [list]. I'll ask about the gaps."
- Mark extracted fields as `source: document` in the working intake record

---

### Chapter 1 — What kind of project this is

Three questions, one per axis (`docs/PROJECT-TYPES-SPEC.md` §3, decision
`2026-09-24-project-types-three-axes`): **what the work is** (one primary work pack), **who needs to hear
how it's going** (accountability packs), and **how the work moves** (a phase preset). Then the questions
that were always here: SR&ED, whether it ends, timezone.

**Every option comes from the catalogue, never from this file.** Read `packs/*/manifest.yaml` and
`templates/phase-presets/*.yaml`. A pack is offered by default only when `picker.listed: true`; show
`picker.label` and `picker.blurb`. Unlisted packs appear only when the operator asks for *advanced*,
marked *thin*. `axis: capability` packs are never offered here. The previous version of this chapter
asked five yes/no questions from a hardcoded list and never asked what the work was; 7 of 13 registry
facilities ended up with no pack, and two non-open-source projects loaded `open-source-community` as
the least-wrong option.

**Prose to present:**

> Project-state shapes itself to the kind of work you're doing: the phases it tracks, the milestones it
> starts you with, and which reports go to whom. Three quick questions.

**Q1.0 — One sentence.**

> In a sentence, what is this project trying to make happen?

If the inbox orientation already answers it, present your one-line reading instead and ask for a yes.
Classify the answer against every listed `axis: work` pack: match its `picker.signals` phrases, then use
judgement — the signals are hints, not a keyword gate. Present the best match as a confirmation, with the
runner-up offered by name:

> This reads like **[picker.label]** — [picker.blurb] Is that right, or is it closer to **[runner-up]**?

If nothing fits well, offer **General project** (`work-general`) as a real choice: "General project gives
you a define → plan → deliver → review → close ladder with dated starting milestones. Nothing is lost by
choosing it."

**Q1.A — Confirm the work type.** Write the confirmed pack as `work_type` on the intake record; it
becomes `project.kind`. On *advanced*, list every work pack including unlisted ones, and allow
*secondary* work packs (a software launch that is also a campaign): they add matrix entries and seeds but
never the preset (decision D4).

**Q1.B — Who needs to hear how it's going?**

> Who needs to hear how this is going? Pick any.

Offer every listed `axis: accountability` pack plus **Just me**. Packs with `picker.preselected: true`
(`sponsor-internal`, decision D3) start selected and are presented as a confirmation: "I've assumed
there's a manager or sponsor who commissioned this — keep that?" **Just me** deselects everything.

When the operator names a **government funder or grant**, run the funder sub-questions:
- Is it a Canadian federal program? Which one? Match against the funder packs' `picker.signals`
  (`pic-pcais`, `grant-canada`). Present the pack's one-line blurb.
- No matching pack → note the program and continue: "I don't have a pack for that program yet, but the
  core skills still work. You can configure the funder-reporting profile manually." SR&ED is not a
  funder pack — if it comes up here, set `sred_interest: yes` and let Q1.6 handle it.

Write the confirmed list as `accountable_to` on the intake record.

**Q1.C — How does the work move?**

Pre-fill from the **primary work pack's** `defaults.preset` and present it as a confirmation ("Events are
planned backwards from the date — right?"). With no work pack, an accountability pack's
`defaults.preset` pre-fills (a PIC-funded project → `grant-default`). Otherwise ask, in these words:

| Answer | Preset |
|---|---|
| "In sprints or iterations" | `agile-default` |
| "Through stages, with sign-off between them" | `stage-gate-default` |
| "Toward a fixed date" | `countdown-default` |
| "In a repeating cycle" | `cycle-default` |
| *advanced* | `grant-default` (proposal → approval → planning → execution → closeout → archive), `client-engagement-default` (discovery → proposal & SOW → engagement → wrap → archive), `waterfall-default` (requirements → design → build → test → deploy → maintain), `open-source-default` (incubation → active → maintained → archived), custom |

Write the confirmed value as `phases.preset`. `project-phase-gate set_preset(name)` changes it later.

Then, **in the same breath**, ask what the choices need:
- If the preset declares `requires: [anchor_date]` (`countdown-default`), ask for the date — "What's the
  launch date?" / "What's the event date?" — using the work pack's own `asks:` prompt when it has one.
  Write `phases.anchor_date`. Never guess it: every countdown milestone and deadline hangs off it.
- Ask each remaining `asks:` entry from the loaded packs' manifests, in pack order, writing each answer
  to its `key` on the intake record. Offer `options` as the choices when declared. Skip an optional one
  the operator leaves blank.

**Q1.6 — SR&ED (Canada only):**
> Is your organization Canadian, and does this project involve work that might qualify as Scientific Research or Experimental Development — meaning technical work where the outcome was genuinely uncertain and required systematic investigation?

**SR&ED is a capability, not a pack.** Do not add `sred-canada` to the pack list here — it is the
capability's *bundled* pack and is loaded by the capability's own enable step. What this question
decides is a single flag on the intake record, `sred_interest: yes | no | unsure`, which routes to
a handoff after Chapter 9.

- Yes → `sred_interest: yes`. Present: "Good — SR&ED gets its own short setup after this one,
  because it needs things this session doesn't ask for: your fiscal year end, the claimant's legal
  name, and a conversation about where your technical frontier actually is. It extends the
  substrate with uncertainty, experiment, and advancement records so the T661 is built from
  contemporaneous notes rather than reconstructed at year-end."
- No → `sred_interest: no`. Skip.
- Unsure → `sred_interest: unsure`. Present: "SR&ED eligibility is genuinely hard to call, and
  nothing here decides it — that's your advisor's determination. But if any of your technical work
  involved uncertainty you couldn't resolve by looking it up, it's worth capturing. Capturing
  commits you to nothing; not capturing is what loses claims. We can run the SR&ED setup after
  this and you can stop at any point."

**Do not ask for the fiscal year end here.** It is required, it gates the whole capability, and it
belongs to the session that can refuse without wasting this one.

**Q1.7 — Does this project end?**

**Pre-fill from the pack before asking.** Read `defaults.lifecycle` from the **primary work pack**
first, then the accountability packs selected above. That value is a *suggestion*, and it turns this from a blank-slate interview into a
confirmation pass — the same pattern as every other pre-filled chapter in this skill.

- Pack suggests `terminal` → present: "The [pack] pack assumes projects of this kind end — a deadline,
  a decision, a final report. Sound right?"
- Pack suggests `continuous` → present: "The [pack] pack assumes this kind of work keeps going —
  releases, renewals, or reporting that recurs. Sound right?"
- Packs disagree, or none declares one → ask the open question below with no pre-fill.

Then, whether confirming or asking cold:

> Does this project have an end date after which no further work is planned?

Ask in exactly those terms. Do **not** ask "is this terminal or continuous" — that is the model's
vocabulary, not the operator's, and it invites a guess.

- **Yes, it ends** → `phases.lifecycle: terminal`. Present: "Then the phase ladder fits as-is: one pass
  through to closeout and archive."
- **No, work continues** → `phases.lifecycle: continuous`, provided the chosen preset declares
  `cycles_back_to` on a phase. Present: "Then work will arrive in increments — v1, v1.1, next quarter's
  retainer. Each gets its own closure, and closing one opens the next instead of reopening a phase. The
  practical difference: your progress number will say how far through *this* increment you are, and
  closing an increment freezes its gate record instead of overwriting it."
- **Unsure** → **leave it unset and move on.** Present: "Then leave it — the default assumes an ending,
  and if work turns up after closeout the project will notice and ask you then." Do not press. An
  unanswered lifecycle is a supported, permanent state and the post-closeout diagnostic exists precisely
  so this question can be deferred at no cost.

**Never ask this question of a facility that already has a value** — re-orientation confirms, it does
not re-interview.

The preset from Q1.C usually settles it: on `stage-gate-default`, `countdown-default` or
`grant-default` (no `cycles_back_to`) the only possible answer is *it ends* — record `terminal` without
asking. On `cycle-default` the work pack suggests *continues*; confirm it.

If `project-scaffolder` already wrote `terminal` because a selected pack declares it, skip Q1.7 —
re-asking a settled question implies it is open. `sred-canada` is a capability pack and declares no
lifecycle default by design: it layers onto whatever shape the project already has, so it never
pre-fills this question and never suppresses it.


**Q1.8 — What timezone should scheduled work use?**

> Automation fires in a nightly window — 23:00 to 05:00 by default. In which timezone?

Ask for an IANA name (`America/Vancouver`, `Europe/Berlin`). Offer the machine's timezone as a
*suggestion to confirm*, never as an answer written without being seen: the facility's timezone is a
property of the PROJECT, not of whoever happens to run the command, and a facility worked on from two
machines in two zones would otherwise silently reschedule itself.

**Never skip this question and never substitute a default.** `manifest-v2.yaml` has marked
`automation.timezone` as REQUIRED since it shipped, while shipping the value as `~`, and no skill ever
collected it (FB-002). `project-automator` now refuses rather than guessing, so an unanswered question
here becomes a blocked automation run later — which is the intended trade: a 23:00–05:00 window
interpreted as UTC fires the nightly jobs at 4pm in Vancouver, and a schedule that is confidently
wrong is worse than one that will not start.

Write it to the working intake record as `automation.timezone`.

**Q1.9 — Which phase ladder?** Asked as Q1.C above. It exists because nothing wrote `phases.preset`
for the first ten weeks the presets existed (FB-003); Q1.C is where it is now written. Q1.C and Q1.7
interact: a preset that declares no `cycles_back_to` cannot host a `continuous` lifecycle. If Q1.7
answered "work continues" and Q1.C landed on a terminal preset, say so and ask which of the two to change
— do not silently resolve it.


**Confirmation:**
> Here's how I'll set this project up: a **[work type]** that reports to **[accountability]**, moving
> **[rhythm in plain words]**[, anchored on [date]]. Here's what each piece adds. Look right?

Present one row per axis: the work pack (with its preset, how many draft milestones and risks it will
queue), each accountability pack (its reports), the preset (its phases), and any capability hand-off
flagged (`sred_interest`). Confirm before proceeding.

**HTML artifact (Coworker):** Render three groups of OptionCard components in selected (green-bg) state —
Work, Who hears about it, How it moves — each card showing `picker.label` with its contribution beneath.
Add an [Advanced] OptionCard per group in unselected state. NavRow: [Back] [Confirm selection →].

**Markdown mode (Claude Code):** Present as a markdown table `| Axis | Choice | What it adds |`. Ask "Does
this look right? Reply with anything to change."

Write `work_type`, `accountable_to`, `phases.preset`, `phases.anchor_date` and the `asks` answers to the
working intake record. `packs_selected` is `[work_type, secondary work packs…, accountable_to…]`.

---

### Chapter 2 — Project Identity

**Prose to present:**

> Now let's establish the stable identity of this project — the facts that appear on every document the system generates.
>
> If your documents already answered some of these, I'll show you what I found and just ask you to confirm or correct.

**Collect the following, presenting extracted values first where available:**

| Field | What to ask | Notes |
|-------|-------------|-------|
| `project.short_name` | What's the short name or code for this project? | e.g., "Proj-001", "Project Volta" |
| `project.long_name` | What's the full formal title? | As it appears in the governing document |
| `project.one_liner` | In your own words — one or two sentences — what is this project? | Freeform. This is used in every public-facing document. Do not rewrite it. |
| `project.funder` / `project.customer` | Who is funding or commissioning this work? | Full organization name |
| `project.program` | What program or contract is this under? | e.g., "Consortium AI Program", "Federal Innovation Stream" |
| `governing_document` | What is the primary governing document? | MPA, SOW, Grant Agreement, etc. |
| `dates.project_start` | When does the project start (or when did it)? | YYYY-MM-DD |
| `dates.project_end` | When is the project expected to end? | YYYY-MM-DD |
| `budget.total_project_cad` | What is the total project budget, if you can share it? | Optional — leave blank if sensitive |

After collecting these: "Here's the project identity I've captured. Anything to change?"

Display a clean summary and wait for corrections.

---

### Chapter 3 — Document Drop (Second Invitation)

**Prose to present:**

> Before we go further, I want to make sure I've seen everything that's already written down about this project. Documents — even rough drafts — let me skip questions and give you better output.
>
> Specifically useful at this stage:
> - The governing document (MPA, SOW, grant agreement) — gives me milestones, stakeholders, budget, obligations
> - The original proposal or application — gives me the project rationale, technical approach, team
> - A milestone schedule or work plan — gives me the full milestone list with dates and owners
> - Any previous reports or claims — gives me format and tone reference
> - Any documents you'd like the system to produce outputs that look like — these go directly into references/examples/
>
> If you already shared everything, just say "nothing else" and we'll move on. No pressure — missing documents just means more questions.

**Collect:**
- Additional documents from the user
- Process new documents the same way as Chapter 0: extract structure, stage examples
- Update the extraction summary: "I've now seen: [complete list]. Remaining gaps: [list]."

**If no documents at all have been provided by this point:**
> That's completely fine. We'll build context through conversation. I'll offer to research any gaps at the end, and you can always add documents later — they'll update the substrate and improve output quality as you go.

---

### Chapter 4 — Stakeholder Mapping

**Prose to present:**

> The system routes reports and notifications to specific people in specific formats. To do that well, it needs to know who's involved — not just their names and roles, but enough about them to tailor communication.
>
> We'll map your key stakeholders. You don't need to be exhaustive — just the people who receive outputs from this project.

**For each stakeholder, collect:**

Ask conversationally — not as a form. Example opening: "Let's start with the people inside your organization. Who is the Project Lead — the person ultimately responsible for this project?"

Collect for each person:
- Name + organization
- Role in the project (not just title — what do they do in relation to this project)
- What they receive (which reports, at what cadence)
- Any communication preferences the user knows about ("she prefers bullet points", "he wants technical depth", "they only read the executive summary")
- Contact information (email, Slack handle) — optional

**Do not interrogate every possible field.** Ask for the most important people first:
1. Project Lead (internal)
2. Finance Representative
3. Funder/Customer contact (if applicable)
4. Any pack-specific required roles (e.g., funder PM for pic-pcais). The SR&ED advisor is asked for by `sred-onboarding`, not here.

After the main contacts: "Are there any other people or organizations who receive reports or need to be informed about this project?"

Write each stakeholder as a record in the working intake — they will become entries in `manifest.yaml:consortium.members` and `reporting-matrix.yaml` stakeholder entries.

---

### Chapter 5 — Milestone Capture

**Prose to present:**

> Milestones are the spine of the system. They drive status reports, review meetings, claims where there's a funder, and the project tracker. If you have a milestone schedule, this chapter is short. If not, we'll build one together.

**If the work pack ships milestone seeds** (`packs/<work_type>/seeds/milestones.yaml`): resolve their date
expressions against the start, end and anchor dates captured so far and present them as the starting
list — "For a [label], projects usually hit these. Keep, change, or drop any?" Merge with anything
extracted from documents (a document's milestone outranks a seed with the same meaning). An undateable
seed is shown undated with the missing date named, never guessed. These are still DRAFTS: Chapter 8's
`seed-pack` queues the pack's seeds for review, and what the operator confirmed here is queued alongside.

**If milestones were extracted from documents:** Present the extracted list and ask for confirmation + corrections. "Here are the milestones I found. Do they look right? Any missing, renamed, or reordered?"

**If no milestones were extracted:** Ask conversationally:

> What are the main deliverables or phases of this project? Walk me through what needs to get done, roughly in order.

For each milestone mentioned, collect:
- `title` — as the user describes it
- `owner_org` — which organization owns this deliverable
- `planned_end` — target completion date
- `completion_criteria` — how will you know it's done? (accept prose, summarize if long)
- `description` — brief description of what it involves

After: "Here's the milestone list I've built. Does the sequence and ownership look right?"

**If `sred_interest` is `yes` or `unsure`:** After milestone confirmation, ask:
> For each of these milestones, did the work involve genuine technical uncertainty — outcomes that
> weren't known in advance and required systematic investigation?

Flag those milestones `sred_candidate: true` and carry the list forward on the intake record.
`sred-onboarding` uses it as the raw material for its frontier walk (Chapter 4) and first
uncertainty capture (Chapter 5).

Name the flag `sred_candidate`, not `sred_eligible` — nothing in this session can determine
eligibility, and a field named `eligible` will be read as a determination by the next person who
opens the file.

---

### Chapter 6 — Examples

**Prose to present:**

> The system can generate technically correct reports from the data it holds. But "technically correct" and "actually useful" are different things — the gap is knowing what GOOD output looks like for this specific project. A couple of examples to model goes a long way.
>
> (Goals are **not** set here. Your objectives and the KPIs that prove them live in the dedicated **Goals tab** — a structured objectives + KPIs feature. If you want to define goals, do it there; this chapter is only about example outputs.)

**Do NOT** ask about, create, or infer objectives, KPIs, or any "goals" here. Never write `references/goals.md`. If the user volunteers goals, acknowledge and point them to the Goals tab.

**Question 6.1 — Positive examples:**
> Do you have any examples of output you'd want to model? This could be a past report you thought was excellent, a claim document that worked well, a weekly update that people actually read, a presentation that landed — anything where you thought "that's what I want." Share it here, or describe it.

- If files are shared: save to `references/examples/good/` with a brief metadata header noting what it is
- If described in prose: save the description to `references/examples/good/described-examples.md`
- If nothing: "No problem. You can add examples at any time — the system will pick them up."

**Question 6.2 — Negative examples or anti-patterns:**
> Is there anything you want to avoid? A format that doesn't work for your audience, a tone that feels wrong, a type of output that's been criticized? Even "don't sound like a government form" is useful.

- Save any anti-patterns to `references/examples/avoid/anti-patterns.md`
- If nothing: skip.

**After collecting both:** Save the examples as freeform markdown exactly as provided — they are orientation documents, not data. Do not extract structured fields. Never create objectives/KPIs or `references/goals.md` from this chapter.

---

### Chapter 7 — Gaps and Synthesis

**Prose to present:**

> Here's what I have so far, and here's what's still missing.

Present a structured gap report:

```
CAPTURED (from documents and conversation)
──────────────────────────────────────────
✓ Project identity: [fields captured]
✓ Packs: [confirmed list]
✓ Stakeholders: [N records]
✓ Milestones: [N records]
✓ Goals: [yes/no]
✓ Examples: [N examples]

GAPS (not yet captured)
──────────────────────────────────────────
○ [field or category] — needed for [which outputs it affects]
○ ...

SYNTHETIC CONTENT OFFERED
──────────────────────────────────────────
[List any gaps where synthesis could help, with a description of what would be generated]
```

**HTML artifact (Coworker):** Render the CAPTURED section as a list of StatusRow components (✓ green prefix). Render each gap as a GapRow with three inline action buttons: [Provide now] [Leave gap] [Synthesize]. Render a synth-notice (amber) beneath any gap where synthesis is offered. NavRow: [Back] [Continue →].

**Markdown mode (Claude Code):** Render the gap report as the code block shown above. After the block, ask for each gap in sequence: "For [field]: provide now, leave blank, or want me to synthesize a starting point?"

**For each gap, offer one of three paths — ask before doing anything:**

**Path A — User provides now:** "Can you fill this in now?" [answer → capture]

**Path B — Leave as gap:** "We can leave this blank and fill it later. [Field] affects [specific outputs] — those will be incomplete until it's added." [confirm → mark as gap in manifest]

**Path C — Research and synthesize:** "I can research this and generate a synthetic starting point — it will be clearly labeled as synthetic, and you can correct it at any time. It's a starting point, not a source of truth. Want me to try?"
  - If yes: research and generate, save with `synthetic: true` header and a note explaining what it's based on
  - If no: leave as gap

**Never synthesize without asking.** Never present synthetic content as equivalent to user-provided content.

**Synthesis quality note (present when offering synthesis):**
> A note on synthetic content: the system can generate plausible-sounding context based on what it knows about [project type / funder / industry]. But it won't know your organization's history, your team's preferences, your funder's quirks, or your project's specific rationale. Synthetic content is useful as a starting point to react to — it is not a substitute for real context.

---

### Chapter 8 — Initialize

**Prose to present:**

> We're ready to initialize. Here's a summary of what will be created.

Present a complete pre-flight summary:

```
WILL CREATE
──────────────────────────────────────────
manifest.yaml              — [N fields populated, N from documents, N from conversation, N synthetic]
reporting-matrix.yaml      — seeded from: [pack list] (project-scaffolder seed-pack)
outbox/queue/*-seed-*      — [N draft milestones, N draft risks] from [work pack], for review
milestones/                — [N milestone files]
stakeholders/              — [N stakeholder records] (written into manifest)
references/examples/      — [present/absent]
references/examples/       — [N examples in good/, N in avoid/]
references/context.md      — [present if synthesis was accepted / absent]

PROJECT TYPE
──────────────────────────────────────────
Work:            [work pack label]  (project.kind: [id])
Who hears:       [accountability pack labels]
How it moves:    [preset] [· anchored on YYYY-MM-DD]
Packs loaded:    [packs_selected, one-line role each]

SYNTHETIC CONTENT (will be labeled)
──────────────────────────────────────────
[list any synthetic fields or documents]
```

**HTML artifact (Coworker):** Render each section (WILL CREATE / PACKS LOADED / SYNTHETIC CONTENT) as a group of SummaryRow components. Source badges (document / conversation / synthetic) appear inline on each row. Synthetic rows are highlighted with amber-bg. A single large [Initialize project-state/ →] button with a warning note beneath: "This creates the project-state/ directory. Nothing is permanent except the activity log." NavRow: [Back] [Initialize →].

**Markdown mode (Claude Code):** Render the pre-flight summary as the code block shown above. Ask: "Ready to initialize? Type 'yes' to proceed."

Ask for explicit confirmation: "Ready to initialize? This will create the `project-state/` directory structure. You can always add to it — nothing is permanent except the activity log."

**On confirmation:** Call `project-scaffolder` with all captured inputs, passing the working intake record as structured input. Do not re-ask questions that have already been answered.

**Build output (after initialization):** Render a StatusRow list of every file/directory created (✓ prefix + path). Then transition directly to Chapter 9.

Report on what was created: "Initialized. Here's what's in `project-state/` now."

---

### Chapter 9 — Orientation Check

**Prose to present:**

> Let's do a quick check to confirm the system knows what it needs to know.

Run the following checks and present results:

**Check 1 — Identity:** Can the system answer "what is this project" from the manifest? Present the one-liner + funder + phase.

**Check 2 — Milestones:** Show the milestone list with statuses. "Are any of these wrong or missing?"

**Check 3 — Stakeholders:** Show the routing table: "who receives what." Verify at least one recipient per pack's primary report type.

**Check 4 — Orientation quality:** Rate the orientation on three dimensions:
- **Grounding** (0–3): 0 = no documents, 1 = some documents, 2 = governing document + proposal, 3 = full document set
- **Goals clarity** (0–3): 0 = no goals captured, 1 = brief description, 2 = detailed goals + anti-patterns, 3 = goals + positive + negative examples
- **Stakeholder depth** (0–3): 0 = no stakeholders, 1 = names only, 2 = names + roles, 3 = names + roles + preferences

**HTML artifact (Coworker):** Render the orientation quality as three QualityBar components inside a ChapterCard. Each bar shows label, filled-block graphic (█░), and score. Add an overall summary line beneath. Then render suggested next steps as OptionCard components (each clickable to trigger the corresponding action). NavRow: [Done].

**Markdown mode (Claude Code):** Render as the code block below:

```
Orientation quality
───────────────────
Grounding:    ██░  2/3 — governing document seen; proposal not provided
Goals:        ███  3/3 — goals, positive examples, and anti-patterns captured
Stakeholders: █░░  1/3 — names captured; preferences not yet known

Overall: Good starting point. Outputs will improve as grounding increases.
```

**Check 5 — Suggested first actions:** Based on gaps, offer 2–3 concrete next steps:
- "Add your proposal document to improve milestone extraction"
- "Update M03 with percent_complete — it's currently at 0%"
- "Run `project-orchestrator` to see what's due this week"

**Closing:**
> Setup complete. The system is oriented and ready. You can always improve orientation by adding documents, updating goals, or adding examples — run `project-onboarding re-orient` to revisit any chapter without starting over.

### Capability handoff

If the intake record carries `sred_interest: yes | unsure`, offer the handoff **after** the closing
— not before. This session is complete on its own, and SR&ED setup is a separate decision the
operator should be able to defer without feeling they left the project half-configured.

> You flagged SR&ED earlier. That's a separate short setup — seven chapters, about fifteen minutes
> — because it needs things this session didn't ask for: your fiscal year end, the claimant's legal
> name, and a real conversation about where your technical frontier is. Run it now, or any time
> with `/sred-onboarding`.

If they say yes, invoke `sred-onboarding`, passing the intake record so it can pre-fill from the
`sred_candidate` milestones instead of interviewing cold. If they defer, say so plainly and stop —
`project-orchestrator` will not nag about a capability that was never enabled.

The same pattern applies to any other capability flagged during the project-type chapter. Onboard the
project first; layer capabilities after.

---

## Re-orientation mode

When the user says "re-orient project-state" or runs `project-onboarding re-orient`:

1. Run Chapters 6 and 7 only (goals + examples + gap check)
2. Offer to revisit any other chapter by name
3. Do not re-run initialization unless the user explicitly asks
4. **Offer a work type once, if the facility has none** (decision D5). When `project.kind` is not the id
   of a loaded `axis: work` pack — a legacy value like `grant_consortium`, or absent — run Q1.0 as a
   *proposal*: "This project has no work type. From its manifest and milestones it reads like a
   **[label]** — want me to add it? That would add [N] matrix entries and queue [N] draft milestones for
   review; nothing existing changes." On yes, append the pack to `packs_loaded`, set `project.kind`,
   and run `project-scaffolder seed-pack`. On no, record nothing and do not ask again this session. Never
   change `phases.preset` as a side effect — a live facility's ladder moves only through
   `project-phase-gate set_preset`.

Re-orientation is appropriate when:
- The project has changed significantly
- New documents are available
- Output quality has degraded and the user wants to improve it
- A new pack is being added mid-project

---

## Working intake record

Throughout the onboarding, maintain a working intake record in memory. This is not written to disk until Chapter 8. It accumulates all captured inputs with source attribution:

```yaml
intake:
  session_date: "YYYY-MM-DD"
  operator: "user@email"

  work_type: ~            # primary axis:work pack id → project.kind   (PROJECT-TYPES-SPEC §4)
  secondary_work: []      # optional extra work packs (matrix + seeds only, never the preset)
  accountable_to: []      # axis:accountability pack ids; [] == "just me"
  packs_selected: []      # [work_type, secondary_work…, accountable_to…] → project.packs_loaded
  phases:
    preset: ~             # Q1.C
    anchor_date: ~        # Q1.C, when the preset requires it
  asks: {}                # dotted manifest key → answer, from the packs' asks: blocks

  project:
    short_name: {value: "...", source: "document|conversation|synthetic"}
    long_name: {value: "...", source: "..."}
    one_liner: {value: "...", source: "..."}
    # ... all fields with sources

  stakeholders:
    - name: "..."
      source: "document|conversation"
      # ...

  milestones:
    - title: "..."
      source: "document|conversation"
      # ...

  documents_provided:
    - type: "governing_document"
      reference: "path or description"
      extraction_summary: "..."

  goals_captured: true|false
  examples_captured: true|false
  anti_patterns_captured: true|false

  gaps:
    - field: "..."
      resolution: "left_blank|synthetic|will_provide_later"
```

---

## Output to substrate

On initialization (Chapter 8), write:

| File | Contents |
|------|----------|
| `project-state/manifest.yaml` | All project identity, dates, budget, consortium, phases, packs_loaded, surfaces — from intake record |
| `project-state/reporting-matrix.yaml` | Seeded from packs via `project-scaffolder seed-matrix` |
| `project-state/milestones/M<NN>-<slug>.yaml` | One file per captured milestone — always set `status: planned` on new milestones |
| `project-state/references/examples/` | Example outputs to model (good/) and anti-patterns (avoid/) from Chapter 6 |
| `project-state/references/examples/good/` | Any positive example documents or descriptions |
| `project-state/references/examples/avoid/anti-patterns.md` | Any negative examples or anti-patterns |
| `project-state/references/context.md` | Synthetic context if generated (always labeled `synthetic: true` at top) |
| `project-state/references/documents-index.md` | Index of all documents provided: type, reference, what was extracted, what was not |
| `project-state/references/onboarding-intake.yaml` | The full working intake record — audit trail of how the substrate was built |
| `project-state/state.json` | Initial health, counters, current phase |
| `project-state/logs/activity.ndjson` | First entry: `onboarding.completed` with summary |

---

## Discipline rules

- **Never skip chapters.** Each chapter builds on the previous. Offer to accelerate ("I can move quickly through this if you want"), never silently omit.
- **Never auto-synthesize.** Always ask before generating synthetic content. Always label synthetic content when generated.
- **Never paraphrase goals or examples.** Chapter 6 content is saved exactly as provided. Its value is the user's voice, not a cleaned-up version of it.
- **Never invent milestone names or stakeholder contacts.** If the user says "there are five milestones but I can't remember the exact names," capture "five milestones, names TBD" rather than generating plausible names.
- **Never present orientation as complete when it isn't.** The orientation quality card in Chapter 9 must be honest. A 1/3 grounding score should say 1/3.
- **Documents take precedence over conversation, which takes precedence over synthesis.** When the same field has multiple sources, use the highest-fidelity one and note the others.
- **Preserve source attribution.** Every field in `manifest.yaml` that came from a document should have a comment noting it. Every synthetic field must be labeled.

## Integration

- **project-inbox** — called in the Inbox Orientation pre-check (before Chapter 0) when unprocessed documents are present; generates `references/inbox-orientation.yaml` that pre-fills Chapters 2, 4, and 5
- **project-scaffolder** — called in Chapter 8 with the intake record as input; handles directory creation and manifest writing
- **project-state** — all substrate writes route through it; onboarding.completed logged to activity log
- **project-milestone-manager** — milestone records created from Chapter 5 intake
- **sred-onboarding** — handed off to after Chapter 9 when `sred_interest` is `yes` or `unsure`; consumes the `sred_candidate` milestone flags from Chapter 5
- **project-orchestrator** — referenced in Chapter 9 suggested actions
- **project-doc-suite** — benefits directly from references/examples/ in orientation quality

## Reference files written

- `references/examples/` — example outputs the user wants to model (good/) and anti-patterns to avoid (avoid/). Goals (objectives + KPIs) are set in the Goals tab, not here.
- `references/examples/good/` — positive output examples and descriptions
- `references/examples/avoid/anti-patterns.md` — formats and patterns to avoid
- `references/context.md` — synthetic context (if generated)
- `references/documents-index.md` — what was provided and what was extracted
- `references/onboarding-intake.yaml` — full audit trail of the onboarding session
