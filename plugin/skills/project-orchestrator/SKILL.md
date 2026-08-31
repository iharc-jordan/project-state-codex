---
name: project-orchestrator
description: "Read-only-by-default conductor for Project State. Rank what needs attention from canonical state, locally configured calendars, enabled capabilities, and due matrix entries. Use for what-next, deadline, daily/weekly routine, or orchestration requests. Invoke a generator only after explicit operator acceptance, a due enabled reporting-matrix entry, or an active pack's required trigger, and dispatch one report owner once per source event and period."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Orchestrator

## Purpose

Be the agent that notices what time it is, what state the project is in, and what
the sensible next action is. The orchestrator reads and recommends by default;
other skills act only through the invocation gates below. A normal invocation
produces one prioritized list rooted in canonical state and configured calendars,
not a fixed routine or a fan-out of generators.

Before invoking a mutating or generating skill, require one of:

1. explicit operator acceptance of the proposed action;
2. a due, enabled `reporting-matrix.yaml` / `automation/tasks.yaml` entry; or
3. a required trigger declared by an active pack.

For one source event and reporting period, select one owner and invoke it once.
Suggestions, quiet checks, disabled matrix entries, unconfigured surfaces, and
inactive capabilities remain read-only.

It is thin. It knows the *rhythm* of a grant project; the details live in the other skills.

## Trigger phrases

- "what should I do today / this week"
- "run the project" / "run the orchestrator"
- "morning briefing" / "daily briefing"
- "what's pending" / "what needs attention" / "what's on deck"
- "are there any deadlines coming up"
- "kickoff the day" / "kickoff the week"
- "run the weekly routine"

## The cadence model

Grant projects run on overlapping clocks:

| Clock        | Events                                                       |
| ------------ | ------------------------------------------------------------ |
| Daily        | (optional) standup, inbox check, at-risk milestone review    |
| Weekly       | Monday weekly report; at-risk escalation; mid-week milestone check-ins |
| Monthly      | Monthly technical brief (best practice per PIC PM Guide)     |
| Quarterly    | SC meeting; claim submission (20th of Apr/Jul/Oct/Jan); financial reporting |
| Annual       | PIC Annual Questionnaire; annual risk assessment; financial update |
| Phase        | Gate polling; transition readiness; kickoff/closeout rhythms |
| Event-driven | MPA signature; milestone completion; Change Order raised; IP disclosure; publication proposal; risk materialization |

The orchestrator knows roughly when each clock ticks and offers the right next action.

## The decision loop

On invocation:

1. **Load state.** Get current phase, health, recent activity, pointers (last_weekly_report, last_sc_meeting, last_claim_submitted, next_claim_due, next_sc_meeting).
2. **Compute windows.**
   - Days since last weekly report. If ≥7, flag "weekly due".
   - Days to next claim due date (Apr/Jul/Oct/Jan 20). If ≤14, flag "claim due soon". If ≤3, flag "claim due URGENT".
   - Days to next SC meeting. If ≤14, flag "SC pack prep". If ≤7, flag "SC pack due".
   - Days to annual questionnaire (if set).
3. **Check at-risk milestones.** Via `project-milestone-manager`. Any with `status in {at_risk, blocked}` or behind-schedule rules get flagged.
4. **Check gate.** Via `project-phase-gate`. If the current phase has unblocked items (e.g., MPA landed → planning.mpa_signed autoclose), surface the transition option.
5. **Check inbox.** If `documents/inbox/` is non-empty, flag "classify N new docs".
6. **Compose enabled capabilities' routines.** See "Capability routines" below.
7. **Prioritize.** Order: URGENT deadlines → gate-blocking items → pending reports → at-risk milestones → routine work → opportunities. Capability items rank by their declared `severity` alongside core items — they are not a separate section and never get their own digest.
8. **Return a ranked list** with, for each item: the reason, the skill that handles it, and what the user needs to do.

## Output format

```
# Orchestrator — YYYY-MM-DD

## 🔴 Urgent
- <items that cannot wait>

## 🟡 This week
- <items due in 7 days>

## 🟢 On deck
- <items on the weekly horizon>

## 💤 Quiet
- <nothing to flag here>

---
What would you like to do first?
```

Every line links to the skill that handles it, so the user can say "yes, do the weekly report" and the orchestrator delegates to `project-status-reporter`.

## Capability routines

A capability plugin (`sred`, `tender-intelligence`) knows a rhythm the core orchestrator does not.
Rather than shipping its own orchestrator — which would duplicate this calendar logic and give the
operator two competing answers to "what should I do today" — a capability ships
`capabilities/<id>/routine.yaml`, and this skill composes it.

**Step 6 of the decision loop:**

1. Read `manifest.yaml → capabilities`. For each entry with `enabled: true`, load
   `capabilities/<id>/routine.yaml`. A capability that is disabled, or has no routine file,
   contributes nothing — skip it silently.
2. Read the capability's runtime state (`routine.state.runtime`, e.g. `state/sred.json`) once.
3. Evaluate each `checks[]` entry's `when:` condition against that state and the substrate.
   A check whose condition does not hold produces nothing. Conditions are read-only — evaluating
   the routine must never write.
4. Emit each firing check as a digest item at its declared `severity`
   (`urgent` → 🔴, `soon` → 🟡, `ondeck` → 🟢), interpolating `{...}` placeholders from state,
   carrying its `action:` and its `handler:` skill.
5. If the routine declares `always_surface:`, render it as standing context at the top of the
   digest whenever its `suppress_when:` does not hold. This exists for hard external deadlines —
   an SR&ED filing window is unforgiving and must be visible on a day when nothing else fires.
6. If no check fired and `quiet_when:` holds, report `quiet_message` under 💤. **Do not
   manufacture an item.** A capability with nothing to say is a healthy result, and inventing
   busywork to fill the section trains the operator to skip the digest.

**Ordering discipline.** Capability items interleave with core items by severity. A 🔴 SR&ED
deadline outranks a 🟡 weekly report; a 🟢 SR&ED quarterly nudge sits below an at-risk milestone.
The operator reads one prioritized list, not a core list plus per-capability appendices.

**Scheduling is not here.** Capability *scheduling* lives in the reporting matrix, seeded from the
capability's bundled pack at enable and compiled by `project-automator` into
`automation/tasks.yaml` — the `tick` routine below dispatches it like any other entry, and the
generic `deadline` cadence already handles per-capability escalation tiers via
`state/<capability>.json:escalation_tiers_fired`. `routine.yaml` answers the *conversational*
question ("what does this capability want looked at right now"), which the tick does not.

## Routines

The orchestrator understands named routines:

### `tick` — the registry-driven scheduler

The single routine that makes reporting *automatic*. It is deterministic: read the
cadence registry, compute what is due today, dispatch the generators. Each generator
self-queues its draft into `outbox/queue/` (see each skill's "Outbox emission"),
so a tick's whole job is **decide what's due and call the right generator** — it
authors nothing and sends nothing.

**Algorithm:**

1. Read `project-state/automation/tasks.yaml` (`tasks[]`) — the **canonical cadence
   registry** (`project-automator` compiles it from the matrix; compatible editors
   may write operator reschedules into it, so it carries the live schedule).
   Resolve each task's target: `kind: matrix` → the matching `reporting-matrix.yaml`
   entry (generator, profile, surface; the matrix `enabled` flag is authoritative for
   matrix tasks); `kind: action` → the named skill action; `kind: adhoc` → the task's
   own stored prompt. Skip disabled tasks and `status: proposed` tasks (unaccepted
   ghost holds never fire). **Fallback:** only if `automation/tasks.yaml` does not
   exist, read `reporting-matrix.yaml` entries directly (skipping `enabled: false`)
   as in v2.0.
2. For each remaining task, evaluate its `cadence` against today's date and the relevant
   `state.json:pointers` (e.g. `last_weekly_report`):
   - `weekly` (`day: <dow>`) → due if today is that weekday **and** no run is
     recorded since the start of this week.
   - `monthly` → due on the configured day / last working day, once per month.
   - `quarterly` / deadline-bound (`Apr/Jul/Oct/Jan`) → due when today falls inside
     the entry's `lead_time` window before the deadline (default 14 days).
   - `sprint-aligned` → due on the sprint boundary from the active sprint calendar.
   - `deadline` → due when today ≥ (`due` − `lead_days`), once per period (the task's `fy`).
     **Independently of dueness**, compare today against each `escalation` tier relative to
     the `hard` date; on first crossing (check `state/<capability>.json:escalation_tiers_fired`),
     emit `<capability>.deadline.warning|alert|critical` and place the item in 🔴
     (critical/alert) or 🟡 (warning). A task past its `hard` date with non-terminal status
     is a permanent 🔴 ("claim window forfeited unless filed") until a human records the
     terminal status. **Chaining:** a task with `after:` dispatches only once the referenced
     entry has a completed run for the same period; `review_gate:` additionally requires a
     completion event from the named skill with a verdict in `pass_on`. Chains evaluate
     within a single tick pass; unsatisfied chains show in the digest as "waiting on <entry>".
   - `event-driven` / `on-publish` → **never** time-due; these fire from activity-log
     triggers (`phase-transition`, `milestone-completion`, `documents/published/`),
     not from the tick. Skip them here.
3. Build the **due-list**: `[ {entry-id, generator, profile?, reason, source-event,
   period} ]`. Include only due enabled matrix entries, active-pack required
   triggers, or actions explicitly accepted by the operator. Map each report to
   the single owner in `CODEX.md`.
4. Deduplicate on `{source-event, period, report-owner}` using existing run
   pointers/activity. Invoke each remaining owner once (passing `profile` if
   present). The generator produces its report **and** drops an outbox card.
5. Surface the result to the user as the standard digest (🔴/🟡/🟢) noting which
   cards were just queued: "Queued 2 drafts for review in outbox/queue/."
6. Append one `orchestrator.tick` event per dispatch to the activity log so the
   configured scheduling views can show last-run.

**Discipline for the tick:** it dispatches generators, never sends. If nothing is
due, say so — a tick with an empty due-list is a healthy quiet day. Idempotent:
re-running a tick on the same day must not double-queue (the per-period pointer /
"already run this week" check prevents duplicates).

**Dry run:** `tick --dry-run` prints the due-list without invoking generators —
use it to preview what a scheduled run would do.

### `daily` (optional — only if the team wants a daily check)
1. If at least one harvest surface is configured and available, offer or run
   `project-harvester` under the invocation gates. Otherwise skip it silently.
2. If `documents/inbox/` contains files, offer or run
   `project-document-curator`; otherwise skip it.
3. Tail activity log since yesterday
4. Check `at_risk` and `blocked` milestones
5. Flag any unclassified docs remaining in inbox
6. Report any Gmail drafts from yesterday not yet sent (if integrated)
7. **Suggest `project-git checkpoint`** if `git status --short` shows uncommitted changes — mention it at the end of the daily summary: "You have uncommitted changes. Run `project-git checkpoint` to record today's work."

### `end-of-session`
When the user signals end of day, end of session, or "wrapping up":
1. Tail activity log for events since last commit.
2. If uncommitted changes exist, propose a checkpoint: surface the auto-generated commit message and ask "Ready to checkpoint?" Do not commit automatically.
3. If the next SC meeting or claim deadline is within 7 days, flag it as a reminder.
4. Remind the user to push if working with a team: "After checkpointing, run `project-git push` to share with teammates."

### `weekly` (Monday)
1. Call `project-status-reporter` to draft the weekly report
2. Hand off to `project-notifier` to post to Slack after the user reviews
3. Check SC prep window (meeting in <14 days?) → start SC pack prep
4. Check claim window (claim in <14 days?) → start claim prep
5. Recompute `state.json:health`
6. Update `state.json:pointers.last_weekly_report`

### `monthly` (last working day of month)
- Monthly technical brief to consortium (`project-status-reporter` monthly mode)
- Review + refresh risk register
- Nudge IP disclosure review

### `quarter-close` (around the 15th of Apr/Jul/Oct/Jan)
- Call `project-funder-reporting` to assemble the quarterly claim
- Draft the PIC PM cover email via `project-notifier` (Gmail draft)
- Nudge Finance Rep for member claim packages
- Schedule the SC meeting if one is due

### `sc-prep` (10 business days before a SC meeting)
- Call `project-review-meeting` to build agenda + pack
- Invite check via `project-notifier`
- Circulate agenda 5+ business days prior

### `baseline` (on phase transition, milestone completion, or on demand)
- Under the invocation gates, call `project-doc-suite` once to produce the
  unified documentation bundle
- Output: `project-state/reports/unified-suite/YYYY-MM-DD/`
- Copy to website `public/downloads/unified-suite/YYYY-MM-DD/` for static serving
- Log `report.generated` event to activity log

### `phase-check` (weekly during planning and closeout, monthly during execution)
- Call `project-phase-gate` for gate status
- If ready-to-transition, surface the prompt; then trigger the `baseline` routine

## Scheduling

The orchestrator does not run itself. It is invoked:
- On user demand ("what should I do?")
- By a Codex recurring automation, when the operator explicitly requests scheduling
- By an operating-system scheduler firing **`project-orchestrator tick`** on the registry's natural cadence
  (for example, early each weekday). The scheduler is a thin trigger; all scheduling *logic* lives
  in the `tick` routine reading `automation/tasks.yaml` (falling back to
  `reporting-matrix.yaml` when no registry exists), so the schedule is testable
  and inspectable in the substrate rather than buried in scheduler config. An optional
  compatible calendar may render the same registry with computed next-due and last-run.

`project-state/manifest.yaml` does not specify schedules; those are managed via the `schedule` skill and should be configured separately.

**Registering a recurring trigger.** The public package does not include a scheduler
or calendar application. In Codex, use the product's recurring-automation support when the
operator requests scheduling; on Windows, Task Scheduler is an optional CLI fallback.
Never register a trigger silently or bypass normal approval and sandbox settings.
Keep scheduler logs under `logs/cron-tick.log` when a CLI fallback is used.

## Discipline

- **Read first.** Return recommendations without invoking generators unless one
  of the three invocation gates is satisfied.
- **One owner once.** Do not ask multiple report generators to represent the same
  source event and reporting period.
- **Don't surprise the user.** Even when a next step is obvious, offer it — don't execute. Especially for anything going to PIC.
- **Honor the quiet days.** If there's genuinely nothing to do, say so. A healthy project has quiet days.
- **Respect phase.** In planning, focus on gate items. In execution, focus on rhythm. In closeout, focus on final reports. The orchestrator's priorities shift by phase.

## Integration

Routes to the single applicable owner, including `project-doc-suite` for a full
documentation bundle. It does not mutate canonical state directly; it goes
through `project-state`. Its own derived run snapshot may be written to
`reports/adhoc/orchestrator-YYYY-MM-DD.md`, then logged through `project-state`.

- **project-git** — suggested at end of daily routine and end-of-session; the orchestrator surfaces the checkpoint prompt but never calls `git commit` automatically.
