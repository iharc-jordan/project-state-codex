# Tender — SCHEMA.md Extension

Append this section to the enabling facility's `project-state/SCHEMA.md`. It follows the
substrate's schema-extension mechanism: the canonical schema lives *in the project*, and the
`project-state` memory layer validates against it.

---

## Tender package entity kinds

The tender package adds two entity kinds and one append-only event stream.

### Directory layout additions

```text
project-state/
├── manifest.yaml                # + capabilities.tender block (see templates/tender/manifest-capability-block.yaml)
├── state/tender.json  # tender counters + tender_connectors (per-capability state file)
├── tenders/
│   ├── t-<year>-<seq>.yaml      # kind: tender (file-per-entity — never a fused tenders.yaml)
│   ├── profiles/<slug>.yaml     # kind: tender-profile
│   └── events.ndjson            # tender source events (append-only)
├── decisions/                   # bid/no-bid decisions use the EXISTING decision kind
├── documents/
│   ├── inbox/                   # retrieved tender packages land here
│   │   └── quarantine/          # unrecognized notification templates
│   └── index.yaml               # + tender doc types and tender_id links
└── logs/activity.ndjson         # all tender.* events
```

### `kind: tender`

Common frontmatter (`id`, `kind`, `created`, `created_by`, `last_modified`, `last_modified_by`, `phase`) plus:

| Field | Type | Notes |
| --- | --- | --- |
| `title`, `normalized_title` | string | normalized = lowercase, collapsed whitespace, punctuation stripped |
| `solicitation_number` | string \| null | as published |
| `buyer` | map | `name`, `normalized_name`, `type`, `jurisdiction`, `wiki_page` |
| `procurement` | map | `type` (RFP/RFQ/ITT/RFI/SOI/NPP), `status`, `contract_duration`, `estimated_value`, `currency` |
| `dates` | map | `published_at`, `questions_due_at`, `mandatory_meeting_at`, `closing_at`, `original_timezone` — ISO-8601 with original offset |
| `location` | map | `regions[]`, `delivery_modes[]`, `travel_required` |
| `summary` | map | `source_synopsis`, `generated_summary`, `scope_summary` |
| `matching` | map | `profiles[]`, `matched_terms[]`, `relevance_score` 0–100, `strategic_value_score`, `urgency_score`, `evidence[]` (`passage`, `source`) |
| `qualification` | map | `status`: `preliminary` \| `needs_review` \| `qualified` \| `disqualified`; `mandatory_requirements[]`, `possible_disqualifiers[]`, `missing_information[]`, `human_approved` (bool — only a person may set true) |
| `documents` | map | `available`, `retrieved`, `login_required`, `ids[]` (documents/index.yaml entries) |
| `sources[]` | list | per portal: `portal`, `source_id`, `role` (`discovery`/`documents`/`submission`), `discovery_url`, `document_url`, `submission_url`, `first_seen_at`, `last_checked_at`, `message_id` (email-discovered) |
| `workflow` | map | `status` (see lifecycle), `owner`, `decision_id`, `next_action`, `dismissal_reason` |
| `monitoring` | map | `followed`, `watch_feed_url`, `last_change_at`, `amendment_count` |

**Workflow lifecycle** (`workflow.status`):
`discovered → preliminary_match → documents_required → under_review → qualified → bid_no_bid_pending → { pursue | watch | partner_opportunity | dismissed } → preparing_response → submitted → { awarded | unsuccessful } | cancelled | closed`

Transitions are validated by `tender-pipeline`; every transition logs `tender.status.changed`.

### `kind: tender-profile`

Common frontmatter plus: `name`, `enabled`, `include` (`exact_phrases[]`, `concepts[]`, `commodity_codes[]`), `exclude.exact_phrases[]`, `buyers.preferred_types[]`, `geography` (`preferred[]`, `excluded[]`), `commercial` (`minimum_days_remaining`, `maximum_estimated_bonding`, `allow_document_fees`), `delivery.accepted[]`, `weights` (must sum to 100). See `templates/tender-profile-template.yaml`.

### `tenders/events.ndjson` — source event lines

One JSON object per line, append-only, never rewritten:

```json
{"ts":"…","actor":"tender-monitor","event":"tender.deadline.changed","id":"t-2026-0041","source":"CanadaBuys","previous_value":"…","new_value":"…","evidence_url":"…","parser_version":"canadabuys-feed/1.0","notification_sent":true}
```

Required: `ts`, `actor`, `event`, `id`, `source`, `parser_version`. `previous_value`/`new_value` required for change events. Raw payload reference (`raw_ref`) required when a raw capture exists.

### `state/tender.json` (per-capability state file)

```json
{
  "counters": {"tenders": 0, "tender_profiles": 0, "tender_events": 0},
  "tender_connectors": {
    "<connector-id>": {
      "cursor": null, "etag": null, "gmail_cursor": null, "seen_ids_hash": null,
      "health": "unknown", "last_success": null, "last_new_record": null,
      "consecutive_failures": 0, "paused": false
    }
  }
}
```

Connector ids: `canadabuys-feed`, `canadabuys-email`, `merx-email`, `sasktenders-email`, `sasktenders-listing`, `gem-listing`, `bidsandtenders-email`, `bidsandtenders-listing`.
Health states: `healthy | delayed | parsing_error | authentication_required | access_restricted | paused | unknown`.

### `documents/index.yaml` additions

Tender documents extend the existing document record with: `tender_id`, `version` (int), `hash` (sha256), `supersedes` (document id | null), `access_classification` (`public` | `account-restricted` | `confidential` | `internal-analysis`), and doc types `tender-notice`, `tender-addendum`, `tender-qa`, `tender-submission`.

Documents with `access_classification` other than `public` are excluded from every publishing surface (blog, website, external comms) by classification check.

### Canonical events (lowercase noun.verb)

| Event | Emitted by | Bumps counter |
| --- | --- | --- |
| `tender.harvest.completed` | tender-harvester | — |
| `tender.discovered` | tender-harvester | `counters.tenders` |
| `tender.scored` | tender-qualifier | — |
| `tender.qualified` | tender-qualifier | — |
| `tender.disqualified` | tender-qualifier | — |
| `tender.amended` | tender-monitor | `counters.tender_events` |
| `tender.deadline.changed` | tender-monitor | `counters.tender_events` |
| `tender.document.revised` | tender-monitor | `counters.tender_events` |
| `tender.cancelled` | tender-monitor | `counters.tender_events` |
| `tender.awarded` | tender-monitor | `counters.tender_events` |
| `tender.status.changed` | tender-pipeline | — |
| `tender.merged` | tender-qualifier | — |
| `tender.dismissed` | tender-pipeline | — |
| `tender.handoff.completed` | tender-pipeline | — |
| `tender.profile.created` / `tender.profile.updated` | project-state | `counters.tender_profiles` on create |

Bid/no-bid reuses `decision.opened` / `decision.recorded`. Pursuit deadlines reuse `milestone.*`.

### Write discipline

All writes go through the `project-state` memory layer: lock → read → staleness check → write → release → activity log → counters. `tender-*` skills never write facility files directly.
