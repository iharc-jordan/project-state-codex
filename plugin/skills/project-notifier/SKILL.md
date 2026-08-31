---
name: project-notifier
description: "Route an approved Project State artifact only to a configured, available Slack, Gmail-draft, Calendar, or blog surface, or when the operator explicitly requests surface setup. A generator may offer this handoff but must not invoke an unconfigured surface. Require authorization for posts/events; Gmail remains draft-only. Log one delivery event through project-state."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Notifier

## Purpose

Centralize the "how does this artifact reach a human?" decision. Other skills produce payloads (a weekly report, a phase transition, a claim draft, an SC reminder, a risk alert). This skill routes them to Slack, Gmail, Calendar, or the scsiwyg blog.

**Design principles:**
- **Gmail is always a draft.** Never auto-send. The human reviews and sends.
- **Config is in the manifest.** Channel names, from-identities, calendar IDs live in `manifest.yaml:surfaces`. This skill reads them; it doesn't carry its own config.
- **One log entry per delivery.** Every push to a surface is an activity event.
- **Retries are cheap; idempotency matters.** Give each delivery a deterministic key so repeating the same notification doesn't double-post.

## Trigger phrases

- "post to Slack" / "send to #channel" / "ping the team"
- "email to PIC" / "draft an email to PM" / "Gmail draft"
- "calendar the SC meeting" / "put this on the calendar" / "schedule a hold"
- "alert about the at-risk milestone"
- "notify [audience] about [thing]"

## Surfaces

### Slack

Reads `manifest.yaml:surfaces.slack.channels`:
- `daily_standup` — brief daily updates
- `weekly_report` — Monday weekly report
- `alerts` — phase transitions, overdue claims, SC reminders, at-risk milestones

If a named channel is `~`, warn the caller and abort that specific surface (don't fail the whole notification).

**Uses:** the Slack MCP (`mcp__*__slack_send_message` etc.).

**Formatting rules:**
- Weekly reports: multi-block, use the report markdown; Slack handles it well.
- Alerts: compact, with "why now?" in the first line.
- Claim reminders: include the deadline in ISO-8601 and the PIC contact.

### Gmail

Reads `manifest.yaml:surfaces.gmail.from_identity` + `default_recipients`.

**Always drafts.** Uses `mcp__*__create_draft`. The user sends manually.

**Default email templates (adjust for tone):**
- PIC Project Manager: formal, per-paragraph framing matching the PIC PM Guide vocabulary
- Consortium Members: collegial, technical where relevant
- SC distribution: follow the 5-business-day minutes-distribution template

Draft subject prefix conventions:
- `[PIC Update] ` — to PIC
- `[Consortium] ` — to Consortium Members
- `[SC] ` — Steering Committee
- `[Claim Q2 2026] ` — claim-related

### Google Calendar

Reads `manifest.yaml:surfaces.google_calendar.calendar_id` + `event_prefixes`.

**Event prefixes** ensure Project-related events are visually grouped:
- `[SC] ` — Steering Committee meetings
- `[PIC Claim Due] ` — claim deadlines
- `[PIC Milestone] ` — milestone boundaries
- `[Internal] ` — team-internal reviews / standups

**Event fields:**
- `description` must include a link back to the `project-state/` entity it's about (e.g., `reports/sc-meetings/2026-Q2-01.yaml`).
- For SC meetings: send invites to the SC designates (from `people/` files), at least 5 business days in advance.

### scsiwyg

Routed through `project-blog-publisher`, not this skill directly. If the user says "post to blog", invoke blog-publisher.

## Operations

### `notify(audience, artifact_ref, channel_hint?)`

Input: an audience label ("team", "pic-pm", "consortium", "sc", "exec") and a reference to an artifact in `project-state/` (path or id), plus optional channel override.

Flow:
1. Resolve audience → channel(s). `audience=team + artifact=weekly report` → Slack `weekly_report` channel. `audience=pic-pm + artifact=claim draft` → Gmail draft.
2. Format the payload for the target.
3. Deliver (Slack: send; Gmail: create draft; Calendar: create event).
4. Log `notify.posted` or `notify.drafted` via project-state, with target, artifact_ref, and the resulting message/draft/event id.
5. **Backfill the outbox card** (see Outbox deep-link backfill) — if a queued card references this artifact, stamp the new draft/event URL onto its `deep_link`.

### `schedule_event(title, start, end, invitees, description, prefix)`

Create a Google Calendar event with the given fields. Return the event id; log `calendar.event.created`.

Use cases:
- SC meeting — prefix `[SC] `, invite designates, include link to `reports/sc-meetings/<id>-agenda.docx`.
- Claim deadline — prefix `[PIC Claim Due] `, 1-day all-day event on Apr/Jul/Oct/Jan 20, reminder 14 days prior.
- Milestone boundary — prefix `[PIC Milestone] `, all-day on planned_end.

### `reminder(entity_id, days_before, channel)`

Set up a reminder N days before a date. Executed by `project-orchestrator` via `schedule` skill; `project-notifier` just defines the reminder payload.

## Outbox deep-link backfill

Generators emit outbox cards into `outbox/queue/` with `surface` set but often **no
`deep_link`** — because the external draft doesn't exist yet. `project-notifier` is
what *creates* that draft (Gmail) or proposed hold (Calendar), so it owns stamping the
link back onto the card. This is the seam that makes a `gmail_draft` / `calendar_hold`
card actionable end-to-end: generator says "this needs sending," notifier creates the
review-not-author draft and records *where* it lives.

**When** `notify` or `schedule_event` produces a draft/event for an artifact that has a
matching queued card (match on `artifact` filename or `artifact_ref` → card `id`):

1. Read the card's `<id>.meta.yaml` from whichever outbox folder it's in (normally
   `queue/`).
2. Set `deep_link` to the created Gmail draft URL or Calendar event URL.
3. Leave `status` untouched — backfilling a link is **not** approval. The card stays
   `queued`; the human still reviews and actions it from the file queue or a compatible viewer.
4. Route the write through `project-state` so the edit is logged
   (`outbox.deep_link.backfilled`).

If no matching card exists, do nothing — not every notification corresponds to a queued
draft. Never create a card here; emission is the generator's job, linking is notifier's.

## Idempotency

For each notification, compute a deterministic `delivery_key`:
```
delivery_key = sha1("{audience}|{artifact_ref}|{date}|{channel}")
```
Before delivering, check `state.json:recent_notifications[delivery_key]`. If present and dated within 6 hours, skip (the user must have already triggered it). Otherwise record it after successful delivery.

This lets `project-orchestrator` call `notify` eagerly without worrying about duplicate Monday-morning weekly posts.

## Discipline

- **Never auto-send Gmail.** If the surfaces config were ever mutated to `always_draft: false`, refuse to send and escalate. This is an MPA/PIC compliance concern.
- **Never post to public Slack channels without reviewing confidentiality.** Default all posts to internal channels; public-adjacent posts route through `project-external-comms` first.
- **Respect the MPA publication clock.** If a notification includes results that haven't cleared the 30/14-day SC review, route through `project-external-comms` first.
- **Include links, not screenshots.** Every Slack/Gmail message references the canonical `project-state/` file by path so the recipient can click through.

## Integration

- **project-state** — reads surfaces config; writes `notify.*` events; backfills `deep_link` onto matching `outbox/` cards; maintains `recent_notifications` key map.
- **project-status-reporter** — biggest caller; produces weekly/SC/claim payloads.
- **project-orchestrator** — drives reminders and calendar holds on schedule.
- **project-review-meeting** — uses this for invites + minutes distribution.
- **project-funder-reporting** — uses this for deadline reminders and PIC PM draft email.
- **project-phase-gate** — phase transitions alert the team.
- **project-blog-publisher** — parallel skill for scsiwyg; shares the publication-review discipline.
