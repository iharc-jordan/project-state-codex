---
name: tender-monitor
description: "The change-detection layer of the tender-intelligence package. Re-check followed tenders across their sources (CanadaBuys watch feeds, listing re-fetches, amendment emails flagged by tender-harvester), diff against stored state, and emit typed change events to tenders/events.ndjson and the activity log: tender.amended, tender.deadline.changed, tender.document.revised, tender.cancelled, tender.awarded. Trigger on 'check for amendments', 'any changes on the tenders we're watching', 'monitor t-2026-0041', 'follow this tender', 'did the closing date move', 'stop following', or when tender-harvester flags amendment notifications. Every material change carries previous value, new value, and an evidence URL."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# tender-monitor

Notice what changed on tenders the facility cares about, record it durably, and let the notifier escalate. Monitoring is per-tender (`monitoring.followed: true`), automatically enabled when a tender reaches `under_review` or later, or manually via "follow".

## Preconditions

Facility located; package enabled; connector health readable. Monitoring respects the same politeness ledger and never-authenticate rules as `tender-harvester`.

## Sub-actions

### `sweep` (default)

For every followed, non-terminal tender (status not in `dismissed`, `closed`, `cancelled`, `awarded`, `unsuccessful`):

1. **Pick the cheapest authoritative channel per source:**
   - CanadaBuys → the notice's watch feed if registered (`monitoring.watch_feed_url`), else the public notice page;
   - SaskTenders / GEM / bids&tenders → cached detail page re-fetch (ledger-gated) and any amendment emails flagged by the harvester;
   - external submission systems (Bonfire, SAP Ariba…) → the recorded `submission_url` page when public; never log in.
2. **Diff** the fresh capture against the entity: closing date/time; question deadline; mandatory meeting; status (open/amended/cancelled/awarded); document list (new addenda, revised/replaced files by name+hash where retrievable, Q&A additions); scope text (synopsis hash); contacts.
3. **Emit events** for every material difference (see table), then update the entity fields, `monitoring.last_change_at`, `monitoring.amendment_count`, and `sources[].last_checked_at` — one memory-layer write per tender.
4. Report a sweep summary and remind which changes triggered immediate notifier rules.

### `follow` / `unfollow`

Set `monitoring.followed`. For CanadaBuys, when the user has created a notice-level subscription, record `watch_feed_url`. Following a tender that lacks retrieved documents also nudges: "documents not yet retrieved — create the retrieval task?"

### `diff <tender-id>`

Show the change history for one tender: all `tenders/events.ndjson` lines for the id, rendered as a timeline with evidence links.

## Event vocabulary

| Change detected | Event | Notes |
| --- | --- | --- |
| New addendum / amended notice | `tender.amended` | `new_value` = addendum identifier/title |
| Closing date moved (either direction) | `tender.deadline.changed` | shortened deadlines are flagged `shortened: true` — immediate alert |
| Question deadline or mandatory meeting changed | `tender.deadline.changed` | `field` distinguishes which date |
| Document revised or replaced | `tender.document.revised` | supersession recorded in documents/index.yaml by the curator |
| Notice cancelled | `tender.cancelled` | terminalizes workflow via tender-pipeline suggestion |
| Award published | `tender.awarded` | if we submitted → pipeline `awarded`/`unsuccessful` flow |
| Scope/synopsis text changed | `tender.amended` | `field: synopsis`, old/new hashes |

Every line in `tenders/events.ndjson` carries: `ts`, `actor: tender-monitor`, `event`, `id`, `source`, `previous_value`, `new_value`, `evidence_url`, `parser_version`, `notification_sent`. The same event is appended to `logs/activity.ndjson` (summary form) under the write lock. **Never rewrite or delete event lines.** If a detection was wrong, append a correcting event (`superseded_ts` pointing at the bad line).

## Amendment handling rules

- A previously **qualified** tender gaining a possible disqualifier (e.g. new mandatory clearance in an addendum) → flag for `tender-qualifier qualify` re-run and immediate notification; set `qualification.status: needs_review`.
- New addenda on tenders in `preparing_response` are always material → immediate alert regardless of content.
- A shortened deadline on any followed tender → immediate alert (spec §17.1).
- Amendment before discovery (email arrived for unknown tender) → harvester creates the entity; monitor then records the amendment normally.

## Cadence

Watch feeds hourly with the CanadaBuys feed run; listing-based re-checks ride the 4-hour listing cadence; a full sweep belongs in the facility's daily routine (project-orchestrator proposes it). Between sessions, scheduled harvesting runs invoke `sweep` after `tender-harvester all`.

## Output format

```
Monitor sweep — 6 followed tenders

  t-2026-0041  CanadaBuys   closing 2026-08-14 → 2026-08-21 (+7d)   tender.deadline.changed  → alert sent
  t-2026-0102  SaskTenders  addendum 3 posted                        tender.amended           → alert sent
  t-2026-0087  bids&tenders no change
  …
  1 re-qualification needed: t-2026-0102 (addendum adds insurance limit) → tender-qualifier qualify
```

## Boundaries

Detects and records; does not move workflow status (suggests `tender-pipeline`), does not re-score (suggests `tender-qualifier`), does not send notifications itself (the notifier reads the events), and writes only through the memory layer.
