---
name: tender-harvester
description: "Collect tender opportunities only when the tender-intelligence capability is enabled and at least one connector is configured, or when the operator explicitly requests setup. Preserve source coverage, cursor/health state, quarantine, politeness, and project-state write contracts. A due enabled capability trigger may run it; otherwise remain inert and never infer connector access."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# tender-harvester

Pull tender opportunities from configured sources and deposit them as `kind: tender` entities in the enabling facility, via the `project-state` memory layer. This skill discovers and normalizes; it does not score (`tender-qualifier`), track changes on followed tenders (`tender-monitor`), or move workflow status (`tender-pipeline`).

## Preconditions

1. Locate the facility: walk up from cwd to `project-state/manifest.yaml` (standard project-state discovery).
2. Confirm `manifest.yaml:packages.tender-intelligence.enabled: true`. If absent, stop: "Tender package not enabled in this facility — adapt the bundled `templates/tender/manifest-capability-block.yaml` into manifest.yaml."
3. Read the package block for sources, feeds, mailbox label, and intervals.
4. Read `state/tender-intelligence.json:tender_connectors` for cursors and health. Initialize missing connector entries with the schema-extension defaults before first use.

## Philosophy

Mirrors `project-harvester`: a focused lens driven entirely by facility configuration — no hardcoded searches. The collection hierarchy is fixed by spec: (1) official feeds, (2) official notification emails, (3) conservative public polling, (4) human-authenticated retrieval. The automated path holds **no portal credentials**; anything behind a login is a human task, created rather than attempted.

## Sub-actions

### `all` (default)

Run every enabled connector that is due (interval elapsed since `last_success`), in order: feeds → email → listings. Report a per-connector summary and emit one `tender.harvest.completed` activity event per connector run:

```json
{"ts":"…","actor":"tender-harvester","event":"tender.harvest.completed","id":"canadabuys-feed","summary":"12 entries, 3 new tenders, 1 updated, 0 errors"}
```

### `feeds` — CanadaBuys RSS/Atom

For each URL in `sources.canadabuys.feeds.discovery` (watch feeds belong to `tender-monitor`):

1. Fetch with `If-None-Match` / `If-Modified-Since` from the connector's stored `etag` / `last_modified`. On 304, record success and move on.
2. Parse RSS 2.0 or Atom (see `scripts/feed_poll.py` for the reference parser). Retain every entry's feed identifier (`guid`/`atom:id`) and updated timestamp.
3. For each entry newer than the cursor, or whose updated timestamp changed:
   - Extract the notice reference number from the entry link/id.
   - Check existing tenders for a source match (`sources[].portal == CanadaBuys && source_id == ref`). If found and unchanged, skip. If found and changed, update `last_checked_at` and hand the diff to `tender-monitor` conventions (write nothing yourself beyond the source block).
   - If new: fetch the public notice page; parse title, organization, notice type, status, publication date, closing date (preserve original timezone), regions of delivery, commodity codes (UNSPSC/GSIN), trade agreements, procurement method, contact where public, external tendering-system links.
   - Build the entity from `templates/tender/tender-entity-template.yaml`; `sources[0].role: discovery`; if the notice points to another submission portal, record `submission_url` and add a second source block with `role: submission`.
   - Write via memory layer → `tender.discovered`.
4. Update cursor, `etag`, `last_success`, `last_new_record`; reset `consecutive_failures`.

### `email` — MERX, SaskTenders, bids&tenders, CanadaBuys notifications

1. Search the Gmail surface for messages under `mailbox_label` newer than each email connector's `gmail_cursor`.
2. Identify the portal from sender domain and template shape:
   - `merx.com` → MERX new-opportunity / amendment notifications
   - `sasktenders.ca` / GEM senders → SaskTenders notifications
   - `bidsandtenders.ca` (and buyer-branded variants) → bids&tenders notifications
   - `canadabuys.canada.ca` → CanadaBuys email fallback
3. Parse per-template (reference field maps in `references/email-templates.md`): title; buyer; solicitation/competition number; publication date; closing date where present; category or saved-search name; canonical source URL; notification type (new | amendment | reminder).
4. **New opportunity:** dedupe against existing source ids and solicitation numbers; if new, create the entity with `qualification.status: preliminary` and the source block carrying `message_id`. Display convention: *"Preliminary match — full documents not yet reviewed."* If the notification implies documents behind login, set `documents.login_required: true` and leave a `documents_required` breadcrumb in `workflow.next_action`.
5. **Amendment notification:** do not mutate tender content here — record `last_checked_at` and note the amendment for `tender-monitor` to diff (its job to emit `tender.amended`). If the tender is unknown (amendment before discovery), create the entity first, then flag for monitor.
6. **Unrecognized template:** copy the raw message (headers + body) to `documents/inbox/quarantine/<message-id>.eml.txt`, log a warning in the harvest summary, do not advance the cursor past unparsed messages silently — quarantined messages count as processed only because their raw form is preserved.
7. Advance `gmail_cursor` (newest processed message's internal date); never reprocess by message id.

### `listings` — SaskTenders, GEM, bids&tenders public pages

Conservative by construction:

- **Politeness ledger first.** Before any request, check the global ledger (`scripts/politeness.py`; `~/.tender-politeness/ledger.json`) for the domain's minimum interval. If the ledger says wait, wait or skip this run. Record every request in the ledger. This holds across every facility on the machine.
- Default interval 4 hours per the package block; hard minimum 1 hour; one request at a time, no concurrency.
- Cache each listing page fetch under `documents/working/tender-cache/<connector>/` keyed by URL hash; fetch detail pages **only** for unseen or changed identifiers.
- On HTTP 403/429, CAPTCHA, or challenge pages: stop the connector immediately, set health `access_restricted`, do not retry this run, never attempt circumvention.
- Exponential backoff on errors: after `consecutive_failures` ≥ 3, set health `parsing_error` or `delayed` and alert via the notifier rule; after 5, set `paused: true` (admin unpauses).

Per source:

1. **SaskTenders:** fetch the open-competition listing; capture all visible competition numbers; compare with `seen_ids_hash` and stored source ids; fetch detail pages for unseen/changed ids; parse title, buyer, competition number, publication and closing date-times, status, synopsis, contact, response address, external submission system, document availability, login requirement. If the notice redirects to GEM/Bonfire/SAP, add source blocks with `role: documents` / `role: submission`.
2. **GEM:** distinct connector (`gem-listing`), same discipline; each Saskatchewan record retains discovery, document, and submission sources separately.
3. **bids&tenders:** poll only the approved `search_urls` from the package block; never enumerate the directory. Extract title, organization, bid type, status, closing date, source link, document-fee indication.

## Normalization rules

- Dates → ISO-8601 retaining the original UTC offset; also record `dates.original_timezone` (IANA name when derivable, else the offset).
- `normalized_title` / `buyer.normalized_name` → lowercase, collapse whitespace, strip punctuation.
- Buyer `type` from a fixed vocabulary (see schema extension); when uncertain, leave null rather than guess.
- Entity ids: `t-<year>-<zero-padded seq>`; sequence from `counters.tenders` + 1 under the write lock.
- Every entity write goes through the `project-state` memory layer (lock → staleness → write → log → counters). This skill **never** edits facility files directly.

## Health reporting

After each run, update the connector's `health`:

| Condition | Health |
| --- | --- |
| Run succeeded | `healthy` |
| Interval overdue > 2× | `delayed` |
| Parse failures this run | `parsing_error` |
| Login wall encountered on a needed page | `authentication_required` |
| 403/429/challenge | `access_restricted` |
| `paused: true` | `paused` |

## Output format

```
Tender harvest — <facility> — 2026-07-21 09:00 PT

  canadabuys-feed        12 entries   3 new   1 changed   healthy
  merx-email              4 messages  2 new   1 amendment healthy
  sasktenders-listing    41 ids       1 new   0 changed   healthy
  bidsandtenders-email    2 messages  1 new   0           healthy
  gem-listing            skipped (not due for 2h 10m)

  New tenders: t-2026-0128, t-2026-0129, t-2026-0130, …  → run tender-qualifier score
  Quarantined: 1 message (unrecognized MERX template) → documents/inbox/quarantine/
```

Always end by suggesting the follow-on: `tender-qualifier score` for new/changed tenders; flag amendments for `tender-monitor`.

## What this skill must never do

Bypass CAPTCHAs or bot protection; authenticate to any portal; poll faster than the ledger allows; write facility files outside the memory layer; silently discard an unparseable notification; submit anything.
