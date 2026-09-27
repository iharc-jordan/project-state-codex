---
name: project-scheduler
description: "Change when things happen — 'move the weekly report to Fridays', 'add a monthly review', 'what's scheduled this week'. Conversational edits to automation/tasks.yaml, proposed before applied."
map:
  tier: P2
  stage: control
  reads: [reporting-matrix, automation-tasks, state, milestones]
  writes: [automation-tasks]
---

# project-scheduler

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Talk the project's cadence into place. Conversational read and write over automation/tasks.yaml — the canonical cadence registry — using the same op vocabulary and proposed-ghost-card discipline as the kanban calendar's chat surface, but without needing the app running. Use when the user says 'schedule the weekly status report', 'move the SR&ED digest to Tuesday', 'pause the Monday tracker email', 'what's scheduled', 'what fires this week', 'set up the cadence for this project', 'add milestone check-ins for M03', 'stop that recurring report', 'run the weekly report now', or any request to read or change WHEN something runs. Creates land as status:proposed ghost tasks awaiting acceptance — never live on first write. Does NOT compile from the matrix (that is project-automator), does NOT dispatch generators (that is project-orchestrator tick), and never edits reporting-matrix.yaml. All writes route through project-state. Trigger: /project-scheduler

## Purpose

The reporting matrix says *what* runs. `automation/tasks.yaml` says *when*. This skill is
how a person changes the *when* by talking, instead of editing YAML or dragging cards in
the kanban calendar.

It is the third door onto one registry:

| Door | Who uses it | Where |
|---|---|---|
| `project-automator` | compiles matrix → registry | batch |
| kanban calendar + its chat | operator, visually | the app, port 3355 |
| **`project-scheduler`** | operator, conversationally | **anywhere — Claude Desktop, CLI** |

All three write the same file under the same rules. This skill exists because the other
two need the app running, and the scheduling hosts that actually fire (see
`docs/AUTOMATION-HOSTS.md`) mostly do not have it.

> **This skill decides and persists. It does not fire.** Dispatching due work is
> `project-orchestrator tick`. Compiling the matrix is `project-automator`. Keep the
> jobs separate — one skill, one coherent job.

---

## Invocation

```
/project-scheduler                          → read: what's scheduled, what fires next 7 days
/project-scheduler status                   → registry health: orphans, proposed, disabled, stale once-tasks
/project-scheduler <anything in words>      → interpret, emit ops, persist
```

There is no op syntax for the user to learn. They speak; this skill resolves.

---

## Step 0 — Locate and load state

1. Walk up from cwd to find `project-state/manifest.yaml`. **Fail fast if not found** —
   a scheduling change written into the wrong project is worse than no change.
2. Read `project-state/automation/tasks.yaml` → `tasks[]`. If absent, say so and route to
   `/project-automator generate` rather than creating one from nothing.
3. Read `project-state/reporting-matrix.yaml` → `entries[]` (targets and the authoritative
   `enabled` flag for matrix tasks).
4. Read `project-state/state.json` → phase, pointers, `sprint_calendar`.
5. Read `milestones/` for ids and due dates (milestone-scoped check-ins need both).
6. Timezone from `manifest.yaml:automation.timezone`. **REFUSE if absent** — report the
   missing key and stop. Never default to UTC or read the host clock.

---

## The op vocabulary

Every change is one of eight ops. This is the same vocabulary the kanban chat emits, so a
cadence talked into place here reads identically to one dragged into place there.

| Op | Shape | Applies |
|---|---|---|
| `create` | `{target: {kind: matrix\|action\|adhoc, ref}, cadence, title?, prompt?, scope?}` | **as proposal** |
| `reschedule` | `{id, cadence}` | immediately |
| `enable` / `disable` | `{id}` | immediately |
| `accept` | `{id}` | immediately |
| `remove` | `{id}` | immediately, proposed/adhoc only |
| `run` | `{id}` | immediately (one firing) |
| `apply-preset` | `{preset, day?, hour?, milestone?, due?}` | **as proposals** |

### Cadence shape

```yaml
kind: daily | weekly | bi-weekly | monthly | quarterly | annual | sprint-aligned | once | deadline
day:    <weekday>        # weekly, bi-weekly
hour:   0-23             # all time-fired kinds
minute: 0 | 30
dom:    1-28             # monthly, quarterly, annual
month:  1-12             # annual
start:  YYYY-MM-DD       # once
due / lead_days / hard / escalation   # deadline
```

`sprint-aligned` fires on each sprint's last day and stays **dormant** until
`state.json:sprint_calendar` is set — say so plainly when it is null rather than writing a
task that silently never fires.

### Presets

`daily-ops` · `weekly-core` · `funder` · `agile-default` · `milestone-checkins`

Presets are additive and idempotent. `milestone-checkins` takes `milestone` and `due`.

---

## The rules that keep this safe

1. **Creates are proposals.** Every `create` and `apply-preset` is written with
   `status: proposed` and `enabled: false`. The tick skips both, so a proposal cannot fire.
   Acceptance is a separate, deliberate act — `accept`, or the calendar's Accept button.
   Say "proposed, not live" in the reply every time.
2. **Never invent an id.** Targets must resolve to something already on file: a
   `tasks[].id`, a `reporting-matrix.yaml` entry id, a known skill action, a preset id, or
   a milestone id. If the user asks for a report nothing covers, create an **adhoc** task
   with an explicit `title` and `prompt`, and say it is ad-hoc, not a matrix entry.
3. **Never write `reporting-matrix.yaml`.** This skill owns *when*, not *what*. For matrix
   tasks the matrix's own `enabled` flag is authoritative — disabling a matrix entry is a
   matrix edit, and belongs to `project-state` or the matrix editor.
4. **Never dispatch, never send.** `run` queues one firing through the normal job path; the
   generator still drafts into `outbox/queue/`. Nothing reaches a human recipient from here.
5. **Milestone scoping.** Check-ins for a milestone carry
   `scope: {milestone: <id>, until: due}` so they retire when it completes. Prefer the
   `milestone-checkins` preset, passing `due` from the milestone file.
6. **Preserve operator intent.** Existing cadences are the operator's. Re-running this
   skill must never silently reset a task someone rescheduled — that is exactly the
   guarantee `project-automator update` makes, and this skill honours it too.
7. **Route writes through `project-state`.** Take the advisory lockfile on
   `automation/tasks.yaml` (300 s TTL), write, release, and append one
   `scheduler.<op>` event per applied op to `logs/activity.ndjson` (append-only).

---

## How a turn works

1. **Read the registry** and build the current picture: time-fired tasks, event-driven
   tasks, proposals awaiting acceptance, disabled tasks, and what fires in the next 7 days.
2. **Resolve the request against what exists.** "The Monday email" → `auto-monday-tracker-email`.
   Ambiguous? Ask once, with the candidates named. Never guess between two tasks.
3. **Emit the ops** — plainly, in the reply, so the user sees exactly what will change.
4. **Persist** through `project-state`, under the lock.
5. **Report** what applied, what is proposed and still needs acceptance, and when each
   thing next fires. Name the weekday and date, not just the cadence kind — "Monday
   2026-09-28" beats "weekly".

---

## Reading the schedule

A read should answer three questions without being asked:

- **What fires next, and when** — next 7 days, by date.
- **What is waiting on you** — proposals unaccepted, and anything disabled that the matrix
  still expects.
- **What is declared but dead** — `sprint-aligned` tasks with no sprint calendar, `once`
  tasks whose `start` has passed, matrix entries with no compiled task, tasks whose target
  no longer resolves. A cadence that cannot fire should never look healthy.

---

## What this skill does NOT do

- Does not compile the matrix into the registry — `project-automator`
- Does not decide what is due today or dispatch generators — `project-orchestrator tick`
- Does not create or edit reporting-matrix entries
- Does not register cron, launchd, or Claude Desktop scheduled tasks — those are *hosts*,
  documented in `docs/AUTOMATION-HOSTS.md`; this skill only fills the registry they read
- Does not send, post, or publish anything
