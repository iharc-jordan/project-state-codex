---
name: project-feedback
description: "Register and triage defects or requests about Project State as substrate feedback records, then project them idempotently to GitHub issues. Use for 'file a bug', 'log this bug', 'report an issue', 'capture feedback', 'sync feedback', or 'list open feedback'. Treat the substrate record as source of truth and require explicit confirmation before creating or updating an external GitHub issue."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Feedback

## Purpose

An explicitly captured, durable bug-shaped report about the Project State
product becomes exactly one substrate record and at most one GitHub issue, with
working links both ways. Routine task-local implementation defects stay in the
active Codex task or configured issue tracker; do not create an FB record merely
because coding work found a bug. The substrate record
(`feedback/FB-NNN-<slug>.yaml`) is the source of truth; the GitHub issue is its projection —
the same relationship `project-jira-publisher` has to Jira, using the same backlink idempotency.

This skill is the complete public Tier 1 contract. The private outbox
`github_issue` action, orchestrator integration, and pilot deposit endpoint are
not bundled and are unsupported here. Filing remains **direct**
(`feedback.file_mode: direct`) with explicit confirmation.

## Trigger phrases

- "file a bug" / "log this bug" / "report an issue" / "found a plugin bug"
- "register this feedback" / "capture feedback"
- "capture feedback from signals" (drain seed-issue flags)
- "sync feedback" / "did they fix FB-002?"
- "list open feedback" / "feedback status"

## The record

```yaml
# feedback/FB-001-scaffolder-onboarding-collision.yaml
id: FB-001-scaffolder-onboarding-collision
kind: feedback
type: bug                    # bug | enhancement | question | docs
title: "..."
component: project-scaffolder  # skill name | kanban | appliance | packs | substrate | docs
severity: workflow-blocking  # cosmetic | annoying | workflow-blocking | data-risk
status: captured             # captured -> triaged -> filed -> resolved -> verified | rejected
description: |               # the report, verbatim where possible
repro: ~
reported_by: "email-or-name"
reported_via: command        # command | doc | slack | harvest | skill-error | pilot
source_document: ~           # signal/doc id when the report came from curation
pilot: ~
verified_in_repo: true
verification_note: "SKILL.md:456 abort rule confirmed"
github_issue: 3              # backlink — idempotency key; null until filed
github_url: "https://github.com/<repo>/issues/3"
labels: [bug]
duplicate_of: ~
resolution: ~
created: "..."
created_by: "..."
last_modified: "..."
last_modified_by: "..."
phase: "..."
```

Ids allocate from `counters.feedback` under the `state.json` advisory lock, via `project-state`.

## Manifest config

```yaml
feedback:
  enabled: true
  repo: "<owner>/<repo>"                 # defaults to surfaces.github.repos[0]
  default_labels: ["bug"]
  label_map: { bug: [bug], enhancement: [enhancement], question: [question], docs: [documentation] }
  file_mode: direct          # direct until spec piece 5 (queue action) lands; then queue
  auto_capture:
    curator_flag: true       # honor action_flags: [seed-issue]
    skill_errors: false      # opt-in; drains logs/feedback-candidates.ndjson
```

GitHub access uses an available authenticated connector or `gh` CLI. Tokens never
touch the substrate.

## Operations

### `capture` — report → FB record

From an inline report: draft the record with the reporter's words verbatim in `description`,
allocate FB-NNN, `status: captured`, log `feedback.captured`. Never touches GitHub.

Apply the materiality gate first. Capture when the operator explicitly asks for
Project State feedback, or when the report represents a durable cross-project
workflow/data/safety contract. Otherwise return the configured issue-tracker
route and leave Project State unchanged. A reasoned operator override is
recorded in the existing description/summary fields.

From signals (`capture --from-signals`): walk `documents/index.yaml` classified entries whose
`action_flags` include `seed-issue` and that have no FB record linking them
(`source_document` match). Draft one FB record per distinct claim (a single doc may yield
several). Provenance: `source_document`, `reported_via: doc`
or `harvest`.

### `triage` — captured → triaged | rejected

1. **Dedup** against open FB records and open GitHub issues (title similarity + component).
   Duplicate → set `duplicate_of`, close as dup, never file.
2. **Verify in repo**: grep/read the claimed files; set `verified_in_repo` +
   `verification_note` with file:line citations. Unverifiable reports still proceed, marked
   unverified — reporters may not be able to read the code and their reports are still evidence.
3. Classify `type`, `component`, `severity`; map labels from `feedback.label_map`.

### `file` — triaged → filed

Render the issue body (template below). In `file_mode: direct`: show the drafted issue to the
user, get explicit confirmation, run `gh issue create`, write `github_issue` + `github_url`
back, `status: filed`, log `feedback.filed`. A record that already has `github_issue` is
**updated** (`gh issue edit` / comment), never re-created. Every external create or
update requires confirmation, including `severity: data-risk`.

An internal version may later replace direct filing with a queued
`kind: github_issue` action; that feature is unavailable in this public adapter.

### `sync` — filed → resolved

For each FB with `status: filed`: check the issue state (`gh issue view`, or consume the
harvester's GitHub signals). Closed → `status: resolved`, record `resolution`, log
`feedback.resolved`, and if the reporter came via a doc or pilot, offer a notification draft.
`verified` is set by a human confirming the fix.

### `list`

Return bounded FB summaries by status/component/severity with `limit=50` and a
stable cursor. Full descriptions/reproduction details require a named record or
explicit detail mode. Feeds the weekly report one-liner and the P-SPP
workstream-G learning register.

## Issue body template

```
**Reported by:** <name>, via <source> (<date>)  [pilot: <id> if applicable]

## Problem
<claim, with file:line citations when verified_in_repo>

## Expected
<what correct behavior looks like>

## Where
<files/skills involved>

---
_Registered from project-state feedback record FB-NNN._
```

## Discipline

- **One report, one record, one issue.** Dedup before filing; the `github_issue` backlink is
  the idempotency key — never strip it.
- **External issue ownership is lean.** Once filed, keep the stable issue number,
  URL, and necessary status/resolution snapshot. Do not copy issue comments or
  later full bodies back into Project State.
- **Reporters' words are evidence.** Keep the verbatim report in `description`; triage adds to
  the record, it doesn't rewrite the report.
- **Verify before filing when the code is readable.** Every claim in a filed issue carries a
  file:line citation or an explicit "unverified" marker.
- **Filing is outward.** Direct mode requires explicit user confirmation per filing session
  (data-risk severity excepted, loudly).
- **This is not a support desk.** Pilot support threads route per the P-SPP D6 decision; only
  product defects/requests become FB records.

## Integration

- **project-state** — id allocation, all writes, activity log.
- **project-inbox / project-document-curator** — produce the `seed-issue` flag this skill drains.
- **project-orchestrator** — (piece 6, future) calls `capture --from-signals` after the curator step.
- **project-harvester** — Step 5e GitHub sweep is the return path for `sync`.
- **project-status-reporter** — weekly "Feedback: N filed, M resolved" line from `list`.
- **project-jira-publisher** — the backlink pattern this copies; do not also publish FB records to Jira.
