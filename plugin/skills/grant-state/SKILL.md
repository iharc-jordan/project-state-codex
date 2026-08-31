---
name: grant-state
description: "Canonical gateway for an existing grant-state facility, or an explicit request to inspect or validate one. Own pre-award manifest, narratives, gates, letters, budget lines, source references, findings, program, award, and ledger mutation through its write protocol. Do not activate grant workflows merely because a repository mentions a grant."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Grant State

## Purpose

The memory layer for grant-submission facilities. Every `grant-*` skill reads and writes `grant-state/` through this skill. Mirrors the role of `project-state` for the pre-award phase.

A grant-submission facility (`grant-state/`) is separate from the execution facility (`project-state/`). It exists from the moment a team decides to pursue a program until award (or rejection). On award, `grant-scaffolder` freezes it and spawns a sibling `project-state/`.

## Finding `grant-state/`

Walk up from the current working directory looking for `grant-state/manifest.yaml`. That directory is the submission root. If none found, report: "No grant-state/ found. Run grant-scaffolder to initialize a submission facility."

## Facility layout

```
grant-state/
├── manifest.yaml          # program, PI, org, consortium, deadline, phase
├── state.json             # current_phase, gate counts, section counts, counters
├── sections/              # narrative sections (one YAML per section)
├── gates/                 # compliance gate records (one YAML per gate)
├── letters/               # support, partnership, TTO, ethics letters
├── budget/                # budget lines and cost-share records
├── sources/               # ingested program guides and reference docs
├── citations/             # factual claims with source tracebacks
├── findings/              # internal review findings (red-team results)
├── program-record.yaml    # program metadata, eligibility, requirements
├── award-record.yaml      # populated on award (or rejection)
├── documents/
│   ├── inbox/             # raw drop zone (grant-ingestor reads here)
│   └── working/
└── logs/
    ├── activity.ndjson    # append-only event log
    └── decisions.ndjson
```

## Schema

### `manifest.yaml` fields
```yaml
id: <slug>
kind: grant-submission
program: <program id>           # e.g. nserc-alliance, irap, pic-pcais
playbook: <playbook id>         # matched by grant-scaffolder
deadline: <ISO date | null>     # null for continuous-intake programs
phase: prospect | pre-submission | internal-review | submitted | awarded | rejected
lead_organization: <org name>
pi:
  name: <name>
  email: <email>
consortium_shape: single-applicant | single-pi-with-partners | multi-party-consortium
geography: [<province>, ...]
indigenous_engagement: yes | no | unsure
surfaces: { slack: bool, gmail: bool, calendar: bool }
created: <ISO-8601 UTC>
created_by: <email>
last_modified: <ISO-8601 UTC>
last_modified_by: <email>
```

### `sections/` — narrative section files
```yaml
id: <section-id>
kind: narrative-section
title: <section title>
required: true | false
status: draft | in-progress | complete | red-flagged
word_count: <int>
word_limit: <int | null>
content: |
  <current draft text>
findings: [<finding-id>, ...]   # open findings against this section
last_modified: <ISO-8601 UTC>
last_modified_by: <email>
```

### `gates/` — compliance gate records
```yaml
id: <gate-id>
kind: compliance-gate
gate_type: ocap | gba-plus | bilingual | tto-routing | stacking | ip-declaration |
           indigenous-engagement | environmental | cost-share | ethics-reb |
           biosafety | data-sovereignty
applicability: required | recommended | not-applicable
status: open | cleared | waived | deferred
evidence: <path to evidence doc or URL>
cleared_by: <email | null>
cleared_date: <ISO date | null>
notes: |
  <compliance notes>
last_modified: <ISO-8601 UTC>
```

### `findings/` — internal review findings
```yaml
id: <finding-id>
kind: internal-review-finding
severity: blocker | major | minor | observation
section: <section-id | null>
gate: <gate-id | null>
description: <finding text>
recommendation: <suggested fix>
status: open | resolved | accepted-risk
raised_by: <name>
raised_date: <ISO date>
resolved_date: <ISO date | null>
```

## Operations

### Read operations (no locking needed)
- **Get manifest.** Parse `manifest.yaml`.
- **Get state.** Parse `state.json`.
- **List sections.** Return all `sections/*.yaml` with status summary.
- **Get gate matrix.** Return all `gates/*.yaml` grouped by applicability and status.
- **List findings.** Return all `findings/*.yaml` filtered by severity/status.
- **Tail activity log.** Return last n lines of `logs/activity.ndjson`.
- **Validate.** Walk all YAML/JSON; check required frontmatter; report mismatches.

### Write operations (with locking + logging)
Same protocol as `project-state`: acquire `<target>.lock` (TTL 300s), read current, check staleness, apply change, write, release lock, append to `logs/activity.ndjson`.

### Canonical write events
| Operation | Event name |
|---|---|
| Scaffold facility | `grant.scaffolded` |
| Update section | `section.updated` |
| Clear gate | `gate.cleared` |
| Add finding | `finding.raised` |
| Resolve finding | `finding.resolved` |
| Record award | `award.recorded` |
| Record rejection | `rejection.recorded` |
| Freeze facility | `facility.frozen` |
| Spawn project-state | `project-state.spawned` |

## Phases

| Phase | Meaning |
|---|---|
| `prospect` | Team evaluating whether to apply |
| `pre-submission` | Actively drafting the submission |
| `internal-review` | Red-team / institutional review underway |
| `submitted` | Package sent to funder |
| `awarded` | Award confirmed; facility frozen |
| `rejected` | Submission unsuccessful; optional lessons capture |

## Reads
- `grant-state/manifest.yaml`, `state.json`, `sections/`, `gates/`, `findings/`, `logs/`

## Writes
- All of the above via the write protocol
- Never writes to `project-state/` — that is spawned by `grant-scaffolder` on award

## Called by
- `grant-scaffolder` — for all facility initialization and award handoff
- `grant-ingestor` — to register sources, update sections, update gates
- `project-orchestrator` — may read grant-state summary for morning briefing if a submission is active
