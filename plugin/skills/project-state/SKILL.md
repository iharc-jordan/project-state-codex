---
name: project-state
description: "Read or write the project's state — 'what's the project state', 'record a decision', 'log a risk', 'who is on the team', 'validate the manifest', 'enable SR&ED'. The memory layer every project-* skill writes through."
map:
  tier: P0
  stage: keep
  requires: [memory]
  binding: owner
  reads: [manifest, state, log]
  writes: [manifest, state, log]
  delivers: [kanban]
  role: memory-layer
---

# Project State — the memory layer

> **When to use.**
>
> The shared memory of a project. Read, write, or validate project state — manifest, current phase, milestones, decisions, risks, changes, people, documents, activity log. Trigger on 'what's the project state', 'record a decision', 'log this change', 'update milestone M03', 'who is on the steering committee', 'what phase are we in', 'append to activity log', 'check state health', 'validate the manifest', or any request that reads or writes `project-state/`. Also trigger automatically whenever another project-* skill (phase-gate, document-curator, milestone-manager, status-reporter, notifier, sc-meeting, claim-prep, change-register, orchestrator) needs to read or write state — they route through this one. Also owns the capability lifecycle — enable, disable, and validate bundled capability plugins for this project: 'enable SR&ED', 'turn on the sred capability', 'is SR&ED enabled', 'disable the capability'. Works for any `project-state/` found by walking up from cwd.

## Purpose

Every `project-*` skill depends on this one. `project-state` is the *only* skill that reads and writes `project-state/` directly; every other skill expresses intent ("create milestone", "transition phase") and this skill enforces schema, concurrency, and logging.

Without this skill, state edits drift, two agents clobber each other on the shared drive, and the activity log stops being trustworthy.

## Codex binding and project selection

Read `plugin/CODEX.md` once when Project State first runs in this task. Discover available Project State MCP tools and call `project_list` before opening or changing project files. Match the selected project by its served identity or local folder. If it is served, use its tools for all operations: prefer domain actions (`milestone_update`, `kpi_reading`, `queue_action`, and similar) and use `get_entity` / `list_entities` / `entity_put` / `entity_patch` / `log_append` for general work. Supply `base_sha256` from the last read when replacing or patching an entity; preserve unknown fields. The server validates kinds, IDs, paths and attribution. A rejection never authorizes a file write around it.

For a local project not served by MCP, walk upward from the current directory to `project-state/manifest.yaml`, or use a valid `PROJECT_STATE_DIR` when configured. If absent, answer a read-only request with the finding; route a requested initialization to `project-scaffolder`. A local `home.kind: server` manifest is a read-only copy: use the configured cloud connector for writes. The deposit binding requires its actual endpoint and personal token; never claim it exists merely because the skill mentions it. Use one substrate per project.

General MCP entity and log calls are distinct operations, not an atomic transaction. Inspect the resulting entity, event and projection after a partial failure, then reconcile only the missing step. Do not duplicate an event. Domain actions that log their own change need no second `log_append`. On local files, use the write protocol below and preserve current project data. The actor is the server's authenticated identity or, for local files, a configured actor, signed-in identity or real Git email; ask once only if no source resolves it.

Before repeating an update, read the canonical target and compare the requested final values with the existing values. If they already match, return the existing result without invoking a writer, stamping time, or appending a log. Domain tools are not assumed idempotent merely because they are domain tools. The milestone update tool also returns unchanged for identical values; general repeat detection remains owned here.

Routine reads begin with bounded summaries and recent activity, then open details needed for the answer. The same canonical paths apply across bindings. Installation alone does not enable a capability or migrate project data.

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

**Get current phase.** `state.json:current_phase` → read `phases/<phase>/manifest.yaml`.

**Get entity.** Input: `kind` + `id`. Locate file by filename convention (see SCHEMA.md). Return parsed YAML.

**List entities.** Input: `kind`, optional filters (status, owner, phase). Return array.

**Tail activity log.** Input: `n=50`. Return last n lines of `logs/activity.ndjson` parsed.

**Count entities.** Return counters from `state.json`.

**Validate.** Walk every YAML/JSON in `project-state/`; confirm it parses **under a duplicate-key-strict loader** and has required frontmatter. Report deviations; do not auto-fix. Full check list under "Validate the state" below.

### Who the actor is (every write)

`created_by`, `last_modified_by`, the lock's `actor` and the activity line's `actor` all name **the
person responsible for this write** — resolved once per session, in this order:

1. **Deposit binding:** the token's email, server-resolved (see *Substrate binding*). Never claimed.
2. **`$PROJECT_STATE_ACTOR`**, when set. Hosts set it: the kanban, scheduled routines, eval harnesses.
3. **The signed-in person's email**, when the host tells you who you are talking to.
4. **`git config user.email`** of the repository holding `project-state/` — skipping no-reply
   addresses (`*@users.noreply.github.com`, `noreply@…`), which name an account, not a person.
5. Otherwise **ask once**: "Whose name should go on these records?" — and reuse the answer.

Never write a skill name (`project-state`), `TODO`, a placeholder, or the person the record is
*about*. On-behalf entries keep the two apart: the operator who entered it is `created_by`; the person
who decided or owns it goes in `decided_by` / `owner` (a `people/` id). Only a run **no person
started** — a scheduled routine, a monitor — uses a machine actor, and it says so:
`<skill> (automated)`, e.g. `project-orchestrator (fan-out: tick)`. (Found 2026-09-24: evals wrote
`created_by: project-state` for a decision a person dictated.)

### Write operations (with locking + logging)

For a local file write (MCP writes use the server checks described above):

1. **Find lockfile.** Check `<target>.lock`. If it exists and its `acquired + ttl_seconds` is in the future, wait (up to 30 s) or abort.
2. **Acquire lock.** Write `<target>.lock` = `{actor, acquired, ttl_seconds: 300}`.
3. **Read current state** of the target if it exists.
4. **Check staleness.** If the caller passed a `base_last_modified` and the current file's `last_modified` is newer, return a CONFLICT to the caller. Do not overwrite.
5. **Apply the change.** Update `last_modified`, `last_modified_by` (the actor, above), fields under change. Preserve all other fields. A new entity gets `created` / `created_by` the same way.
6. **Write the file.**
7. **Release lock.** Delete `<target>.lock`.
8. **Append to activity log.** One NDJSON line: `ts, actor, event, id, summary`. `summary` is
   canonical; `detail` and `note` are read-only aliases a reader must accept, in that order, and a
   line whose structured fields say everything needs none of the three. Never rewrite existing lines
   to match. Full vocabulary and validator severity: the project `SCHEMA.md` activity-log contract.
9. **Update state.json counters** if creating a new entity (also under the lock).

Before a general `log_append`, identify the resulting fact by event name, canonical target,
and normalized final value using `scripts/event_identity.py`. Include the exact source
revision for validation or release evidence, or period, owner and output path for a
report. If that identity already exists and the target is already in the requested
state, return the existing result without appending, updating `last_activity`,
regenerating, or notifying. Keep an entity ID in the log's `id` field when the
event contract reserves that field; compare the same tuple to suppress repeats.
Do not rewrite legacy duplicate lines. On partial failure, inspect the entity,
log and `state.json` projection before retrying a missing step.

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
| Log change (non-material)           | `change.logged`             | `counters.change_log_entries` |
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

Discover installed capabilities from each bundled `capabilities/<id>/plugin.yaml`; the current inventory is `sred`, `tender`, `intel`, `portfolio`, and `research`. Installed means available. A project enables one only by an explicit request and a valid `manifest.yaml:capabilities.<id>` block. Paid entitlements and configured delivery surfaces are separate checks. The canonical declaration, required config and schema live in the capability's `plugin.yaml`, `templates/manifest-block.yaml`, `schema/`, `validator/`, and `surfaces.yaml` when present.

To enable or update a capability, check compatibility and obtain required configuration from the operator or existing project evidence. Preserve unknown fields and adopt existing namespaced records. Use the bundled migration script, if one exists, only for this explicitly requested operation; inspect its dry run or changes before applying. Add the manifest block, missing schema directories and state file, and merge bundled reporting defaults without replacing an existing entry of the same ID. Route cadence compilation through `project-automator update` into `automation/tasks.yaml`; a capability is not grounds to create a recurring Codex automation without a scheduling request. Log the resulting capability event once. Report the actual changes and next configured cadence, if any.

Legacy Tender configuration and `tenders/` records belong to the same `tender` capability; adopt them without creating another pursuit ledger. Disabling a capability sets its block to `enabled: false`, disables its seeded matrix entries, and preserves its data. If the runtime state shows an outstanding governed obligation or deadline, present its actual date and ask for the specific decision before disabling. Validation composes the core checker with enabled capability validators, reports version/configuration drift and missing state, and never auto-migrates.

Per-entry profiles resolve from the active pack or the bundled pack of an enabled capability. A reference to an unavailable pack is a validation error. Existing paths, logs, operator schedules and report outputs remain canonical.

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
Nothing about conversion is destructive; see `project-phase-gate` for the transition contract.
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

## Concurrency discipline (for local files)

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
Read `state.json:current_phase`. Read `phases/<phase>/manifest.yaml`. Return phase label + gate-out checklist with done/pending counts.

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
Tail `logs/activity.ndjson`. Default to last 50 events. Pretty-print with timestamp + actor + event + any `id`/`summary`.

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
- Lifecycle consistency — see below
- The heavy-artifacts register — see below

Return a summary; never auto-fix.

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
- Every increment at `status: closed` or `cancelled` has `closed`, `phase_at_close`, `closed_what`, a
  frozen `phases/`, and a `gates.json`.
- `increment` references on milestones name existing increments.
- `cycles_back_to` on any phase manifest names a phase id in the active preset.

Use the project schema and bundled phase-gate contract.

#### Heavy-artifacts register

`manifest.yaml → caches` lists what the project's tools download that is large, and where each is
cached. **Absent or `~` is valid and never reported**; `[]` means asked, nothing heavy. For each
entry, with `<repo>` the folder holding `project-state/` (or the entry's `repo`, relative to it):

- `artifact`, `tool`, `path` and `setting` are present — **error** if not.
- `path` is relative and stays inside the repository: absolute, `~` or a `..` segment is an **error**.
- `path` has no `node_modules` segment — **error**: a clean install deletes it, which is the defect the
  register exists to prevent (FB-001).
- `git -C <repo> check-ignore -q -- "<path>/"` exits 0. Exit 1 is an **error** (a cached binary must
  never be committable). Exit 128, or `<repo>` not on this machine, is **info: not checked here**. Keep
  the trailing slash: without it, a directory rule like `.cache/` does not match a cache folder that
  has not been created yet.
- `path` sits under `.cache/`, or the entry carries a `note` saying why not — **warning** otherwise.

Offer a missing ignore rule as a one-line `.gitignore` addition, shown before it is written. Never
change the tool's own setting; that is the code owner's change. Shape, the tool table and the CI cache
step: `references/heavy-artifacts.md`.

## Reference files

- `references/field-enums.yaml` — canonical enum values for `status`, `classification`, `kind`, etc.
- `references/write-protocol.md` — local write protocol.
- `references/heavy-artifacts.md` — the `caches` register: shape, the shared `.cache/` convention,
  where common tools look, what validate checks, and the CI cache step.

(These reference files are optional; if missing, the above instructions in SKILL.md are self-sufficient.)
