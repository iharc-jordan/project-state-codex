---
name: project-milestone-manager
description: "CRUD project milestones, update percent complete and technical progress narrative, flag at-risk or blocked milestones, and regenerate the tracking xlsx from the YAML source of truth. Use this skill whenever the user says 'update M03', 'milestone status', 'how's M05 going', 'mark M01 complete', 'what milestones are at risk', 'recompute overall percent complete', 'list milestones', 'add a new deliverable to M07', 'assign owner to M12', 'regenerate the milestones tracker', or any request to read or write milestone state. Also trigger when project-status-reporter needs milestone data for a weekly report or SC pack, when project-funder-reporting needs % complete + technical_progress for the quarterly claim, when project-phase-gate checks whether gate milestones are done, or when project-change-register needs to know which milestones a change affects. PIC requires technical_progress + percent_complete per milestone on every claim — this skill owns that surface."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Milestone Manager

## Purpose

Milestones are the spine of a PIC-funded project. The Master Project Agreement's Schedule A lists them; quarterly claims report progress against them; Steering Committee meetings review them; final reports close them out. This skill is the single interface for everything milestone-related.

Per PIC PM Guide, the two fields that *must* be reported on every milestone every quarter are:
- `percent_complete` — integer 0–100
- `technical_progress` — narrative string describing what was accomplished

Every other field (planned/actual dates, deliverables, owner, budget category, status, at-risk reason) supports those two.

## Trigger phrases (priority order)

1. "update M03" / "update milestone M03"
2. "mark M01 complete" / "M05 is done"
3. "what milestones are at risk?"
4. "list milestones" / "show me the milestone status"
5. "how's M05 going?"
6. "assign owner to M12" / "M07's owner is Jane"
7. "add a deliverable to M04"
8. "recompute overall percent complete" / "project health"
9. "regenerate the milestones tracker" / "rebuild tracking/milestones.xlsx"
10. Any `project-*` skill fetching milestone data

## Operations

### `list_milestones(filter?, limit=50, cursor?, detail=false)`

Return bounded summary rows sorted by id, with a stable next cursor when more
results exist. Do not load full YAML bodies unless detail mode or a named
milestone requires them. Optional filters:
- `status: planned | in_progress | at_risk | complete | blocked` — `blocked` renders in the **At Risk** column in the kanban
- `owner_short: "OrgA" | "OrgB"`
- `proposal_phase: "Phase 1 – ..."` (loose match)
- `at_risk: true` (shortcut for status in {at_risk, blocked})

Output fields: `id, title, owner_short, planned_start, planned_end, percent_complete, status, at_risk_reason`.

### `get_milestone(id)`

Read one milestone file and return the full parsed YAML.

### `create_milestone(...)`

Create only for a source-supported shared deliverable, an approved scope change,
or an explicit operator request. Scaffolding does not imply a fixed milestone
count. When a governed schedule is amended, require:
- `id` (Mxx format, next available)
- `title`
- `owner_org`, `owner_short`
- `description`
- `planned_start`, `planned_end`
- `completion_criteria`
- `mpa_reference` — reference to Schedule A position

Filename: `M<NN>-<kebab-slug>.yaml` where `<NN>` matches the MPA Schedule A number.

### `update_milestone(id, fields)`

The most-used operation. Common field updates:

| User says                              | Fields updated                                          |
| -------------------------------------- | ------------------------------------------------------- |
| "M03 is 40% done, pilot batches 5-10 complete" | `percent_complete: 40`, `technical_progress: "Pilot batches 5-10 complete. Batches 1-4 pending rework on sensor calibration."` (always append date context if missing) |
| "M05 is at risk — waiting on M04 data" | `status: at_risk`, `at_risk_reason: "Blocked on M04 labeled dataset completeness."` |
| "M01 is done"                          | `status: complete`, `percent_complete: 100`, `actual_end: <today>` |
| "M07 started today"                    | `status: in_progress`, `actual_start: <today>`          |
| "Jane from OrgB now owns M11"          | `owner_person: <slug-of-person-record>` (create people entry if missing via project-state) |

All writes go through `project-state` for locking + logging. Event names:
- `milestone.created`
- `milestone.updated` (default)
- `milestone.completed` (when `status: complete` set)

### `check_at_risk()`

Surface milestones that need attention. Rules:
- `status in {at_risk, blocked}` → always
- `status == in_progress AND planned_end - today < 14 days AND percent_complete < 70` → "behind schedule"
- `status == planned AND planned_start < today` → "late start"
- Any milestone with stale `technical_progress` (not updated in 30 days) while `status == in_progress` → "stale progress"

Return a prioritized list with reasons and suggested actions.

### `compute_overall_progress()`

Return:
- Weighted overall % complete (weight each milestone equally unless budget weights are available from Schedule A)
- Count by status
- Count by owner org
- Count by proposal phase
- delivery posture from the adapter's material health semantics. A blocked
  required milestone can be red; a material schedule risk can be yellow;
  development-only advisories do not affect this rollup.

Store the result under `state.json:health` via `project-state` only when the
normalized material-condition fingerprint changes. Exact repeats return the
existing `health.assessed` event without touching state or activity.

#### `overall_percent` is all-time, and now says so

`overall_percent` is a mean over **every milestone ever declared**, which is the right number for a
project with one ending and a misleading one for a facility that keeps going. Six complete milestones
read 100; adding a seventh for the next increment reads 85. But 85 of *what*? The number has quietly
stopped meaning "how much of this project is done" and started meaning "how much of everything ever
conceived is done". After several increments a facility that ships perfectly every time converges on
100 and never once reports that the increment in front of it is finished.

Two changes, both additive:

- **Always write `health.scope: "all-time"`.** `overall_percent` keeps its exact computation and its
  exact meaning — the existing consumers of the rollup read the same field and get the same value.
  What changes is that the field now states what it measures. This is disclosure, not a fix, and spec
  §5.3 says so plainly.
- **When `state.json:lifecycle` is `continuous`, also write `health.increment`,** scoped to
  `current_increment`: `{id, percent, milestones_total, by_status}`. Membership is
  `milestone.increment == current_increment`, else the increment manifest's `milestones` list. This is
  the number that answers *are we done with what we are doing now.*

Never write `health.increment` on a terminal facility — its absence is how a reader knows there is only
one pass.

Also report `milestones_total` as a count of **unique** ids. Duplicate IDs would
otherwise make file counts and the health projection disagree. `project-state`'s
validator reports the collision; this operation must not paper over it.

#### Which number to show

Readers prefer `health.increment.percent` where present and fall back to `overall_percent`. When
reporting to a human on a continuous facility, lead with the increment number and name the increment:
*"v1.1 is 40% complete (all-time across 45 milestones: 6%)."* A bare percentage on a continuous
facility is ambiguous, and that ambiguity is the defect.

Deprecating `overall_percent` in favour of a scoped-by-default rollup is a v5 conversation — spec §9,
open question 1 — not something this operation decides.

#### `increment` on a milestone

Optional. Absent on every existing milestone and never backfilled. A milestone with no `increment` on a
continuous facility counts toward `overall_percent` and not toward `health.increment` unless the
increment manifest lists it — the conservative reading: unassigned work is real work, but it is not
evidence that *this* increment is done.

### `regenerate_tracker()`

Build/refresh `tracking/milestones.xlsx` from the YAML source:
- One row per milestone
- Columns: id, title, owner_org, proposal_phase, planned_start, planned_end, actual_start, actual_end, percent_complete, status, at_risk_reason, technical_progress, completion_criteria
- Add a conditional-format traffic-light column based on `check_at_risk()` output
- Second sheet: summary (count by status, owner, phase; overall %)

Use the `xlsx` skill for the heavy lifting; do not write xlsx from scratch. The xlsx is a *view* — the YAML remains source of truth.

Event logged: `tracking.regenerated` with `target: "milestones.xlsx"`.

## Discipline rules

- **Apply the materiality gate.** Routine task progress, ordinary commits, and
  test reruns do not create/update milestones or events. A shared commitment,
  durable delivery risk, governed scope, or explicit reasoned operator override
  may do so.
- **Never silently accept a 0%→100% jump without a completion event.** If `percent_complete` is set to 100, `status` must become `complete` and `actual_end` must be set.
- **Never let `percent_complete` go backward.** If an update would decrease it, require an explicit user confirmation and append a note to `technical_progress` explaining the regression.
- **Always update `technical_progress` when `percent_complete` changes.** If the user provides a number but no narrative, ask them for one line of context. PIC requires the narrative.
- **Require `at_risk_reason` when `status` becomes `at_risk` or `blocked`.**
- **Don't edit `completion_criteria` casually.** That text is from the MPA Schedule A. Edits to it require a Change Order.
- **Respect ownership.** If asked to update a milestone owned by a different organisation, warn and suggest confirming with the owner before making changes.

## Integration with other skills

- **project-state** — all writes route through it.
- **project-status-reporter** — pulls milestone state for weekly reports, SC packs, and quarterly claims.
- **project-funder-reporting** — pulls `percent_complete` + `technical_progress` per milestone at quarter-close for the PIC MS & financial tracking form.
- **project-phase-gate** — may reference milestone completion as a gate-out criterion (e.g., M13 complete → closeout gate opens).
- **project-change-register** — when a milestone is added/subtracted or its timeline shifts ≥3 months, that's a material change requiring a Change Order.

## Worked example

**User:** "Mark M01 as 60% complete — we got the first year of historical data loaded and the baseline cycle time and yield validated. Still waiting on the two energy-consumption datasets."

**Skill:**
1. Read `milestones/M01-cdi-data-readiness.yaml`.
2. Update:
   - `percent_complete: 60`
   - `technical_progress: "Year 1 historical data loaded and integrated. Baseline cycle time and yield KPIs validated and approved. Remaining: Year 2/Year 3 energy consumption datasets expected by 2026-04-25."`
   - `last_modified: <now>`, `last_modified_by: <user>`
3. Call project-state to acquire lock, write, release, log `milestone.updated` with summary.
4. Run `check_at_risk()` — M01 is 60% with 7 days to planned_end; returns "behind schedule" (60% with only 14 days to reach 100% is tight but achievable).
5. Offer to also update the tracking xlsx.
6. Return updated entity + at-risk status.

## Reference files

- `references/milestones-ownership.md` — who owns what (seeded from proposal)
- `references/claim-mapping.md` — how milestone % and technical_progress map to the PIC MS & financial tracking form fields
