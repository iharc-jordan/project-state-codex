---
name: tender-pipeline
description: "Manage the tender pursuit lifecycle only when tender-intelligence is enabled and a tender entity exists, or when the operator explicitly requests capability setup. Preserve all workflow states, decision entities, tasks, deadline milestones, dismissal reasons, and win handoff. Never create a delivery project or mutate pipeline state without explicit confirmation."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# tender-pipeline

The only skill that changes `workflow.*` on a tender. Everything it does is a validated state transition through the `project-state` memory layer, so the kanban, activity log, and reports stay truthful by construction.

## Lifecycle and transition rules

```text
discovered ─► preliminary_match ─► documents_required ─► under_review ─► qualified ─► bid_no_bid_pending
                                                                                        │
                          ┌─────────────┬─────────────────┬─────────────────────────────┤
                          ▼             ▼                 ▼                             ▼
                        pursue        watch      partner_opportunity               dismissed
                          │             │                 │
                          ▼             └──── (re-enter bid_no_bid_pending on change)
                 preparing_response ─► submitted ─► awarded | unsuccessful

  cancelled  ◄── any non-terminal status (source cancellation via tender-monitor)
  closed     ◄── watch/partner tenders past closing; merged tombstones
```

Validation:

- Forward transitions follow the graph; **backward moves are allowed with a stated reason** (logged in the event summary) — e.g. an addendum can push `qualified` back to `under_review`.
- Entering `bid_no_bid_pending` **requires** `qualification.status: qualified` and auto-opens a decision entity (below) with a due date defaulting to `min(question deadline − 2d, closing − minimum_days_remaining)`.
- Entering `pursue` requires a recorded decision (`workflow.decision_id` resolved with `decision: pursue`).
- Entering `preparing_response` creates the standard pursuit milestones (below) unless they exist.
- `dismissed` requires a reason code; `awarded`/`unsuccessful` require `submitted` first.
- Terminal statuses: `dismissed`, `cancelled`, `closed`, `awarded`, `unsuccessful` — leaving one requires an explicit reopen with reason.

Every transition: memory-layer write + `tender.status.changed` (`previous_value` → `new_value`) + `workflow.next_action` refreshed. Dismissals also log `tender.dismissed`.

## Sub-actions

### `status <tender-id> <new-status>` — validated transition

Also: `assign <tender-id> <person>` (sets `workflow.owner`), `next-action <tender-id> <text>`.

### `decision open <tender-id>` / `decision record <tender-id>`

Bid/no-bid uses the facility's **existing `decision` kind** — no parallel decision system:

- **open** → creates `decisions/<id>.yaml` titled `"Bid/no-bid: <title> (<buyer>)"` with `tender_id` back-reference, the five assessment dimensions as prompts (strategic / capability / commercial / competitive / delivery fit — spec §12), and logs `decision.opened`. Sets `workflow.decision_id`.
- **record** → captures `decision` (`pursue` | `watch` | `partner` | `no_bid`), `decision_owner`, `confidence`, `conditions[]`, `pursuit_budget` (`hours`, `external_cost`); logs `decision.recorded`; transitions the tender accordingly. A `no_bid` routes into the dismissal flow with reason `no_bid_decision`.

The decision therefore appears in the facility's ordinary decision log, review meetings, and status reports.

### `tasks <tender-id>`

Create pursuit tasks with owner, due date, priority, type, dependencies: retrieve documents · review mandatory requirements · confirm insurance · identify references · contact potential partner · submit clarification question · attend mandatory meeting · complete pricing · approve final submission. Deadline-bearing items (question deadline, mandatory meeting, submission) are also offered as **milestones** via `project-milestone-manager` when the tender is in `preparing_response`.

### `dismiss <tender-id> <reason-code> [note]`

Reason codes: `no_capability_fit` · `excluded_term` · `timeline_too_short` · `geography` · `mandatory_disqualifier` · `budget_mismatch` · `incumbent_locked` · `low_value` · `capacity_conflict` · `no_bid_decision` · `duplicate` · `other`. Codes feed the dismissal-reason analysis (status-reporter) and profile tuning (`project-lessons`). Dismissal never deletes — the entity and its history remain.

### `won <tender-id>` — the handoff

1. Confirm `submitted` → `awarded` (with evidence: award notice URL or client confirmation).
2. Invoke **`project-scaffolder`** to spawn the delivery `project-state/` facility, carrying forward: buyer (as client/stakeholder), contacts, the tender document package references, extracted requirements (as the delivery compliance baseline), pursuit decisions, and relevant people.
3. Record `tender.handoff.completed` on both sides (the new facility's activity log notes its origin tender).
4. The tender entity stays in the pursuit facility as the historical record (`workflow.status: awarded`, link to the new project).

### `lost <tender-id>` / `cancelled <tender-id>`

Terminalize with evidence; prompt a `project-lessons` retrospective (what the winning bid had, what our gap was, profile adjustments). Cancellation of a pursued tender triggers the immediate notifier rule.

### `pipeline` — the board in words

Summarize the facility's tenders grouped by lifecycle band (Discovery / Review / Decision / Pursuit / Closed), with score, days remaining, owner, next action. Flag: act-now unowned; decisions past due; deadlines within 10 days; stale `under_review` (> 7 days without activity).

## Optional viewer integration

A separately installed compatible viewer may render lanes from `workflow.status`
using the band grouping above. This skill is the only writer of that field, so every
view remains a truthful projection of state — regenerate a view, never hand-edit it.

## Output format

```
t-2026-0041 → bid_no_bid_pending
  decision d-2026-014 opened (due 2026-07-28) — owner: unassigned
  next action: complete five-dimension assessment
  reminders: question deadline 2026-07-30 · closing 2026-08-21 (31d)
```

## Boundaries

No scoring (qualifier), no change detection (monitor), no harvesting. Never sets `qualification.human_approved` except on an explicit, named human's instruction recorded in the event summary. All writes through the memory layer.
