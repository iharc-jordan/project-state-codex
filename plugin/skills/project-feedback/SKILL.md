---
name: project-feedback
description: "Report a bug or request against project-state itself — 'file feedback', 'this skill got it wrong', 'feature request for project-state'. Records FB-NNN entries."
map:
  tier: P3
  stage: keep
  reads: [feedback]
  writes: [feedback]
---

# Project Feedback

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Register defects and requests against the project-state product itself. Captures reports from any source — inline user report, seed-issue curation flags on harvested signals, or an opt-in skill-error log — as feedback/FB-NNN-<slug>.yaml substrate records, triages them (dedup, in-repo verification with file:line notes, type/component/severity), and projects them to GitHub issues idempotently: first filing writes github_issue back onto the record; re-runs update, never duplicate. Sync pulls issue status back (resolved/verified) via the harvester's GitHub sweep. Use whenever the user says 'file a bug', 'log this bug', 'report an issue', 'register this feedback', 'found a plugin bug', 'the skill misbehaved', 'capture feedback from signals', 'sync feedback', 'list open feedback', or when curation flags a doc with seed-issue. Spec: docs/FEEDBACK-AND-ISSUES-SPEC.md; adopted by decision 2026-08-11-adopt-feedback-issues-spec. Trigger: /project-feedback

## Purpose

Any bug-shaped report about the project-state product, from any source, becomes exactly one
substrate record and exactly one GitHub issue, with working links both ways. The substrate record
(`feedback/FB-NNN-<slug>.yaml`) is the source of truth; the GitHub issue is its projection —
the same relationship `project-jira-publisher` has to Jira, using the same backlink idempotency.

Design of record: `docs/FEEDBACK-AND-ISSUES-SPEC.md` (adopted 2026-08-11). This SKILL.md
implements spec pieces 1–4 (Tier 1). Pieces 5–7 (outbox `github_issue` queue action,
orchestrator tick, pilot deposit endpoint) are spec'd but not built; until piece 5 lands,
filing is **direct** (`feedback.file_mode: direct` in the manifest) with explicit confirmation.

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
  repo: "Atomic-47-Labs/project-state"   # defaults to surfaces.github.repos[0]
  default_labels: ["bug"]
  label_map: { bug: [bug], enhancement: [enhancement], question: [question], docs: [documentation] }
  file_mode: direct          # direct until spec piece 5 (queue action) lands; then queue
  auto_capture:
    curator_flag: true       # honor action_flags: [seed-issue]
    skill_errors: false      # opt-in; drains logs/feedback-candidates.ndjson
```

GitHub access: `gh` CLI locally/desktop; `ps_github` MCP connector on the appliance. Tokens
never touch the substrate.

## Operations

### `capture` — report → FB record

From an inline report: draft the record with the reporter's words verbatim in `description`,
allocate FB-NNN, `status: captured`, log `feedback.captured`. Never touches GitHub.

From signals (`capture --from-signals`): walk `documents/index.yaml` classified entries whose
`action_flags` include `seed-issue` and that have no FB record linking them
(`source_document` match). Draft one FB record per distinct claim (a single doc may yield
several — Jen's kickoff doc yielded three). Provenance: `source_document`, `reported_via: doc`
or `harvest`.

### `triage` — captured → triaged | rejected

1. **Dedup** against open FB records and open GitHub issues (title similarity + component).
   Duplicate → set `duplicate_of`, close as dup, never file.
2. **Verify in repo**: grep/read the claimed files; set `verified_in_repo` +
   `verification_note` with file:line citations. Unverifiable reports still proceed, marked
   unverified — pilot reporters can't read the code and their reports are still evidence.
3. Classify `type`, `component`, `severity`; map labels from `feedback.label_map`.

### `file` — triaged → filed

Render the issue body (template below). In `file_mode: direct`: show the drafted issue to the
user, get explicit confirmation, run `gh issue create`, write `github_issue` + `github_url`
back, `status: filed`, log `feedback.filed`. A record that already has `github_issue` is
**updated** (`gh issue edit` / comment), never re-created. `severity: data-risk` records may
file without the confirmation pause — with a loud log line — per spec §9 proposal.

When piece 5 lands, default switches to queueing an outbox card (`kind: github_issue`) and the
queue's approve action performs the create.

### `sync` — filed → resolved

For each FB with `status: filed`: check the issue state (`gh issue view`, or consume the
harvester's GitHub signals). Closed → `status: resolved`, record `resolution`, log
`feedback.resolved`, and if the reporter came via a doc or pilot, offer a notification draft.
`verified` is set by a human confirming the fix.

### `list`

Open FB by status/component/severity. Feeds the weekly report one-liner and the P-SPP
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
