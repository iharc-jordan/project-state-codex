---
name: project-status-reporter
description: "Own routine status views from Project State: weekly reports, Steering Committee status packs, monthly internal briefs, ad-hoc status, and dashboard snapshots. Use for weekly/status/SC-pack requests, or when a due enabled matrix entry or active pack requires one. Route funder/customer claims to project-funder-reporting and audience-specific briefs to project-onepager. Generate one draft per source event and period; never send."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Status Reporter

## Purpose

Turn the structured state under `project-state/` into readable reports in the formats the project's audiences actually consume. The project produces multiple report types on different cadences; they all draw from the same underlying facts.

**Design principle:** the report is a *view* of state. If the report is wrong, the state was wrong or the template was wrong. Reports are never a place where new facts are first recorded.

## Report catalog

| Report                       | Format        | Cadence            | Audience                | File location                          |
| ---------------------------- | ------------- | ------------------ | ----------------------- | -------------------------------------- |
| Weekly report                | .md + Slack   | Weekly (Mon)       | Project team            | `reports/weekly/YYYY-Www.md`           |
| Monthly technical brief      | .md + Gmail   | Monthly (last Fri) | Consortium members      | `reports/adhoc/YYYY-MM-brief.md`       |
| SC pack                      | .docx         | Quarterly          | Steering Committee + PIC| `reports/sc-meetings/<id>-pack.docx`   |
| SC agenda                    | .docx         | Quarterly          | SC pre-meeting          | `reports/sc-meetings/<id>-agenda.docx` |
| Quarterly claim (MS & financial tracking form) | .xlsx | Apr/Jul/Oct/Jan 20 | PIC Project Manager     | `reports/pic-submissions/YYYY-QN-ms-financial.xlsx` |
| Ad-hoc status                | .md / email   | On demand          | Varies                  | `reports/adhoc/YYYY-MM-DD-<slug>.md`   |
| Dashboard snapshot           | 1-page .md    | On demand          | Exec glance             | `reports/adhoc/snapshot-YYYY-MM-DD.md` |
| Final report (per member)    | .docx         | Project close      | PIC                     | `reports/pic-submissions/final-<org>.docx` |

## Trigger phrases

- "weekly report" / "draft the weekly" / "Monday report"
- "SC pack" / "prep next SC meeting" / "agenda for the steering committee"
- "status update" / "how is the project" / "what's our status"
- "snapshot" / "dashboard"
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
- Activity log tail since the last weekly (`since = state.json:pointers.last_weekly_report`)
- Gate status of current phase from `project-phase-gate`
- Upcoming deadlines (from `manifest.yaml:reporting_calendar` + milestone planned_ends)

**Output template (`reports/weekly/YYYY-Www.md`):**

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

Hand off to `project-notifier` for Slack delivery. Update `state.json:pointers.last_weekly_report` + `counters.weekly_reports`.

## Steering Committee pack

**Inputs:** everything, but specifically shaped for the PIC Appendix A standard agenda (9 topics: Introduction; Review of Previous Minutes; Project Schedule/Overview/Milestones; Change Orders & Change Log; Project Finances; Publications/Media; IP Update; Regulatory Check-In; Key Contact Updates; Open Discussion / Lessons Learned; Action Steps Review; Next Meeting).

**Output:** one `.docx` following PIC's agenda format. Use `python-docx` for
rendering (shared primitives with `project-doc-suite`). Embed:
- Gantt-style view of milestones (status, % complete, planned vs. actual)
- Finances table (budget vs. spend — if available)
- Active risks (top 5 by score)
- Recent Change Log entries + any open Change Orders
- Publications in review / approved
- IP disclosures since last SC
- Action items from previous meeting with status

Companion `agenda.docx` is lighter — just the agenda skeleton for the 5-business-day pre-meeting distribution.

## Funder/customer claim routing

Route a request for a quarterly claim, customer invoice, board/funder report, or
other stakeholder-bound recurring deliverable to `project-funder-reporting`.
Pass the audience, period, and active profile once and do not also generate a
status-reporter wrapper. The established claim/report paths and formats remain
owned by that skill.

## Ad-hoc status

The user says "status update for X" — produce a paragraph or two tailored to the audience:
- PIC Project Manager → formal, milestone-anchored, cautious on at-risk items
- Consortium Member internal → technical + honest
- Board / exec → outcomes + risks + asks

Save to `reports/adhoc/YYYY-MM-DD-<slug>.md`. Offer to hand off to `project-notifier` for Gmail draft.

## Dashboard snapshot

One page. Designed for a glance. Sections: phase + gate, health, milestones table, upcoming deadlines, top 3 risks, last 5 activity events. Saved to `reports/adhoc/snapshot-YYYY-MM-DD.md`.

## Outbox emission (queue the draft for review)

After writing any report to `reports/`, **also drop an outbox card** for human review.
The file queue is the public contract; a separately installed compatible UI may render
it. The person reviews/approves/actions it — the system never sends.

A card is a file pair in `project-state/outbox/queue/`:

1. **The artifact** — `<id>.md`. Reuse the report markdown you just produced (for
   docx/xlsx reports, write a short markdown cover note that links to the file under
   `reports/`). `<id>` is `YYYY-MM-DD-<slug>` (e.g. `2026-05-22-weekly-status`).
2. **The card** — `<id>.meta.yaml`, using this public contract:

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

- **project-state** — reads everything; writes `reports/` entries, drops outbox cards into `outbox/queue/`, and bumps counters via state.
- **project-milestone-manager** — primary milestone data source.
- **project-phase-gate** — current phase + gate pending items.
- **project-change-register** — pending / recent changes for SC pack and weekly.
- **project-funder-reporting** — does the detail work for quarterly claims and other funder reports.
- **project-doc-suite** — shares docx/xlsx rendering primitives and owns the full
  unified documentation bundle.
- **project-notifier** — routes the finished report to Slack, Gmail draft, or Calendar hold.
- **project-blog-publisher** — downstream consumer for public-friendly progress.
