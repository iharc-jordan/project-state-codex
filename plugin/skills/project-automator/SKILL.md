---
name: project-automator
description: "Compile the project's reporting-matrix.yaml into automation/tasks.yaml — the canonical cadence registry that every scheduling host (the kanban in-app scheduler, the cron-curled /api/cron/tick, the appliance headless runner) fires from and the calendar UI edits. Reads every matrix entry, classifies it as cadence (time-fired) or event-driven (hook), normalizes to the task cadence shape (kind/day/hour/dom/month/start), spreads fire hours across the configured window, and writes tasks additively — never clobbering operator reschedules made in the calendar. Also applies named cadence presets (typical daily/weekly/funder/agile bundles) per project or per milestone. Modes: plan (preview), generate (write), update (re-diff, preserve overrides), status (registry health), preset list|apply. Does NOT register crons or call generators — the host fires, the orchestrator tick dispatches. Trigger: /project-automator"
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# project-automator

## Purpose

The reporting matrix is the source of truth for *what* runs. This skill is the compiler
that turns the matrix into the **canonical cadence registry** — `project-state/automation/tasks.yaml` —
the single file every scheduling host fires from and the kanban calendar edits.

Two tracks:

| Track | Source | Compiled to |
|---|---|---|
| **Cadence** | Matrix entries with `kind: daily \| weekly \| bi-weekly \| monthly \| quarterly \| annual \| sprint-aligned` | Time-fired tasks with a normalized cadence, fire hours spread across the configured window |
| **Achievement** | Matrix entries with `kind: ad-hoc \| post-event \| on-publish \| event-driven` | Event tasks (no fire time) that the scheduler's activity-log event hooks fire |

Output: `project-state/automation/tasks.yaml`. The matrix stays the source of *what*;
the registry owns *when* — including any reschedules the operator makes by dragging
cards on the calendar, which this skill **must never overwrite** (see `update`).

> **Retired:** `automation/schedule.yaml` (v2.0 output). No host ever consumed it.
> If `status` finds one, report it as legacy and offer to delete it.

---

## Invocation

```
/project-automator                    → plan mode (preview, no writes)
/project-automator generate           → write automation/tasks.yaml
/project-automator update             → add new matrix entries; preserve existing tasks
/project-automator status             → registry health, orphans, last tick, legacy files
/project-automator preset list        → list available cadence presets
/project-automator preset apply <id>  → apply a preset (additive, idempotent)
/project-automator preset apply milestone-checkins --milestone M03
/project-automator --window 23:00-05:00   → override time window
```

---

## Step 0 — Locate and load state

1. Walk up from cwd to find `project-state/manifest.yaml`. Fail fast if not found.
2. Read `project-state/reporting-matrix.yaml` → `entries[]`.
3. Read `project-state/automation/tasks.yaml` if present → existing `tasks[]`.
4. Read `project-state/state.json` → phase, milestone pointers, `sprint_calendar`.
5. Window: args, then `manifest.yaml:automation.window`, then default `23:00–05:00`.
6. Timezone: `manifest.yaml:automation.timezone`. **REFUSE if absent** — report the missing key and
   stop. Do not default to UTC, do not read the host machine's timezone, and do not compile a partial
   schedule.

   The window at step 5 is expressed in LOCAL time, so a guessed timezone does not produce a slightly
   wrong schedule, it produces a confidently wrong one: `23:00–05:00` interpreted as UTC fires the
   nightly jobs at 4pm in Vancouver. And the host machine is the wrong source — the facility's
   timezone is a property of the project, not of whoever runs the command, so inferring it makes the
   schedule depend on who last touched it.

   This is the same rule capability `enable` step 2 applies to `fiscal_year_end`: *"do not invent a
   value, do not substitute a plausible default, and do not write a partial block"*, because a guessed
   value produces a confidently wrong filing date. Same shape, same answer.

   `manifest-v2.yaml` has marked this key REQUIRED since it shipped while shipping it as `~`, and
   nothing collected it (FB-002). `project-onboarding` Q1.8 now asks and `project-scaffolder` writes
   it, so absence should be rare — but rare is not never, and an existing facility predating that
   question will hit this refusal. Report it as a missing answer, not as a broken facility:

   ```
   automation.timezone is not set in manifest.yaml. Scheduling needs it — the 23:00–05:00 window is
   local time, and guessing would fire the nightly jobs at the wrong hour.
   Set it to an IANA name (e.g. America/Vancouver) and re-run.
   ```


## Step 1 — Classify and normalize

One task per matrix entry, `id: auto-<entry.id>`, `target: {kind: matrix, ref: <entry.id>}`.
Matrix tasks carry **no `enabled` flag** — the matrix entry is the enable authority.

### Cadence entries (time-fired)

Normalize the matrix's rich cadence into the registry shape
`{kind, day?, hour?, dom?, month?, start?}`:

| Matrix `cadence.kind` | Normalized |
|---|---|
| `daily` | `{kind: daily, hour}` |
| `weekly` | `{kind: weekly, day, hour}` |
| `bi-weekly` | `{kind: bi-weekly, day, hour, start: <next natural fire date>}` — `start` anchors which week of the fortnight |
| `monthly` | `{kind: monthly, dom, hour}` — `day_of_month: last-business-day` → `dom: 28`; clamp 1–28 |
| `quarterly` | `{kind: quarterly, dom, hour}` — fires day `dom` of Jan/Apr/Jul/Oct |
| `annual` | `{kind: annual, month: <due_month>, dom: 1, hour}` |
| `sprint-aligned` | `{kind: sprint-aligned, hour}` — fires last day of sprint; inert until `state.json:sprint_calendar` (`{length_days, anchor}`) exists. If absent, note it in the output: "sprint-aligned tasks compiled but dormant — set sprint_calendar". |
| `deadline` | One dated task **per anchor instance** (per fiscal year for `recur: annual`): `{kind: deadline, due, hard?, escalation?, lead_days, hour}` + top-level `fy` — id `auto-<entry.id>-<FY>`. Resolve `anchor` (manifest path / state pointer / literal); `due = instance + offset_months`; `hard = instance + hard_offset_months`. New instances added on `update` when a new FY opens; tasks for FYs with terminal claim status (`filed \| waived \| forfeited`) are marked retired, never deleted — **except** FYs registered as an archive tail, which stay live post-archive. The `hard` date is not operator-editable — reschedules apply to fire timing only. Copy `after`/`review_gate` from the entry onto the task verbatim. |

**Window placement:** assign each task an `hour` spread across the window (deadline-bound
first, then weekly, monthly, quarterly, annual) so jobs don't stack on one hour.
`lead_time_days`/`lead_time_hours` subtract from the natural due date (e.g. monthly due
the 1st with `lead_time_days: 2` → `dom: 28`).

### Event-driven entries (hooks)

`ad-hoc`, `post-event`, `on-publish`, and `event-driven` all compile to a task whose
cadence is just `{kind: <matrix kind>}` — no fire time. The scheduler's activity-log
event hooks fire them on `on_event` / `on` / `trigger` matches (`phase.transition`,
`milestone.completed`, `documents/published/`); the calendar renders them in the
event-driven tray. Preserve the trigger verbatim on the task as `trigger: <value>`
so the hook matcher needs no matrix lookup.

## Step 2 — Write discipline (the override-preservation rule)

`tasks.yaml` is **shared-write**: this skill, the calendar UI, and the scheduler's
proposal engine all write it. Non-negotiable rules:

1. Take the advisory lockfile (`automation/tasks.yaml.lock`, 300s TTL) before writing.
2. **Never modify an existing task.** If `auto-<entry.id>` already exists, leave it —
   its cadence may be an operator's drag-reschedule. `generate`/`update` only **add**
   tasks for matrix entries with no task, and list (never auto-delete) orphaned matrix
   tasks whose entry disappeared — deleting requires explicit confirmation.
3. Never touch `status: proposed` tasks, adhoc tasks, or action tasks — they belong to
   the proposal engine, the operator, and presets.
4. Keep `schema_version: 1`, `manifest_kind: automation_tasks`.

## Step 3 — Output by mode

- **`plan`** — print the compiled task list (new / existing-preserved / orphaned), no writes.
- **`generate`** — write additively per Step 2; append `automator.generate` to `logs/activity.ndjson`.
- **`update`** — same as generate plus a diff summary; confirm before deleting orphans.
- **`status`** — task counts by kind/status, dormant sprint tasks, orphans, last
  `orchestrator.tick`, and any legacy `schedule.yaml` (offer deletion).

## Presets — typical cadences as bundles

A preset is a named op-list applied additively (skip refs that already have tasks).
Sources: built-ins below, `templates/cadence-presets/*.yaml`, and the active pack's
`reporting-matrix-defaults.yaml` (each pack is a de-facto preset).

| Preset | Adds |
|---|---|
| `daily-ops` | harvest, inbox-triage, orchestrate-daily (action tasks, weekday hours) |
| `weekly-core` | weekly-status, weekly-retro, comms drafts (weekly, reporting day) |
| `funder` | quarterly-claim chain + SC prep (quarterly + lead-time holds) |
| `agile-default` | sprint-aligned retro + planning set (needs `sprint_calendar`) |
| `milestone-checkins` | per `--milestone <id>`: weekly review + due-minus-7 review, scoped `{milestone, until: due}` so they retire when it completes |

The kanban applies the same presets through `lib/automation.ts:applyPreset` (the
"Set up cadence" picker and chat-to-schedule `apply-preset` op) — one implementation
server-side; this skill is the CLI/headless door to it.

## What this skill does NOT do

- Does not register crons or fire tasks. Hosts fire; the orchestrator `tick` dispatches.
- Does not call generators directly.
- Does not modify the reporting matrix (single exception: nothing — enable toggles go
  through the UI's comment-preserving matrix write, not this skill).
- Does not overwrite operator reschedules (Step 2 rule 2).
- Does not send, post, or draft anything.

## Integration

- **`project-intake` / `project-scaffolder`** call `project-automator generate` as their
  final step, so a new project's calendar is populated and armed out of the gate.
- **Hosts** (kanban scheduler, `/api/cron/tick`, appliance runner) fire from `tasks.yaml`;
  they detect changes by mtime.
- **The kanban Calendar view** (`/calendar`) renders the registry with next-due/last-run,
  edits cadences by drag, and applies presets — all against the same file this skill writes.
