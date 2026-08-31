---
name: project-state
description: "The shared memory of a grant-funded project. Read, write, or validate project state — manifest, current phase, milestones, decisions, risks, changes, people, documents, activity log. Trigger on 'what's the project state', 'record a decision', 'log this change', 'update milestone M03', 'who is on the steering committee', 'what phase are we in', 'append to activity log', 'check state health', 'validate the manifest', or any request that reads or writes `project-state/`. Also trigger automatically whenever another project-* skill (phase-gate, document-curator, milestone-manager, status-reporter, notifier, sc-meeting, claim-prep, change-register, orchestrator) needs to read or write state — they route through this one. Also owns the capability lifecycle — enable, disable, and validate a capability plugin (sred, tender-intelligence) for this project: 'enable SR&ED', 'turn on the sred capability', 'is SR&ED enabled', 'disable the capability'. Works for any `project-state/` found by walking up from cwd."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project State — the memory layer

## Purpose

Every `project-*` skill depends on this one. `project-state` is the only gateway
for canonical entity and activity-ledger mutation; every other skill expresses
intent ("create milestone", "transition phase") and this skill enforces schema,
concurrency, and logging. A generator may write its owned derived report or
automation artifact, then routes canonical pointer, counter, outbox, and activity
updates back through this skill.

Without this skill, state edits drift, writers can clobber each other on a shared
drive, and the activity log stops being trustworthy. Lockfiles protect writers
on the same shared filesystem or server-backed substrate only; separate Git
clones coordinate through Git and explicit conflict resolution.

## Finding `project-state/`

Walk up from the current working directory until a `project-state/manifest.yaml` is found. That directory is the project root. If none is found:
- If the user asked a read-only question, say so and stop.
- If the operator explicitly asked to initialize, apply the adapter's
  task/epic/program routing and hand off to `project-scaffolder` or
  `project-onboarding`. Ordinary code work is not an implicit initialization
  request.

```bash
# Locate state (pseudocode)
dir = cwd
while dir != "/":
  if exists(dir + "/project-state/manifest.yaml"): return dir + "/project-state"
  dir = parent(dir)
raise "No project-state/ found walking up from " + cwd
```

`$PROJECT_STATE_DIR`, when set, short-circuits the walk for explicitly configured runners.

## Substrate binding

The public package fully supports the local file binding described above. The
private remote deposit backend and its authentication/protocol specification are
not bundled, so environment variables alone are not enough to activate it.

Use a deposit binding only when an installed internal adapter supplies the
protocol and the operator explicitly configures and authorizes that endpoint.
Then preserve the existing invariant: one project has one canonical substrate,
an unreachable remote never falls back to local writes, and server-side locking,
deduplication, cursor advance, identity, and activity logging remain atomic.
Otherwise report the deposit binding as unsupported and use the file binding
without prompting for cloud setup.

The harvester's persistence interface remains `read-context`,
`seen?`/`mark-seen`, `write-doc`, `advance-cursor`, and
`append-activity`. In the public adapter those verbs resolve to the local
Project State files and canonical write gateway.

## Schema

The canonical schema lives in `project-state/SCHEMA.md` *in the project itself*. This skill validates against that file; it does not carry its own schema because different projects may extend the schema for their specific needs.

Every entity YAML has common frontmatter:
- `id` (matches filename minus extension)
- `kind` (`milestone` | `objective` | `kpi` | `decision` | `risk` | `change-log` | `change-order` | `person` | `publication` | `ip-disclosure` | `sc-meeting` | `quarterly-claim` | `wiki-page`)
- `created`, `created_by`, `last_modified`, `last_modified_by` (ISO-8601 UTC)
- `phase` (phase this entity was created in)

**Wiki pages are the one exception to YAML-only:** `wiki/<slug>.md` is Markdown with a YAML frontmatter block (the body is prose with inline `[[links]]`). The validator accepts `.md` under `wiki/` and treats the frontmatter block as the entity record (common fields + `title`, `aliases`, `tags`, `parent`, `links`, `visibility`, `confidence`). The derived `wiki/.index/` is non-canonical and rebuildable (like `tracking/*.xlsx`) — excluded from validation.

Before every write, verify the document has all common frontmatter. Refuse to write if `id`, `kind`, or timestamps are missing.

## Operations

### Read operations (no locking needed)

**Get manifest.** Return parsed `manifest.yaml`.

**Get state.** Return parsed `state.json`.

**Get current phase.** Read `manifest.yaml:phases.current_phase` as authority,
compare `state.json:current_phase`, and read `phases/<phase>/manifest.yaml`.
Report a disagreement; do not choose a phase from milestone status.

**Get entity.** Input: `kind` + `id`. Locate file by filename convention (see SCHEMA.md). Return parsed YAML.

**List entities.** Input: `kind`, optional filters (status, owner, phase),
`limit=50` (maximum 200), `cursor`, and `detail=false`. Return bounded summary
fields plus a stable next cursor. Read and return full YAML only for explicit
detail mode or a named entity.

**Read activity.** Input: optional `since`, `limit=50` (maximum 200), and
`cursor`. Return parsed canonical fields plus accepted legacy aliases. A cursor
is the last returned timestamp plus deterministic line position; it is a read
token, not new canonical state.

**Count entities.** Return counters from `state.json`.

**Validate/reconcile.** Walk every YAML/JSON in `project-state/`; confirm it
parses **under a duplicate-key-strict loader** and has required frontmatter.
Mechanically compare unique-ID counters, maximum valid event timestamp,
manifest/transition/state phase, manifest/tasks timezone, lifecycle/increments,
closeout consistency, deterministic event IDs, and material health conditions.
Dry-run and report proposed repairs by default; never auto-fix. An explicit
apply request performs ordinary canonical writes one at a time. Full check list
under "Validate the state" below.

### Canonical write operations (with locking + logging)

For every canonical entity or ledger write:

1. **Apply materiality.** If the fact is task-local and the operator did not
   explicitly override with a reason, return where it belongs and make no
   Project State write.
2. **Find lockfile.** Check `<target>.lock`. If it exists and its `acquired + ttl_seconds` is in the future, wait (up to 30 s) or abort.
3. **Acquire lock.** Write `<target>.lock` = `{actor, acquired, ttl_seconds: 300}`.
4. **Read current state** of the target if it exists.
5. **Check staleness.** If the caller passed a `base_last_modified` and the current file's `last_modified` is newer, return a CONFLICT to the caller. Do not overwrite.
6. **Compute deterministic identity.** Follow `CODEX.md`: retain entity IDs
   where required and otherwise use the existing `id` field for the event
   identity. Search the relevant target/log before writing.
7. **Suppress exact repeats.** If the target already has the normalized result
   and the matching identity exists, return that record without touching the
   target, counters, output fan-out, or `last_activity`.
8. **Apply the change.** Update `last_modified`, `last_modified_by`, fields under change. Preserve all other fields.
9. **Write the file.**
10. **Release lock.** Delete `<target>.lock`.
11. **Append to activity log.** One NDJSON line: `ts, actor, event, id, summary`. `summary` is
   canonical; `detail` and `note` are read-only aliases a reader must accept, in that order, and a
   line whose structured fields say everything needs none of the three. Never
   rewrite existing lines to match. The event table and validation rules in this
   skill plus the facility's checked-in `project-state/SCHEMA.md` are authoritative.
12. **Update state.json projections** only when the operation requires it (also
    under the lock): counters are unique canonical IDs and `last_activity` is
    the maximum valid canonical `ts`. Phase remains the manifest/transition
    authority mirrored into state; health follows only material conditions or
    a reasoned governed override.

One durable fact change produces one canonical entity update, its required
counter/pointer change, and one matching activity event. Do not duplicate the
fact in a second entity or ledger event. Store stable external ticket/document
references rather than copying full external records unless an active pack
requires a managed copy. Reports remain derived views; record a newly discovered
fact here before a report presents it.

### Canonical write events

| Operation                           | Event name                  | Also bumps counter     |
| ----------------------------------- | --------------------------- | ---------------------- |
| Create milestone                    | `milestone.created`         | `counters.milestones`  |
| Update milestone                    | `milestone.updated`         | —                      |
| Complete milestone                  | `milestone.completed`       | —                      |
| Create objective                    | `objective.created`         | `counters.objectives`  |
| Update objective                    | `objective.updated`         | —                      |
| Create KPI                          | `kpi.created`               | `counters.kpis`        |
| Update KPI                          | `kpi.updated`               | —                      |
| Add a dated KPI reading             | `kpi.reading.added`         | —                      |
| Open a decision (owed, not yet made) | `decision.opened`          | `counters.decisions`   |
| Record / resolve decision           | `decision.recorded`         | `counters.decisions` on new |
| Propose a stop                      | `stop.proposed`             | `counters.stops`       |
| Confirm / reject stop               | `stop.stopped` / `stop.rejected` | —                 |
| Log change (material or operator-overridden) | `change.logged`      | `counters.change_log_entries` |
| Draft change order                  | `change-order.drafted`      | `counters.change_orders` |
| Submit change order                 | `change-order.submitted`    | —                      |
| Approve change order                | `change-order.approved`     | —                      |
| Open risk                           | `risk.opened`               | `counters.risks`       |
| Close/materialize risk              | `risk.closed` / `risk.materialized` | —              |
| Register document                   | `document.registered`       | —                      |
| Promote to source-of-truth          | `document.sot.promoted`     | —                      |
| Schedule SC meeting                 | `sc.meeting.scheduled`      | `counters.sc_meetings` |
| Hold SC meeting / distribute minutes | `sc.meeting.held` / `sc.minutes.distributed` | —    |
| Draft claim / submit / paid         | `claim.drafted` / `claim.submitted` / `claim.paid` | `counters.quarterly_claims` on draft |
| Phase transition                    | `phase.transition`          | —                      |
| Select the phase preset             | `preset.declared`           | —                      |
| Warn that the log lags the repo     | `activity.lag.warned`       | —                      |
| Declare the lifecycle               | `lifecycle.declared`        | —                      |
| Convert terminal → continuous       | `lifecycle.converted`       | —                      |
| Warn that work arrived after closeout | `lifecycle.mismatch.warned` | —                    |
| Open an increment                   | `increment.opened`          | `counters.increments`  |
| Close an increment                  | `increment.closed`          | —                      |
| Cancel an increment                 | `increment.cancelled`       | —                      |
| IP disclosure                       | `ip.disclosed`              | `counters.ip_disclosures` |
| Publication proposed / approved     | `publication.proposed` / `publication.approved` | `counters.publications` on proposed |
| Generate report                     | `report.generated`          | —                      |
| Health assessed                     | `health.assessed`           | —                      |
| Create wiki page                    | `wiki.page.created`         | `counters.wiki_pages`  |
| Update wiki page                    | `wiki.page.updated`         | —                      |
| Delete wiki page                    | `wiki.page.deleted`         | —                      |
| Publish wiki page (after review)    | `wiki.page.published`       | —                      |
| Rebuild the derived wiki index      | `wiki.graph.rebuilt`        | —                      |
| Broken entity reference detected    | `wiki.link.broken`          | —                      |
| Enable a capability                 | `capability.enabled`        | —                      |
| Disable a capability                | `capability.disabled`       | —                      |

Event names are lowercase, dot-separated, noun.verb. A capability may register **additional**
event names under its own namespace prefix (`sred.*`, `tender.*`) — see "Capability lifecycle" below.
Those are owned by the capability's `schema/events.yaml`, not by this table.

## Capability lifecycle

A **capability** is a plugin that extends the substrate with new entity kinds, its own event
vocabulary, its own validator, and a bundled default pack. `install` makes a capability *available*
(it lands at the plugin or installed-adapter layer). **`enable` makes it active for one project**, and that is
a memory-layer verb — it writes the manifest, so it routes through here like every other write.

Capabilities ship under `capabilities/<id>/` with a
`plugin.yaml` declaring `namespace.prefix`, `payload.schema`, `payload.validator`, and
`payload.packs.bundled`, plus a `templates/manifest-block.yaml` describing the config the block
requires.

### Discover

**List capabilities.** Read every `capabilities/*/plugin.yaml` available to this install. Return
`{id, version, description, bundled_pack, required_config}` where `required_config` is the set of
keys in the capability's `templates/manifest-block.yaml` whose seeded value is `REQUIRED`.

**Get capability status.** Read `manifest.yaml → capabilities.<id>`. Return `not-installed` (no
plugin.yaml), `available` (plugin present, no manifest block), `enabled`, or `disabled`.

### Enable `<capability-id>`

A write operation — take the `manifest.yaml` lock for the whole sequence.

1. **Resolve the template.** Read `capabilities/<id>/plugin.yaml` and
   `capabilities/<id>/templates/manifest-block.yaml`.
2. **Refuse on missing required config.** Any key the template marks `REQUIRED` must be supplied by
   the caller. Do not invent a value, do not substitute a plausible default, and do not write a
   partial block. Return the list of missing keys so the caller can ask for them. *(For `sred`,
   `fiscal_year_end` is REQUIRED — every deadline in the capability is computed from it, so a guessed
   value produces a confidently wrong filing date. See SRED-CAPABILITY-SPEC §5.)*
3. **Refuse on version incompatibility.** `plugin.yaml → compatibility.substrate` must be satisfied by
   the running substrate version.
4. **Write the manifest block** under `capabilities.<id>`, stamping `enabled: true` and
   `version:` = the plugin version at enable time (the validator checks drift later).
5. **Scaffold the schema directories** named in the capability's `schema/entities.yaml`, each with a
   `.gitkeep`. Enabling over an existing directory tree **adopts** it — never overwrite, never clear.
6. **Create `state/<id>.json`** from the capability's runtime-state shape. Any dated fields the
   capability computes at enable time (deadlines, cursors, current-period entries) are computed now,
   from the config supplied in step 2.
7. **Register the schema extension and event vocabulary** — `schema/entities.yaml` and
   `schema/events.yaml` — so validation and the write path accept the new kinds and event names.
8. **Seed the reporting matrix** from the bundled pack's `reporting-matrix-defaults.yaml`, merging
   into `reporting-matrix.yaml`. Existing entries with the same id are left alone.
9. **Arm the schedule.** Hand off to `project-automator update` so the seeded entries compile into
   `automation/tasks.yaml` immediately. A capability that is enabled but unarmed is the failure
   mode this step exists to prevent.
10. **Log `capability.enabled`** with `{id, version, pack}`.

Report back what was written: the block, the directories created, the computed dates, the matrix
entries seeded, and the next scheduled task. The caller shows the operator a real date, not a promise.

### Disable `<capability-id>`

Flip `enabled: false`. **Data stays** — files are the record, and removing them is a separate,
curated, logged operation that is never part of disable. Skills refuse writes for a disabled
capability; views unmount; seeded matrix entries are **marked disabled, not deleted**.

Before flipping, check the capability's runtime state for open obligations. If any exist, **show the
operator the specific dates and require explicit confirmation** — disabling must never silently walk
away from a live deadline. (For `sred`: any fiscal year whose `claim_status` is not in
`{filed, waived, forfeited}`.)

Log `capability.disabled`.

### Validate

The full validation pass is the core validator **composed with** every enabled capability's validator
(`payload.validator`). Additionally check, for each enabled capability:

- the manifest block still carries every `REQUIRED` key
- `capabilities.<id>.version` matches the installed plugin version (report drift; do not auto-bump)
- `state/<id>.json` exists and parses
- every matrix entry naming a profile from the capability's bundled pack resolves

### Per-entry profile resolution

A generator invoked from a matrix entry loads the profile named on that entry
(`<pack-id>.<profile-slug>`), resolved from **any installed pack** — the active project pack *or* a
pack bundled with an enabled capability. The `active_pack` chain remains the fallback for
conversational invocations that arrive without a matrix entry. An entry naming a profile from a pack
that is neither active nor capability-bundled is a validation error.

## The post-closeout diagnostic

A facility can detect for itself that the terminal phase model has stopped holding, and the signal is
unambiguous: **work is added after closeout.** A new milestone, a new workload, or a reopened gate on a
facility at or past its closeout-equivalent phase is the moment the terminal assumption broke.

Emit a warning when **all** of these hold:

1. `current_phase` is at or past the active preset's closeout-equivalent phase (the last phase with a
   `gate_out`, or a phase whose id or label contains `closeout` / `wrap` / `maintain` / `maintained`).
2. `lifecycle` is absent or `terminal`.
3. The write in hand creates a milestone, creates a workload, or sets a `gate_out.checklist[].done`
   back to `false`.

```
This facility is at 05-closeout and just gained a milestone. The terminal phase model assumes no
further work, so re-entering an earlier phase would overwrite that phase's gate record — including any
criterion closed unmet.

If this project continues, declare it:  project-phase-gate set-lifecycle continuous
Nothing about conversion is destructive; preserve prior phase and increment evidence.
```

**Warn, never refuse.** A facility legitimately gains a milestone during closeout — a late deliverable
is not a lifecycle mismatch, and blocking the write would make the diagnostic worse than the defect.
The warning is a prompt, and its whole value is being asked at the moment the operator can still answer
it cheaply.

Rate-limited to once per facility per day, by reading back the last `lifecycle.mismatch.warned` entry in
`logs/activity.ndjson` — which is also what makes the warning auditable rather than transient.

This check is worth having whatever happens to the rest of the lifecycle work: it is independent of the
increment layer, costs almost nothing, and would have surfaced the whole problem months earlier on the
facility that eventually found it the hard way.

## Increments

Present only when `lifecycle: continuous`. `project-phase-gate` owns the verbs — `open_increment`,
`close_increment`, `cancel_increment`, `convert_to_continuous` — and the writes land here. Entity shape
is in `SCHEMA.md`; ids allocate from `state.json:counters.increments` under the advisory lock, like every
other kind.

Two rules this skill enforces regardless of what the caller asks:

- **A closed increment is frozen.** Refuse any write to `increments/INC-*/` where the increment's
  `status` is `closed` or `cancelled` — including its `phases/` and `gates.json`. Corrections are new
  records, per the append-only discipline below. This refusal is the entire reason the increment layer
  exists; without it the design has no teeth.
- **`closed_what` cannot be empty.** Refuse a close whose `closed_what` is missing, blank, or
  whitespace. It has no default and cannot be generated — only the operator knows what a closure closed.

## Concurrency discipline (from CONCURRENCY.md)

- **File-per-entity** — never fuse `milestones.yaml` or `decisions.yaml`. Each entity is its own file.
- **Advisory lockfiles** with 5-minute TTL on `manifest.yaml`, `state.json`, and `tracking/*.xlsx`.
- **Append-only logs** — never rewrite `logs/*.ndjson`; correct with new entries.
- **Deterministic filenames** — two agents creating the same entity produce the same filename.

## What this skill does NOT do

- **Does not make project decisions.** Doesn't decide if a change is material (that's `project-change-register`) or if a phase gate is clearable (that's `project-phase-gate`).
- **Does not generate reports.** Just returns data (that's `project-status-reporter`).
- **Does not send notifications.** Just writes activity events (that's `project-notifier`).
- **Does not classify documents.** Just reads/writes `documents/index.yaml` (that's `project-document-curator`).
- **Does not run a capability's own work.** `enable` wires a capability in; capturing SR&ED
  uncertainties or screening tenders belongs to that capability's skills. This skill owns the
  manifest block, the directories, the runtime-state file, and the log line — nothing past that.

## Examples

### "What phase are we in?"
Read `manifest.yaml:phases.current_phase`, compare its `state.json` mirror and
successful transition/lifecycle history, then read the authoritative phase
manifest. Return the phase label, gate-out counts, and any disagreement.

### "Update M03 percent complete to 35%"
1. Load `milestones/M03-cdi-pilot-fermentation-trials.yaml`.
2. Set `percent_complete: 35`. Update `last_modified`. Keep `technical_progress` unchanged (caller didn't provide it).
3. Acquire lock, write, release, log `milestone.updated` with `id: M03-...`.
4. Return the updated entity.

### "Track a goal / KPI" (objectives + key results — the outcome layer)
Objectives and KPIs are file-per-entity like everything else; `project-goal-tracker` is the
verb skill, but the writes land here.
1. **Objective** — write `objectives/O<NN>-<slug>.yaml` (next `NN`) with `kind: objective`, `title`, `horizon`, `category`, `status`, optional `narrative`/`key_results`/`milestones`/`confidence`/`target_date`. Log `objective.created`, bump `counters.objectives`.
2. **KPI** — write `kpis/KPI-<NN>-<slug>.yaml` with `kind: kpi`, `metric`, `unit`, `baseline`, `target`, `current`, `direction` (up|down), `cadence`, optional `delivers_to` (objective id). Log `kpi.created`, bump `counters.kpis`.
3. **Reading** — append `{date, value, note?}` to the KPI's `history` (one entry per date — replace same-day), set `current` and `as_of`. Log `kpi.reading.added`. Never rewrite prior readings; corrections are a new same-date entry.
4. Attainment (direction-aware `baseline→target`) and trend (last two readings) are **computed on read** — never store them.

### "Record a decision: engage ACME as subcontractor for M03"
1. Receive `decision.recorded` payload with id, date, title, context, options, decision, rationale, material_change.
2. Validate required fields. If `material_change: true`, cross-reference `change_order_ref` and warn if absent.
3. Write `decisions/<date>-<slug>.yaml`. Append to `logs/activity.ndjson` and `logs/decisions.ndjson`.
4. Bump `state.json:counters.decisions`.
5. If `material_change: true`, remind the caller that `project-change-register` should draft the CO.

### "Open a decision" (a decision that's owed but not yet made)
An open decision is a normal decision record in the `open` state — same `decisions/` directory, no new entity type.
1. Receive a `decision.opened` intent with `title`, `question` (required), and optional `options`, `owner`, `needed_by`, `blocks`, `context`.
2. Write `decisions/<date>-<slug>.yaml` with `kind: decision`, `status: open`, the `question`, `owner`, `needed_by`, `blocks` (list), `options` (list), plus standard frontmatter. Leave `decision`/`rationale` empty until resolved.
3. Acquire lock, write, release, log `decision.opened` with `id`. Bump `counters.decisions`.
4. Resolving it later is a `decision.recorded` update on the same file: set `status: decided`, fill `decision`/`rationale`, keep the `id`. (Existing decisions with no `status` are treated as `decided`.)

### "Propose a stop" (work / practice / low-value report to retire)
1. Receive a `stop.proposed` intent with `title`, `target` (what to stop), `why` (all required), and optional `evidence`, `in_favor_of`, `owner`.
2. Write `stops/STOP-<NN>-<slug>.yaml` (next `NN` like risks) with `kind: stop`, `status: proposed`, `target`, `why`, `evidence` (list), `in_favor_of`, `owner`, plus standard frontmatter.
3. Acquire lock, write, release, log `stop.proposed` with `id`. Bump `counters.stops` (create the counter if absent).
4. A later confirm/reject sets `status: stopped` or `status: rejected` and logs `stop.stopped` / `stop.rejected`. The skill never decides *whether* to stop — it only records the proposal and the operator's call.

### "Show me recent activity"
Read the last 50 events by default, or honor `since`/`limit`/`cursor`.
Pretty-print timestamp, actor, event, id, and canonical/legacy summary. Return a
cursor when more matching lines exist; do not deep-scan the full history unless
asked.

### "Validate the state"

Walk every YAML/JSON, parse, check frontmatter completeness. Report:

- Files that don't parse
- **Duplicate keys within a file** — see below
- Entities missing `id`, `kind`, or timestamps
- Filename-id mismatches
- **Duplicate ids across files of the same kind** — two milestones both claiming `M10` is the
  across-file form of the same collision, and it shows up as `counters.milestones` (file count)
  disagreeing with `health.milestones_total` (unique ids)
- Orphan references (e.g., a decision pointing to a nonexistent change-order)
- Stale lockfiles (older than TTL)
- Phase manifests against the phase-manifest schema in `SCHEMA.md`
- `state.json` counters against unique canonical entity IDs
- `state.json:last_activity` against the maximum valid event `ts`
- `manifest.yaml:phases.current_phase`, successful transition/lifecycle events,
  and `state.json:current_phase` for disagreement (never infer phase from
  milestone completion)
- `manifest.yaml:automation.timezone` against `automation/tasks.yaml:timezone`;
  a null/missing manifest value or a mismatch is a finding, never a default
- duplicate deterministic IDs for new events and exact repeated
  validation/release/report evidence; preserve legacy lines
- health against material delivery, reporting, compliance, security, and
  production-path conditions; development-only advisories remain notes
- Lifecycle consistency — see below

Return a bounded summary and proposed repairs. Dry-run is the default; apply
only after an explicit operator request.

#### Duplicate keys must fail the parse

**Load every YAML with a duplicate-key-strict loader.** A default `yaml.safe_load` accepts a repeated
key at any mapping level and silently keeps the last one — so the file parses, the earlier value is
gone, and nothing ever reports it. This is not hypothetical: a phase manifest carried a duplicate
`ended:` key and the phase read as undated while the file plainly stated a date (`FB-005`).

```python
import yaml


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys instead of silently keeping the last."""


def _no_duplicate_keys(loader, node, deep=False):
    seen = {}
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None,
                f"duplicate key {key!r} (first seen on line {seen[key]})",
                key_node.start_mark,
            )
        seen[key] = key_node.start_mark.line + 1
    return yaml.constructor.SafeConstructor.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)
```

Report duplicates as **errors**, naming the file and both line numbers. This applies to *every* YAML
in the facility, not only phase manifests — a duplicate key in a milestone or a decision loses data
exactly as quietly. JSON gets the equivalent treatment via `object_pairs_hook`.

**Never auto-fix a duplicate key.** Which value the author meant is unrecoverable from the file. Report
and stop.

#### Lifecycle consistency

- `lifecycle`, where present, is `terminal` or `continuous`. **Absence is valid and is never
  reported** — not as an error, not as a warning, not as a suggestion. A facility that never declares
  a lifecycle is a supported facility, permanently.
- `manifest.yaml:phases.lifecycle` and `state.json:lifecycle` agree, where both are present.
- `lifecycle: continuous` requires the active preset's terminal phase to declare `cycles_back_to`,
  naming a phase id in the same preset. Declaring `continuous` against a terminal-only preset
  (`grant-default`) is an **error**, not a warning.
- `current_increment`, where present, names an existing increment whose `status` is `open`.
- A continuous facility has a meaningful current or closed increment. None is a
  reconciliation finding, not permission to invent or backfill one.
- Every increment at `status: closed` or `cancelled` has `closed`, `phase_at_close`, `closed_what`, a
  frozen `phases/`, and a `gates.json`.
- `increment` references on milestones name existing increments.
- `cycles_back_to` on any phase manifest names a phase id in the active preset.
- Terminal closeout has no incomplete required objective/milestone/gate/report.
  Completed work in later phases than the current governed phase, or a closed
  terminal history reopened as continuous without increments, is surfaced for
  reconciliation rather than silently reclassified.

#### Health semantics

- **red** — critical delivery blocker, failed required compliance gate,
  production/security release failure, or blocked required milestone.
- **yellow** — material delivery risk, overdue reporting/compliance obligation,
  or unresolved structural contradiction.
- **green** — no material blocker. Non-production development advisories remain
  visible as notes but do not independently lower health.

Compute the normalized set of material conditions and use its deterministic
event identity as the health fingerprint. If it matches the latest
`health.assessed` result, do not write another event or touch `last_activity`.
Preserve a schema-valid explicit governed override only with its reason and
provenance; report, but do not guess through, a conflict with computed health.

The lifecycle and increment invariants in this skill are authoritative for the
public package.

## Reference files

- `references/field-enums.yaml` — canonical enum values for `status`, `classification`, `kind`, etc.
- `references/write-protocol.md` — detailed step-by-step write protocol with code-like pseudocode.

(These reference files are optional; if missing, the above instructions in SKILL.md are self-sufficient.)
