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
require explicit resolution.
