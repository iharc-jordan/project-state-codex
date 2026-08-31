---
name: project-review-meeting
description: "Manage a recurring review-meeting lifecycle only when an active pack provides a review-meeting profile or the operator explicitly requests it: scheduling, agenda, pre-read logistics, minutes, and action-item filing. Route a Steering Committee status-pack request to project-status-reporter and reuse that single generated pack. Preserve PIC/board/QBR/retro profile rules and never distribute externally without authorization."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Review Meeting (v2.0 — was project-sc-meeting)

Lifecycle for any recurring review meeting where decisions get made, status gets reported, and action items get filed. Steering Committees are the grant-world case; board meetings, customer QBRs, sprint retros, exec reviews, and partner check-ins are others.

The skill itself is generic. Meeting-shape comes from the profile loaded by the active pack:

- **PIC pack** profile (`packs/pic-pcais/profiles/review-meeting.yaml`) — name "Steering Committee", PIC PM Guide Appendix A agenda, 5-business-day notice minimum, 5-business-day minutes distribution window, the four designate roles (Project Lead / Finance Rep / Communications Rep / Signing Authority per consortium member), PIC PM as non-voting attendee, quarterly minimum cadence.
- **Board-investor pack** profile — name "Board Meeting", monthly cadence, board pack template, board-member roster.
- **Client-services pack** profile — name "Quarterly Business Review", quarterly cadence, customer attendees, QBR pack template.
- **Agile-default pack** profile — name "Sprint Retrospective", sprint cadence, team attendees, retro template.

## What it owns

- Scheduling per the profile's cadence + notice rules
- Agenda assembly from the profile's template plus current substrate state
- Pre-read pack assembly (status reporter output + decisions log + risk register slice)
- Calendar invite drafts (via `project-notifier`)
- Minutes capture (manual or transcript-fed) and distribution within the profile's window
- Action-item filing as tasks linked to the meeting record
- Emitting outbox cards (pre-read pack + calendar hold) into `outbox/queue/` for review

## What it does not own

- Running the meeting itself
- Defining the agenda template — that's in the pack
- Sending invites — calendar items are proposed holds for human send
- Sending minutes — Gmail items are always drafts

## Outbox emission (queue the draft for review)

A review meeting produces two card-worthy drafts; emit both into
`project-state/outbox/queue/` as `<id>.md` + `<id>.meta.yaml` pairs using the
fields below, always `status: queued`:

1. **Pre-read pack** — `kind: doc`, `surface: none`, artifact = the assembled
   agenda + pack markdown (or a cover note linking the `.docx` under `reports/`).
   Set `expires` to the meeting date so it sorts up as the meeting nears.
2. **Calendar hold** — `kind: calendar_hold`, `surface: calendar`,
   `deep_link` to the proposed hold `project-notifier` created (calendar items are
   *proposed holds*, never auto-accepted). `action_required:` "Review the hold and
   send the invite." `expires` = the notice deadline (cadence minus
   `notice_minimum_days`).

```yaml
id: 2026-06-30-sc-q2-preread
kind: doc
title: "SC Q2 pre-read pack — draft"
produced_by: project-review-meeting
produced_at: 2026-06-23T06:00:00Z
status: queued
surface: none
action_required: "Review the SC pre-read pack before distribution."
artifact: 2026-06-30-sc-q2-preread.md
expires: 2026-06-30
```

Approving in the UI reveals the calendar deep-link; it never sends the invite or
distributes the pack. Minutes drafts (post-meeting) emit the same way as a
`kind: gmail_draft` card with the distribution deadline as `expires`.

## Profile shape

```yaml
# packs/<pack>/profiles/review-meeting.yaml
meeting_name: "Steering Committee"
short_id_prefix: "SC"
cadence: { kind: quarterly, alignment: "month-end" }
notice_minimum_days: 5  # business days
minutes_distribution_max_days: 5  # business days
attendee_roles:
  - { id: project_lead, required: true }
  - { id: finance_representative, required: true }
  - { id: communications_representative, required: true }
  - { id: signing_authority, required: true }
  - { id: funder_pm, required: false, voting: false }
agenda_template: "templates/sc-agenda-appendix-a.md"
preread_assembly:
  - status-reporter.weekly
  - status-reporter.dashboard-snapshot
  - milestone-manager.at-risk
  - risks.recently-changed
  - decisions.recently-recorded
```

## Migration from v1.x

The v1.x `project-sc-meeting` skill is renamed to `project-review-meeting`. The PIC pack ships a profile that reproduces the SC behavior exactly. If you load only the PIC pack, your existing SC-001, SC-002, … records are unchanged and the skill still produces Appendix-A-formatted packs.

For projects loading non-PIC packs, the meeting name and shape come from those packs' profiles. Multiple meeting kinds (SC + board + QBR) coexist by being separate entries in the stakeholder reporting matrix with different generators.
