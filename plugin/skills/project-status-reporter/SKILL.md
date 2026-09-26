---
name: project-status-reporter
description: "Write a status report — 'weekly report', 'status update', 'draft this week's report', 'Monday tracker email', 'dashboard snapshot'. Built from project-state/, drafted for review, never sent."
map:
  tier: P1
  stage: generate
  requires: [memory]
  binding: mcp-ready
  reads: [milestones, risks, decisions, objectives, changes, log]
  writes: [reports]
  calls: [project-milestone-manager, project-notifier, project-blog-publisher]
  produces: [team-update, stakeholder-update]
---

# Project Status Reporter

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Generate status reports for a grant-funded project in multiple formats — weekly report (team / Slack-format), Steering Committee pack (docx, PIC Appendix A agenda), quarterly claim draft (xlsx, PIC MS & financial tracking form), ad-hoc status prose (for email), and one-page dashboard snapshot. Use whenever the user says 'weekly report', 'draft the weekly', 'SC pack', 'prep the pack for next SC meeting', 'quarterly claim draft', 'draft Q2 claim', 'status update please', 'dashboard snapshot', 'summarize the project', 'how is the project', 'what's our status', 'send a status to PIC', or any request to produce a report from project-state/. Reads through project-state and milestone-manager; hands off delivery to project-notifier and blog-publisher. Never sends anything — always stops at a draft for review.

## Purpose

Turn the structured state under `project-state/` into readable reports in the formats the project's audiences actually consume. The project produces multiple report types on different cadences; they all draw from the same underlying facts.

**Design principle:** the report is a *view* of state. If the report is wrong, the state was wrong or the template was wrong. Reports are never a place where new facts are first recorded.

## Report catalog

**Which home.** If a project-state MCP is connected (the Project State connector, or the local one the
plugin ships; its tools include `project_list`, `get_entity` and `entity_patch`), call `project_list` first. If it
lists this project, with `home: server` or `home: local` alike (the local server writes the folder for you;
`local` is not a cue to edit files), every read and write goes through those tools, the activity-log entry included: after
an `entity_put` / `entity_patch` / `entity_delete`, append the skill's event with `log_append` (the screen
actions, such as `milestone_update`, log their own). Work on the files directly only when no MCP serves the
project.

Reports are entities named by **kind and id**, never by path: the memory layer (`project-state`) places
them. On disk its kinds reference says where each kind lives; over the Project State connector, pass kind
and id to `entity_put` and the server places it. Binary reports (`.docx`, `.xlsx`) need the project's
files (the file binding, or the server runner); over the connector, write the Markdown version and say so.

| Report                       | Format        | Cadence            | Audience                | Kind · id                               |
| ---------------------------- | ------------- | ------------------ | ----------------------- | --------------------------------------- |
| Weekly report                | .md + Slack   | Weekly (Mon)       | Project team            | `weekly-report` · `YYYY-Www`            |
| Monthly technical brief      | .md + Gmail   | Monthly (last Fri) | Consortium members      | `adhoc-report` · `YYYY-MM-brief`        |
| SC pack                      | .docx         | Quarterly          | Steering Committee + PIC| `sc-pack` · `<id>-pack`                 |
| SC agenda                    | .docx         | Quarterly          | SC pre-meeting          | `sc-pack` · `<id>-agenda`               |
| Quarterly claim (MS & financial tracking form) | .xlsx | Apr/Jul/Oct/Jan 20 | PIC Project Manager     | `claim-form` · `YYYY-QN-ms-financial` |
| Ad-hoc status                | .md / email   | On demand          | Varies                  | `adhoc-report` · `YYYY-MM-DD-<slug>`    |
| Dashboard snapshot           | 1-page .md    | On demand          | Exec glance             | `adhoc-report` · `snapshot-YYYY-MM-DD`  |
| Final report (per member)    | .docx         | Project close      | PIC                     | `funder-report` · `final-<org>`         |

## Trigger phrases

- "weekly report" / "draft the weekly" / "Monday report"
- "SC pack" / "prep next SC meeting" / "agenda for the steering committee"
- "quarterly claim" / "draft Q2 claim" / "claim for the 20th"
- "status update" / "how is the project" / "what's our status"
- "snapshot" / "dashboard" / "one-pager"
- "monthly brief" / "technical brief"
- "final report for [org]"

## Common report structure

Every report answers, in this order:

1. **Top line.** One-sentence health + phase.
2. **What's changed since last report.** Milestone progress, completions, decisions recorded, changes logged/orders raised, risks opened/closed, IP disclosures.
3. **What's up next.** Upcoming milestones, deadlines (especially claim + SC), in-flight decisions.
4. **Blockers + risks.** Anything `at_risk`, `blocked`, or overdue. Gate items still pending.
5. **Asks.** Anything the audience needs to decide or approve.

Specifics below customize this skeleton.

## Weekly report

**Inputs:**
- State summary from `project-state` (counters, health)
- Milestones from `project-milestone-manager` (in_progress + at_risk)
- Activity log tail since the last weekly (since the state record's `pointers.last_weekly_report`)
- Gate status of current phase from `project-phase-gate`
- Upcoming deadlines (from the manifest's `reporting_calendar` + milestone planned_ends)

**Output template (a `weekly-report`, id `YYYY-Www`):**

```markdown
# Weekly report — YYYY-Www — [Project Short Name]

**Phase:** <current-phase-label> — <gate-status-summary>
**Overall health:** <green/yellow/red> — <one-line reason>

## Since last week
- <event, event, event — grouped by kind>

## This week's focus
- <upcoming milestones, meetings, deadlines>

## Blockers & at-risk
- <items with status in {at_risk, blocked} + gate items still pending>

## Asks
- <decisions needed, artifacts needed, approvals>

## By the numbers
| Milestones | Planned | In progress | At risk | Complete |
|------------|:-------:|:-----------:|:-------:|:--------:|
| …          |         |             |         |          |

_Next claim due: <date> · Next SC meeting: <date> · Days to project end: <n>_
```

Hand off to `project-notifier` for Slack delivery. Update the state record's `pointers.last_weekly_report` and `counters.weekly_reports`.

## Steering Committee pack

**Inputs:** everything, but specifically shaped for the PIC Appendix A standard agenda (9 topics: Introduction; Review of Previous Minutes; Project Schedule/Overview/Milestones; Change Orders & Change Log; Project Finances; Publications/Media; IP Update; Regulatory Check-In; Key Contact Updates; Open Discussion / Lessons Learned; Action Steps Review; Next Meeting).

**Output:** one `.docx` following PIC's agenda format. Use `python-docx` for rendering (shared primitives with `project-doc-suite-generator`). Embed:
- Gantt-style view of milestones (status, % complete, planned vs. actual)
- Finances table (budget vs. spend — if available)
- Active risks (top 5 by score)
- Recent Change Log entries + any open Change Orders
- Publications in review / approved
- IP disclosures since last SC
- Action items from previous meeting with status

Companion `agenda.docx` is lighter — just the agenda skeleton for the 5-business-day pre-meeting distribution.

## Quarterly claim

Per PIC PM Guide: "Each project member must complete a MS and financial tracking form (provided by PIC). This form is used to assess your organization's claim submissions for the prior quarter."

**Inputs:**
- Period bounds from `claim_period(quarter)` — e.g., Q2 2026 = Apr 1 – Jun 30.
- For each milestone active in the period: `percent_complete` + `technical_progress` at period end.
- Per-member claim packages (expenses, invoices, categorization) — supplied by Finance Rep out of band; this skill assembles around them.

**Output:** a `claim-form`, id `YYYY-QN-ms-financial` — a filled copy of the PIC-provided form. This is the deliverable sent to the PIC Project Manager by the 20th.

Also produce a `quarterly-claim` entity, id `YYYY-QN`, per the schema (through `project-state`).

Hand off to `project-funder-reporting` for the detailed PIC-form assembly; this skill produces the narrative wrapper.

## Ad-hoc status

The user says "status update for X" — produce a paragraph or two tailored to the audience:
- PIC Project Manager → formal, milestone-anchored, cautious on at-risk items
- Consortium Member internal → technical + honest
- Board / exec → outcomes + risks + asks

Save as an `adhoc-report`, id `YYYY-MM-DD-<slug>`. Offer to hand off to `project-notifier` for Gmail draft.

## Dashboard snapshot

One page. Designed for a glance. Sections: phase + gate, health, milestones table, upcoming deadlines, top 3 risks, last 5 activity events. Saved as an `adhoc-report`, id `snapshot-YYYY-MM-DD`.

## Outbox emission (queue the draft for review)

After writing any report, **also drop an outbox card** so the draft
surfaces in the `/queue` UI for human review. This is what makes reporting a UI-first,
review-not-author flow: the report generates on its own, lands in the queue, and the
person reviews/approves/actions it — the system never sends.

A card is a pair with one id in the outbox's queue lane: an `outbox-draft` and an `outbox-card`:

1. **The artifact** — `<id>.md`. Reuse the report markdown you just produced (for
   docx/xlsx reports, write a short markdown cover note that links to the report). `<id>` is `YYYY-MM-DD-<slug>` (e.g. `2026-05-22-weekly-status`).
2. **The card** — `<id>.meta.yaml`, matching the contract in `docs/OUTBOX.md`:

```yaml
id: 2026-05-22-weekly-status
kind: report                       # report | gmail_draft | calendar_hold | doc | blog_post | slack_post
title: "Weekly status report — week of 2026-05-18"
produced_by: project-status-reporter
produced_at: 2026-05-22T06:00:00Z
status: queued
surface: none                      # 'none' for internal reports; 'gmail'/'slack' if a draft awaits sending
action_required: "Review the weekly status. Internal — no external send required."
artifact: 2026-05-22-weekly-status.md
related_milestones: [M03, M07]     # optional
expires: 2026-05-30                # optional — set for deadline-bound reports (claims, SC packs)
```

Field guidance by report type:
- **Weekly / monthly brief / dashboard** → `kind: report`, `surface: none` (internal review).
- **SC pack / agenda** → `kind: doc`, `surface: none`, set `expires` to the SC meeting date.
- **Quarterly claim** → `kind: report`, `surface: none`, `expires` = the 20th. The
  *cover email* draft is emitted separately by `project-funder-reporting` as a
  `gmail_draft` card with the Gmail `deep_link`.

Do **not** create the card with `status` anything but `queued`. Approval, deep-link
reveal, and the move to `approved/`→`sent/` are the UI's job, not the generator's.
Write the card via `project-state` (so the activity log records the emission); never
write external surfaces here.

## Discipline

- **Never invent facts.** If `percent_complete` isn't current, report the last known value and flag the staleness. Do not estimate.
- **Health ratings come from state, not vibes.** Override only if the caller provides an explicit reason; log the override.
- **Sources are traceable.** Every number in a report is backed by a file in `project-state/`. Reports reference that file by id in a footnote when depth matters.
- **Pre-publication review.** If a report will go public (blog, press), route through `project-external-comms` for the 30/14-day SC review per MPA.

## Integration

- **project-state** — reads everything; writes report entities, drops outbox cards into the queue lane, and bumps counters in the state record.
- **project-milestone-manager** — primary milestone data source.
- **project-phase-gate** — current phase + gate pending items.
- **project-change-register** — pending / recent changes for SC pack and weekly.
- **project-funder-reporting** — does the detail work for quarterly claims and other funder reports.
- **project-doc-suite-generator** — shares docx/xlsx rendering primitives; produces baseline report bundles.
- **project-notifier** — routes the finished report to Slack, Gmail draft, or Calendar hold.
- **project-blog-publisher** — downstream consumer for public-friendly progress.
