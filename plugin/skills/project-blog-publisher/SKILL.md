---
name: project-blog-publisher
description: "Draft a Project State progress post only when the operator explicitly requests it, a configured blog surface is available, or an active pack's due enabled trigger requires it. Preserve all MPA/pack review windows and approval rules. Nothing posts automatically, including team-internal content; external publication requires explicit authorization after review."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Blog Publisher

## Purpose

Progress announcements are a key part of PIC-funded project communications — both for funding acknowledgement (PIC + ISED) and for ecosystem visibility. This skill turns state into posts.

It respects the MPA publication discipline: every public post must go through the 30/14-day Steering Committee review before it goes out. Abstract-level posts get 14 days; full content posts get 30. Team-internal posts are exempt; consortium-level posts use a lighter review.

## Trigger phrases

- "blog post about [milestone]"
- "progress post" / "public update"
- "post to scsiwyg" / "publish the post"
- "update the project blog"
- "announce [something] publicly"
- "write up Q2" / "write up this sprint"
- "what should we blog about"

## Audience tiers

Three tiers drive review rules and publishing targets:

| Tier       | Distribution         | Review clock   | Handled by                |
| ---------- | -------------------- | -------------- | ------------------------- |
| Team       | Internal only        | None           | Direct publish (private)  |
| Consortium | Consortium members   | Lightweight (SC Chair ack) | Consortium-only scsiwyg or access-limited post |
| Public     | Open web             | 30 days full / 14 days abstract (per MPA) | Full SC review → publish  |

The tier is set in `manifest.yaml:surfaces.scsiwyg.blog_audience` as a default, but each post can override.

## Operations

### `suggest_topics()`

Scan state for blog-worthy moments:
- Milestone completions (especially the project-phase transitions — P1 done, P2 done…)
- Decisions with public interest (technology choice, partner engagement)
- Publications cleared for public (cross-link)
- Quarterly summaries
- Ecosystem collaborations (PIC cluster events, conference talks)

Return a ranked list with proposed angle, suggested tier, and state references.

### `draft(topic, tier)`

1. Pull relevant state (milestone, decision, quarter summary) via `project-state`.
2. Produce a draft `.md` in `communications/blog-drafts/YYYY-MM-DD-<slug>.md` with frontmatter:
   ```yaml
   ---
   title: "..."
   tier: team|consortium|public
   state_refs: [M02-a47-data-infrastructure, decision-2026-05-01-cloud-choice]
   status: drafted
   sc_review_started: ~
   sc_review_ends: ~
   approved_for_tier: ~
   published_url: ~
   ---
   ```
3. Include PIC + ISED funding acknowledgement on any public post. Per PIC PM Guide §Communications: "Consortium Members will endeavor to include a funding acknowledgement to PIC and ISED in any Publications and the contributions of other members of the Consortium."
4. For public posts, add a call-out: "This draft is subject to the 30-day SC review clock per MPA §Publications."

### `start_review(draft_id)`

For consortium or public tier:
1. Transition draft `status: under_review`.
2. Set `sc_review_started` to today; compute `sc_review_ends` (today + 30 days full, + 14 days abstract).
3. Via `project-notifier`:
   - Gmail draft to SC designates + PIC PM (for public) with the draft attached
   - Slack post to `alerts` channel
4. Call `project-external-comms` to register as a formal publication proposal (it tracks the clock and the SC review record).

### `publish(draft_id, url_slug?)`

1. Confirm SC review clock is either satisfied (public) or N/A (team).
2. Use `mcp__scsiwyg__create_post` with the markdown body, title, and tags.
3. Update the draft frontmatter: `status: published`, `published_url`, `published_date`.
4. Via `project-notifier`, post a Slack update and — for public posts — offer Gmail/X (Twitter) announcement drafts via the scsiwyg shares surface.
5. Log `publication.published` via `project-state`.

### `revise(draft_id, feedback)`

If SC review returns revisions, increment version and re-start the review clock per MPA terms.

## MPA publication discipline

- **30 days for full publications; 14 days for abstracts.** These are from PIC PM Guide / MPA.
- **SC must review before public posts.** No exceptions — this is an MPA obligation.
- **If IP or trade secrets are at stake**, the Publishing Party must delay to allow patent filing or remove the sensitive content. `project-external-comms` enforces this; this skill defers to it.
- **Public posts need PIC + ISED funding acknowledgement.** Add a standard footer block to every public draft.
- **No party may publish another party's data/info without consent.**

## Discipline

- **Team > consortium > public is a one-way upgrade.** A public-tier post can be distributed to team first; a team-tier post cannot jump to public without the review cycle.
- **Never auto-publish a public post.** Even with the 30-day clock satisfied, stop at a draft for explicit user go-ahead.
- **Include state references.** Every post should trace back to specific `project-state/` entities so its claims are verifiable.
- **Announcements cannot pre-empt PIC's press.** Per PIC PM Guide §First Steps: "projects cannot be announced prior to PIC's press release or announcement date for the project." The skill blocks public posts until `manifest.yaml` records a PIC announcement date.

## Outbox emission (queue the draft for review)

Every blog draft emits an outbox card into `project-state/outbox/queue/` as a
`<id>.md` + `<id>.meta.yaml` pair (contract: `docs/OUTBOX.md`), always
`status: queued`. The draft post body is the artifact.

- `kind: blog_post`, `surface: scsiwyg`.
- `action_required:` describes the human's final step — for **team/consortium**
  tier: "Review and publish to scsiwyg." For **public** tier: "Public post —
  confirm SC review clock satisfied, then publish." Never auto-publish (see
  Discipline); approval in the UI only reveals the action, it does not call scsiwyg.
- If a public post is still inside its MPA review window (30-day full / 14-day
  abstract), set `expires` to the date the clock clears and keep
  `action_required` explicit that it is **not yet clearable**. Defer the actual
  gate enforcement to `project-external-comms`.
- `deep_link` is omitted until the post exists in scsiwyg; for a pre-publish draft
  the human publishes from the queue's review view, so no link is needed yet.

```yaml
id: 2026-05-22-m01-release-post
kind: blog_post
title: "v3.2 release announcement — draft"
produced_by: project-blog-publisher
produced_at: 2026-05-22T06:00:00Z
status: queued
surface: scsiwyg
action_required: "Public post — confirm PIC announcement date + SC review, then publish to scsiwyg."
artifact: 2026-05-22-m01-release-post.md
related_milestones: [M01]
```

## Integration

- **project-state** — reads milestones, decisions, publications; writes drafts and emits `outbox/queue/` cards.
- **project-external-comms** — formal publication tracker (SC review clock, patent delay rules).
- **project-status-reporter** — source of narrative material (weekly/monthly/quarterly summaries).
- **project-notifier** — Slack / Gmail distribution of drafts and published posts.
- **project-milestone-manager** — milestone-completion is a common blog trigger.
- **scsiwyg MCP** — final publish via `mcp__scsiwyg__create_post` and sharing via `mcp__scsiwyg__share_to_twitter`.

## Reference files

- `references/funding-ack-template.md` — PIC + ISED acknowledgement block for public posts
- `references/tier-playbook.md` — when to choose team vs. consortium vs. public
