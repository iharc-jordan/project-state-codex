# Codex adapter

This adapter applies to Atomic 47 Labs Project State v4.9.0 from public commit
`c0b55ba52dfdca9312a1f6150039ed14d569e2db`.

- Resolve bundled `packs/`, `templates/`, and `capabilities/` paths from this
  `plugin/` directory, not from the operator's project. From a normal skill
  directory the plugin payload is `../..`; from
  `skills/project-inbox/project-intake/` it is `../../..`. Resolve a script or
  reference stored inside the active skill from that skill's own directory.
- Use regular Markdown and conversation output in Codex. Claude artifact,
  Coworker, and interactive-HTML presentation mechanics are not executable
  Codex surfaces. Preserve their substantive data and approval rules without
  claiming live artifacts or clickable HTML controls.
- Use only tools and connectors actually available in the current Codex host.
  Discover matching tools at runtime and report a configured surface as
  unavailable when its connector is absent. Do not install or connect a service
  unless the operator requests it.
- Translate shell examples to the current operating system and shell. On
  Windows, use PowerShell or cross-platform Python instead of macOS `open`,
  Unix-only paths, or `crontab`.
- Obtain explicit operator authorization before external sends, posts, issue
  creation, deployments, repository mutations, or similar external effects.
  Stricter draft-only rules in individual skills remain in force.
- The public archive does not include its private design documents,
  keep-state-app/project-kanban desktop app, deposit backend, or upstream
  auto-updater. Do not invent missing specifications or claim those optional
  surfaces work. The skill instructions and bundled files are authoritative for
  workflows that are present.
- Bundled scripts do not run on install. Inspect prerequisites and run them only
  when the selected workflow requires them.

## Canonical ownership

- Codex Memories own personal preferences and recurring operator habits. They
  never override a checked-in project fact.
- The nearest applicable `AGENTS.md` owns mandatory repository commands, coding
  rules, release requirements, and execution constraints.
- The current Codex task or Goal owns the temporary implementation objective and
  its completion state.
- Jira, GitHub, or Linear owns individual engineering work items when that
  surface is configured.
- Canonical drives and repositories own source-document content.
- Project State owns shared project objectives, milestone rollups, decisions,
  risks, phases, stakeholders, reporting obligations, compliance evidence, and
  report provenance.
- Store stable ticket and document references in Project State rather than full
  external records unless an active pack explicitly requires a managed copy.
- Reports are derived views. Write a new fact to its canonical entity before
  regenerating a report that presents it.
- A durable change creates one canonical entity update, any required
  counters/pointers, and one corresponding activity event. Do not create a
  parallel representation of the same fact.

## Scale and materiality

Classify the requested operation from the operator's request and supplied
repository evidence. This is routing policy, not a manifest field:

- **task** — a bounded implementation item inside a larger product. Use the
  active Codex task and configured issue tracker. Do not scaffold Project State
  or create an entity merely because code work exists.
- **epic** — one shared outcome spanning meaningful deliverables or
  dependencies. Use one objective/outcome plus only durable milestones,
  decisions, risks, external references, and revision-keyed evidence.
- **program** — ongoing multi-developer, reporting, compliance, grant, or
  portfolio operations. Use the full facility only when those shared operating
  needs justify it or the operator explicitly asks to initialize one.

Before any canonical write, apply the materiality gate. A fact is material when
it changes a shared API, data, or architecture contract; an objective or
milestone commitment; a durable decision or risk; a compliance or reporting
obligation; a governed phase; or a release boundary. Formatting, routine code
changes, ordinary commits, test reruns, and task-local progress are not material
by themselves. For a non-material fact, leave Project State unchanged and point
to the task, Git history, or issue tracker instead. An operator may explicitly
override this gate by asking Project State to record the fact and supplying a
reason; use the existing entity/event contract and include the reason in the
canonical summary rather than adding a schema field.

Explicit scaffold/onboarding requests still create the existing standard file
tree and schema. Ask only unresolved required, pack-driven, or routing-critical
questions after inspecting supplied evidence. Never infer an objective,
milestone, pack, capability, surface, identity, or timezone.

## Idempotent writes and projections

Canonical events continue to use `ts`, `actor`, `event`, `id`, and `summary`.
Legacy lines and their established aliases remain readable. Do not add a second
deduplication ledger or new required event fields.

Before appending an event, compute its deterministic identity from existing
inputs. Use the event name plus the target entity and normalized resulting fact;
for validation or release evidence include the exact source revision; for a
report include its reporting period, output owner, and canonical output path;
for delivery include the artifact's stable reference/revision, audience, and
surface. Where an existing event contract reserves `id` for the entity, retain
that value and compare the normalized tuple. Otherwise store a stable
`evt-<first-20-lowercase-hex-of-sha256(tuple)>` in the existing `id` field.
Length-prefix tuple values before hashing so concatenation is unambiguous.

If the same deterministic identity already exists and the canonical target is
already in the requested state, return or cite that record. Do not append an
event, increment a counter, regenerate an output, notify again, or update
`last_activity`. A changed source revision or material result is a new fact and
therefore a new identity. Preserve history; never rewrite legacy duplicates.

Treat `state.json` as a compatible projection at its established path:

- counters are counts of unique canonical entity IDs;
- `last_activity` is the maximum valid canonical event `ts`;
- phase follows `manifest.yaml:phases.current_phase` plus successful explicit
  transition/lifecycle operations, with `state.json.current_phase` as a mirror;
- phase disagreements are reconciliation findings, never guessed from
  completed milestones;
- `automation/tasks.yaml:timezone` mirrors the manifest timezone when present;
  null/missing or conflicting values are findings, not permission to infer one;
- health changes only when a material health condition or governed override
  changes. Reuse the deterministic event identity as its fingerprint.

Reconciliation and validation are read-only dry runs by default. Report proposed
counter, pointer, phase, timezone, lifecycle/increment, closeout, duplicate-ID,
and health corrections without writing them. Applying a repair requires an
explicit operator request and routes each canonical change through
`project-state`; reports themselves remain derived views.

Default health is red for a critical delivery blocker, failed required
compliance gate, production/security release failure, or blocked required
milestone; yellow for a material delivery risk, overdue reporting/compliance
obligation, or unresolved structural contradiction; and green when none apply.
Development-only advisories remain disclosed but do not change health unless
they affect a required production or release path. Preserve schema-valid
governed overrides only with their existing reason and provenance.

Terminal closeout requires consistent objectives, milestones, phase gates, and
required reports. Continuous operation requires a meaningful current or closed
increment. Missing, stale, or contradictory lifecycle data produces a
reconciliation finding rather than invented state.

## Progressive reads

Routine reads start with bounded summaries. List operations return summary
fields with filters, a caller-set limit (default 50, maximum 200), and a stable
cursor when more results exist. Full entity content requires explicit detail
mode. Activity reads accept `since`, `limit`, and `cursor`; the cursor represents
the last returned timestamp plus deterministic line position and is not stored
as canonical state. Routine status reads state summary, active/at-risk/due
items, and recent events before opening referenced details. Full documentation,
historical, or deep-ledger scans remain available only when explicitly requested
or contractually triggered.

## Lean routing

Normal project operation routes through `project-state`, scaffolding/onboarding,
milestone and goal tracking, phase gates, document curation, orchestration,
status reporting, and deliberate Git synchronization. Keep every other skill
discoverable, but invoke an optional skill only when an applicable pack or
capability is active, its delivery surface is configured and available, a due
enabled reporting-matrix entry requires it, or the operator explicitly requests
it. A detected keyword may prompt for configuration; it does not enable a pack,
capability, automation, connector, or external surface.

Use one report owner per request:

- routine status, weekly report, or Steering Committee status pack →
  `project-status-reporter`
- funder or customer claim/report → `project-funder-reporting`
- audience-specific brief → `project-onepager`
- full documentation bundle → `project-doc-suite`
- technical intelligence → `project-tech-reports`
- public project website → `project-website-publisher`

The orchestrator is read-only by default. It may invoke a generator only after
explicit operator acceptance, a due enabled reporting-matrix entry, or an active
pack's required trigger. For one source event and reporting period, invoke one
owner once; do not fan the same request out to multiple generators. Existing
configured outputs keep their established paths and formats.

`project-state` is the only gateway for canonical entity and activity-ledger
mutation. A report or automation generator may write only its owned derived
artifact, then route the required pointer, counter, outbox, and activity updates
through `project-state`.

At the first Project State operation in a session, a Git-backed facility may
compare `HEAD` with its locally known upstream ref and warn once when the branch
is behind or diverged. Never fetch, pull, commit, or push automatically. Advisory
lockfiles coordinate writers sharing one filesystem or server-backed substrate;
they do not coordinate separate Git clones. Conflicting edits to the same entity
require explicit resolution. Material implementation-linked state normally
travels on the same branch and through the same protected/default-branch merge
as the code it describes. State-only commits remain valid for governance,
meetings, decisions, reports, and post-commit evidence when their reason or
revision is linked. Before merge, reject or surface stale base revisions,
duplicate deterministic event IDs, and incompatible same-entity edits. Ordinary
Git conflict resolution is the serialization point: `merge=union` retains
distinct log lines but does not prove semantic compatibility, and no parallel
change-request ledger is created.
