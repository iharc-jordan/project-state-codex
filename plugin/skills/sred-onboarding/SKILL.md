---
name: sred-onboarding
description: "Guided onboarding for the Canadian SR&ED capability. Runs seven chapters: claimant identity (legal name, Business Number, fiscal year end), advisor engagement, capability enablement, the capture lens (Layer 2 innovation criteria), first uncertainty capture from real in-flight work, evidence-source wiring, and an orientation check that ends on a real filing date. Refuses to enable without a fiscal year end — every SR&ED deadline is computed from it. Writes through project-state's capability enable verb; delegates the criteria interview and TU capture to project-sred-tracker. Never asserts eligibility and never files. Use when the user says 'set up SR&ED', 'onboard SR&ED', 'enable SR&ED', 'turn on SR&ED tracking', 'start capturing SR&ED', 'we want to claim SR&ED', 'get us ready for the T661', 'how do we start with SR&ED', or when project-onboarding hands off after the operator answers yes to the SR&ED question."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# SR&ED Onboarding

## Purpose

Take an operator who has just installed the plugin and knows they *probably* have an SR&ED
claim, and leave them with: the capability enabled, a real filing deadline on screen, a
declared capture lens, and at least one technological uncertainty recorded against work that
is actually running.

The hard part of SR&ED is not the schema — it is knowing what counts. This session's centre of
gravity is Chapter 4, the capture lens. Everything before it exists to make that conversation
possible; everything after it exists to make the lens operational.

**This skill is the front door. It is not the SR&ED system.** Capture, gap analysis, digests and
reviews belong to `project-sred-tracker` and `project-sred-reviewer`. This runs once (and again
on re-orientation), then gets out of the way.

## Hard rules (inherited from the capability, non-negotiable)

1. **Never assert eligibility.** This system captures and structures. Eligibility is a qualified
   SR&ED advisor's determination and CRA's decision. Say so plainly whenever the operator asks
   "does this qualify" — the honest answer is "it is worth recording; the advisor calls it."
2. **Never file.** The terminal artifact is always a draft handed to a human.
3. **Never invent.** No fabricated uncertainties, experiments, results, or dates. If the
   operator's answer is thin, ask again or leave the field empty. An empty field is recoverable;
   a plausible invention in a T661 is an audit finding.
4. **Contemporaneity is the claim.** A TU recorded before the work is defensible; one backdated
   to match the narrative is the thing CRA looks for. Never suggest backdating, and when the
   operator describes past work, record the real dates and mark it back-filled.
5. **Field-relative, never company-relative.** The standard-practice test is field-level.
   "New to us" is explicitly ineligible. Rewrite company-relative framing on the spot, every
   time, citing the Layer 0 rule.

## Trigger phrases

- "set up SR&ED" / "onboard SR&ED" / "enable SR&ED"
- "turn on SR&ED tracking" / "start capturing SR&ED"
- "we want to claim SR&ED" / "get us ready for the T661"
- "how do we start with SR&ED"
- Handoff from `project-onboarding` when the operator answers yes to the SR&ED question

## Presentation protocol

Follow the shared Markdown protocol in `project-onboarding`: seven progress
segments, attributed pre-filled values, grouped unresolved questions, summaries,
status rows, and explicit confirmation before writes.

One deviation: **the deadline strip is red-bg, not green.** Once Chapter 3 computes a real
filing date, render it at the top of every subsequent chapter. It is the only number in this
session the operator cannot recover from missing.

## Pre-check

Before Chapter 1:

1. **Is there a substrate?** Walk up for `project-state/`. If none, stop and hand off:
   "SR&ED layers onto a project. Let's set the project up first — run `/project-onboarding`,
   then come back." Do not scaffold a project from here.
2. **Is `sred` already enabled?** Read `manifest.yaml → capabilities.sred` via `project-state`.
   - Enabled → this is a **re-orientation**, not a first run. Skip to a summary of current
     state (FYs open, criteria status, TU/EX/ADV counts) and offer the chapters individually.
     Never re-interview a settled question; re-orientation confirms.
   - Present but `enabled: false` → the capability was disabled. Show when and why from the
     activity log before offering to re-enable.
3. **Does `sred/` already exist?** Enable adopts an existing tree — never overwrite. If records
   are already there, say what was found and carry it forward.
4. **Is the inbox non-empty?** If `documents/inbox/` has files, note it; technical documents
   there are the best raw material for Chapter 4 and Chapter 5. Offer to run `project-inbox`
   triage first.

---

## Chapter 1 — Claimant identity

The claimant is a **legal entity filing a T661**, which is often not the same name as the
project. Ask in those terms.

> **Q1.1** What is the legal name of the entity that will file the claim?

> **Q1.2** What is its Business Number (BN)? The T661 project summary needs it.
> If you don't have it to hand, we can leave it as TODO and fill it before the draft.

BN is genuinely deferrable — it is needed at draft time, not at capture time. Accept `TODO`
without friction.

> **Q1.3** When does the fiscal year end?

**This question gates the entire session.** Every SR&ED date — the 18-month hard deadline, the
15-month target, the cost-categorization lead window, the narrative-draft window — is computed
from it. Accept a month and day (`December 31`), normalize to `--MM-DD`, and read it back in
words.

**If the operator does not know:** stop. Do not guess, do not assume December 31 because it is
common, and do not proceed with a placeholder. Say:

> I can't set this up on a guess — every deadline in the system is computed from this date, and
> a wrong one would put a confidently incorrect filing deadline on your dashboard. Find it on
> last year's T2 return or ask your accountant, and we'll pick up right here.

Then exit cleanly, having written nothing.

> **Q1.4** What is the default field of science for this work?
> Most software work is `2.02.09` — computer and information sciences, software engineering.
> Offer that as a pre-fill; take a correction if the work is materials, process, or other.

**Chapter 1 output:** `claimant_org`, `claimant_bn`, `fiscal_year_end` (`--MM-DD`),
`field_of_science_default`. Held in the working intake record — nothing is written yet.

---

## Chapter 2 — Advisor

> **Q2.1** Do you already work with an SR&ED consultant or tax advisor?

- **Yes** → capture name and contact. Set `advisor.engaged: true`. Present:
  "Good — they'll receive the handoff bundle as a Gmail draft about two months before your
  deadline, and they should be in the room for Chapter 4 if that's possible."
- **No** → `advisor.engaged: false`, contact null. Present this honestly:
  "That's fine to start — capture is worth doing regardless. But this system drafts and
  reviews; it never files and never rules on eligibility. You'll want an advisor engaged
  before the claim goes in, and the orchestrator will start reminding you when your deadline
  is inside six months."
- **Not sure / considering** → treat as No. Do not press.

Do **not** recommend a specific firm.

---

## Chapter 3 — Enable

Now write. Call `project-state` **enable `sred`**, passing the Chapter 1 and 2 values. That verb
owns the whole sequence — manifest block, schema directories, `state/sred.json` with computed
dates, event vocabulary, matrix seeding from `sred-canada`, and `project-automator update` to arm
the schedule.

Do not write any of that from here. If `enable` refuses for a missing required key, surface its
message and return to the chapter that owns that field.

**Then show the operator what just happened, in dates, not promises:**

```
✓ SR&ED enabled for <claimant_org>

  Fiscal year ends        <Month DD>
  Current claim year      FY<YYYY>  (ends <YYYY-MM-DD>)
  Target filing date      <YYYY-MM-DD>   (FY end + 15 months)
  Hard deadline           <YYYY-MM-DD>   (FY end + 18 months — after this the claim is forfeited)

  Created  sred/uncertainties/ · sred/experiments/ · sred/advancements/
           sred/evidence-log.ndjson · sred/cost-tracking/ · sred/inbox/
  Seeded   <n> reporting-matrix entries
  Armed    next scheduled task: <entry> on <date>
```

Say the forfeiture consequence in plain words once, here, and do not repeat it every chapter:
missing the hard deadline does not delay the claim, it ends it.

---

## Chapter 4 — The capture lens

**This is the chapter that matters.** Everything else is plumbing.

Frame it before asking anything:

> SR&ED is not a record of everything your engineers did. It is a record of the work where the
> field's standard practice ran out and you had to experiment to find out what happened. Most
> teams get this wrong in one of two directions — they claim everything, which fails audit, or
> they claim nothing, because the work felt like ordinary engineering at the time.
>
> So before we record anything, let's declare where *your* frontier is. That declaration becomes
> the lens: it decides what gets flagged for capture, what the harvester watches for, and what
> the weekly digest calls out as uncaptured.

Then **delegate to `project-sred-tracker` `define_criteria()`**. That op owns the interview — the
frontier walk, the routine boundary, the harvester hints, and the framing check against the
Layer 0 baseline and the company Layer 1 profile. Do not reimplement it here.

Two things this skill adds around the delegation:

**Before:** if an advisor was recorded in Chapter 2 and is not present, say so —
"this interview is materially better with them in the room; we can do it now and refresh it
with them later, or wait." Let the operator choose. Both are fine.

**After:** the file lands `status: draft`. Explain what draft means and what flips it:
draft is fully operational — the lens works immediately — but it needs PL sign-off to become
`reviewed`, and the orchestrator will nudge after 30 days. Criteria changes are logged and
dated because **criteria drift is audit-relevant**.

**Watch for company-relative framing throughout and correct it in the moment.** When the
operator says "this was new to us," reflect it back:

> That's the framing CRA rejects — "new to us" is explicitly ineligible, because the test is
> field-level. The question is whether a competent professional in this field, with the
> published literature and available tools, would have known the answer. Was this genuinely
> unestablished, or was it established somewhere you hadn't looked?

Sometimes the honest answer is the second one. Record that as declared-routine and move on —
a narrower, defensible lens is worth more than a wide one.

---

## Chapter 5 — First uncertainty

A capture lens with nothing behind it decays. Ground it immediately.

> Looking at the frontier areas you just named — is there work running right now, or starting
> soon, that lands in one of them?

For the first one or two (not more — this is a start, not a backlog):

1. Delegate to `project-sred-tracker` `record_uncertainty()`.
2. Link it to the candidate area and to any in-flight milestones.
3. If the work has already started, record the **real** `work_start_date`. Do not adjust it to
   look better. If `identified_date` is genuinely today because the uncertainty is only being
   documented now, record today and note the back-fill — an honest late record beats a
   fabricated early one, and CRA can tell the difference.

**If nothing is currently in a frontier area**, that is a legitimate outcome. Do not manufacture
a TU to fill the chapter. Say:

> Then we've done the right thing in the right order — the lens is declared and the system will
> flag work as it lands in those areas. Nothing to record yet.

**If the operator wants to capture past work**, record it accurately with real historical dates
and flag the contemporaneity weakness plainly: reconstructed records are claimable but weaker,
and the advisor should know which records are which.

---

## Chapter 6 — Evidence sources

The capture lens named `harvester_hints` in Chapter 4. Confirm they resolve to real places.

> **Q6.1** Which repositories hold the frontier work?
> Read the default from `manifest.yaml → surfaces.github.repos` and confirm rather than ask cold.

> **Q6.2** Is there a Jira project or Confluence space where this work is tracked or written up?

> **Q6.3** Which Slack channels is the technical discussion actually in?

Explain the tiering once, because it changes what the operator should expect:

> Commits, pull requests, CI builds, Jira issues and Confluence pages are **Tier 1** — they carry
> server-side timestamps and version history, which is what makes them defensible. A failed CI
> build is genuinely good evidence: it is a dated record of a trial that did not work.
> Slack and Docs are **Tier 2** — corroborating, captured as excerpt plus permalink.
>
> Nothing is ever added to the evidence log automatically. The harvester proposes into
> `sred/inbox/` and you confirm. That is deliberate: an auto-appended log is a log nobody stands
> behind.

Write confirmed sources back into `sred/criteria.yaml` via the tracker.

---

## Chapter 7 — Orientation check

Close by showing the operator the running system, not a summary of the conversation.

```
SR&ED — <claimant_org>

  Status          ✓ enabled, capturing FY<YYYY>
  Hard deadline   <YYYY-MM-DD>  (<n> days)
  Capture lens    <n> frontier areas declared · status: draft
  Captured        <n> TU · <n> EX · <n> ADV
  Watching        <n> repos · <n> Jira projects · <n> Slack channels

What happens without you doing anything:
  • Milestone completions trigger an SR&ED check
  • Monday: weekly capture digest — what was caught, what's going stale
  • Quarterly: completeness review and gap analysis
  • <lead date>: cost categorization comes due
  • <draft date>: T661 narrative draft (Sections E/F/G)
  • <review date>: audit-risk review — a weak verdict blocks advisor handoff
  • <handoff date>: advisor bundle, as a Gmail draft. You send it. You file it.

What to do next:
  • Log evidence as work happens — "log SR&ED work on EX-01, two of three approaches failed"
  • Get the criteria signed off to move them out of draft
  • Ask "what should I do today" any time — SR&ED items are in the same list as everything else
```

Then one closing statement, said once and meant:

> One thing to be clear about, because it does not change: this system drafts and reviews. It
> never files, and it never decides that your work is eligible. Those are your advisor's calls
> and CRA's. What it does is make sure that when they ask what happened and when, you have a
> dated, contemporaneous answer instead of a reconstruction.

Log `capability.onboarded` with `{capability: sred, chapters_completed, criteria_areas, tu_seeded}`.

---

## What this skill does NOT do

- **Does not write the manifest or scaffold directories.** That is `project-state` `enable`.
- **Does not run the criteria interview or capture entities.** That is `project-sred-tracker`.
- **Does not review narratives.** That is `project-sred-reviewer`.
- **Does not set up the project.** That is `project-onboarding` / `project-scaffolder`.
- **Does not rule on eligibility, recommend an advisor, or file anything.** Ever.

## Integration

- **project-onboarding** — hands off here when the operator answers yes to the SR&ED question
- **project-state** — `enable sred`; all state reads and writes
- **project-sred-tracker** — `define_criteria()`, `record_uncertainty()`
- **project-automator** — armed by `enable`; no direct call from here
- **project-orchestrator** — composes `capabilities/sred/routine.yaml` from the next tick on
- **project-inbox** — optional pre-check triage of `documents/inbox/`
