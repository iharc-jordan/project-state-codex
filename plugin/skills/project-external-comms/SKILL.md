---
name: project-external-comms
description: "Run the external-communication review pipeline only for an explicit review request or when an active pack supplies the applicable external-comms profile. Preserve content-class review windows, acknowledgements, confidentiality, patent-delay, and approval rules. If no profile applies, report the feature as unconfigured; never publish or send automatically."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project External Comms (v2.0 — was project-publications)

The publication-review-clock pattern, generalized. Anything that crosses the project's audience boundary — papers, abstracts, presentations, press releases, blog posts marked public, marketing-side announcements — runs through this skill's review pipeline. The clock window and review authority come from the profile loaded by the active pack.

The skill itself is generic. Audience-bound review rules come from the profile:

- **PIC pack** profile (`packs/pic-pcais/profiles/external-comms.yaml`) — 30-day full publication review, 14-day abstract review, mandatory PIC + ISED + Government of Canada funding acknowledgement, patent-filing-delay coordination, SC-as-reviewer.
- **Corporate-PR pack** profile — 7-day legal review, brand-team approval, embargo coordination.
- **Client-confidentiality pack** profile — customer NDA review, sensitive-data scrubbing, customer-approval-required.

## What it owns

- Logging proposed external content with classification (paper / abstract / talk / press / blog-public)
- Starting the review clock per the profile's window-by-content-class
- Tracking review state through reviewer signoffs
- Holding the deploy/publish until the clock clears
- Funding-acknowledgement template injection (per profile)
- Confidentiality screening prompts (per profile)
- Patent-filing-delay coordination with `project-ip-tracker` (when enabled)

## What it does not own

- Authoring publications, abstracts, or press releases
- Sending material out — always stops at "cleared for external" status
- Defining the review window — that's in the profile

## Sub-actions

### `propose <content-id> <class>`
Logs a proposed external content item, starts the review clock per profile rules.

### `status <content-id>`
Reports current state: in_review / cleared / blocked + days remaining on clock.

### `clear <content-id>`
Marks reviewers' signoff complete. Once clock has elapsed AND signoffs are complete, status flips to cleared — and an outbox card is emitted (see Outbox emission).

### `block <content-id> <reason>`
Reviewer pauses the clock. Common reasons: confidentiality concern, patent-filing in progress, missing acknowledgement.

## Outbox emission (queue the cleared item for action)

This skill does not author content, so it emits at a different moment than the
generators: **when an item flips to `cleared`** (clock elapsed AND signoffs
complete), emit an outbox card into `project-state/outbox/queue/` announcing the
content is now safe to send externally. Contract: `docs/OUTBOX.md`; always
`status: queued`.

- `kind` mirrors the content class: `paper`/`abstract`/`talk` → `doc`,
  `press`/`blog-public` → `blog_post`, an email send → `gmail_draft`.
- `surface` is wherever the human will act (`scsiwyg`, `gmail`, or `none`).
- `action_required:` "Cleared for external release — publish/send." Include the
  content-id so it traces back to the publication record.
- Do **not** emit a card while an item is `in_review` or `blocked`. The whole point
  of this skill is to hold the gate; the card appears only once the gate opens.
- While the clock is still running, the *draft* card emitted by
  `project-blog-publisher` (with `expires` = clock-clear date) is the queue's
  placeholder; this skill's job is to gate it, not to surface it early.

Approving in the UI reveals the publish/send action; it never publishes. The
existing review-clock and signoff logic is unchanged — emission is an additional
step inside `clear`, after the status flip is logged.

## Migration from v1.x

`project-publications` is renamed to `project-external-comms`. The 30/14-day MPA clock survives in the PIC pack profile. Existing publication records in `publications/` are unchanged. The funding acknowledgement template (PIC + ISED) moves into the PIC pack as a referenceable fragment.

Projects without a funder/MPA can load a corporate-PR or open-source profile with different windows. Projects that publish nothing externally simply don't load any external-comms profile — the skill becomes inert.
