---
name: project-funder-reporting
description: Generic funder/customer reporting owner. Invoke only for an explicit stakeholder-bound claim/report request, a due enabled reporting-matrix entry, or a required trigger from an active pack with a matching funder-reporting profile. Preserve the profile's form, deadlines, format, cover-email, signoff, and established output paths. Drafts only; never submits, and never runs in parallel with another report owner for the same period.
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Funder Reporting (v2.0 — was project-claim-prep)

This skill produces stakeholder-bound recurring reports — anything that one named recipient (or recipient group) needs at a defined cadence in a defined format. Funder claims are one case; customer invoices, board packs, milestone-billing reports, and stage-gate submissions are others.

The skill itself is generic. Funder/customer/recipient-specific behavior comes from a **profile** loaded by the active pack:

- **PIC pack** profile (`packs/pic-pcais/profiles/funder-reporting.yaml`) — quarterly claim, Apr/Jul/Oct/Jan 20 deadlines, MS & financial xlsx field mapping, PIC PM cover-email template, percent-complete + technical-progress per-milestone fields. Reproduces v1.x behavior.
- **Client-services pack** profile — monthly customer invoicing, milestone-based billing entries, customer change-order coordination.
- **Board-investor pack** profile — board pack template, KPI dashboard data, monthly cadence.

## What it owns

- Reading the active profile from the loaded pack(s)
- Pulling milestone state, tasks, expenses, KPIs from the substrate
- Filling the configured template (xlsx / docx / pdf / md)
- Generating the cover delivery (Gmail draft via `project-notifier`)
- Writing the report artifact to `reports/<stakeholder>/<YYYY-QN>-<report-kind>.<ext>`
- For a quarterly claim profile, also writing the established
  `reports/claims/YYYY-QN.yaml` claim record through `project-state` locking
- Emitting an outbox card (`gmail_draft` with deep-link) into `outbox/queue/` for review
- Logging the deliverable and signoff to the activity log

## What it does not own

- Authoring funder-specific templates — those live in the pack
- Submitting reports — always stops at a draft for human signoff
- Defining the cadence — that's in the stakeholder reporting matrix

## Sub-actions

### `draft <stakeholder> <report-kind>`
Produces the next cycle's draft. Reads matrix entry → loads profile → assembles report.

### `lookahead [days]`
Lists upcoming reporting deadlines from the matrix. Default 30 days.

### `finalize <draft-id>`
Marks a draft as PL-signed-off, writes signoff event to activity log, hands to `project-notifier` for delivery.

## Outbox emission (queue the draft for review)

When `draft` produces a funder report, **emit an outbox card** for human review and
action. A separately installed compatible UI may render the queue. Unlike internal status reports, funder
reports usually end in an *external send the human performs* — so the card is a
`gmail_draft` carrying the deep-link to the already-created Gmail draft. Card files
live in `project-state/outbox/queue/` as a `<id>.md` + `<id>.meta.yaml` pair
using the card fields defined below.

Two-part pattern for a quarterly claim:
1. **The deliverable** — the filled `.xlsx` stays under `reports/pic-submissions/`.
   It is *not* the artifact; it's the attachment the human will attach/verify.
2. **The card** — `kind: gmail_draft`, artifact = a short markdown cover note (the
   email body for review), `surface: gmail`, with `deep_link` pointing at the Gmail
   draft that `project-notifier` created (review-not-author). Always set `expires` to
   the funder deadline (e.g. the 20th) so the queue sorts it by urgency.

```yaml
id: 2026-07-15-gmail-claim-q2
kind: gmail_draft
title: "Q2 PIC claim cover email — draft"
produced_by: project-funder-reporting
produced_at: 2026-07-15T06:00:00Z
status: queued
surface: gmail
action_required: "Open the draft in Gmail, attach/verify the xlsx, and send."
deep_link: "https://mail.google.com/mail/u/0/#drafts/<id>"   # from project-notifier
artifact: 2026-07-15-gmail-claim-q2.md
related_milestones: [M03, M07]
expires: 2026-07-20
```

The card is always `status: queued`. The Gmail draft already exists (notifier made
it); approval only reveals the deep-link — it never sends. If
`project-notifier` hasn't produced a draft yet (no deep-link available), still emit
the card with `surface: gmail` and `action_required` describing the manual step, and
omit `deep_link`. Board-pack and invoice profiles follow the same shape with their own
`kind`/`surface` (`doc`, `gmail_draft`) and deadline as `expires`.

## Triggers (handled by orchestrator + matrix)

- 14 days before a quarterly deadline → draft
- Monthly close day → all month-end reports drafted in batch
- On `funder-reporting.<stakeholder>.requested` event in activity log → ad-hoc draft

## Migration from v1.x

The v1.x `project-claim-prep` skill was hard-wired to the PIC quarterly form.
The public v4.9.0 archive does not include the proprietary MS & financial
tracking workbook referenced by the PIC profile. Require the operator to supply
the governing workbook path before producing a PIC claim; never synthesize or
silently substitute a compliance form. Existing claim drafts in
`reports/claims/` remain unchanged.

If you load only the PIC pack, behavior is identical to v1.x. Loading a customer pack alongside adds new reporting matrix entries (customer invoices, customer reports) without affecting the PIC claim flow.
