---
name: portfolio-collector
description: "Collect a portfolio's member projects into dated snapshots and a cross-project index — 'collect the portfolio', 'snapshot the members', 'refresh the portfolio index'. Read-only toward members."
map:
  tier: capability
  stage: ingest
  requires: [memory, python, local-fs]
  inputs: [projects]
  reads: [manifest, portfolio]
  writes: [portfolio, state, log]
  calls: [project-state]
  produces: [portfolio-review]
  delivers: [files]
---

# portfolio-collector — snapshot, index, understand

> **When to use.**
>
> Snapshot, index and understand the member projects of a portfolio. For each active member, resolves its location (local path, pulled hub clone, or appliance read API), reads that member's own project-state/ — manifest, state, milestones, risks, decisions, matrix, people, activity tail, harvest cursors, document index incl. dismissed items, capability strips — and writes one dated, never-edited snapshot. Then compiles the cross-member index (one flat file per entity kind, every row tagged with member and path), recompiles the registry, regenerates one cited understanding page per member, and on the scheduled run writes the weekly change note. Skips unchanged members; records unreachable ones honestly. Trigger on '/portfolio-collector all', 'collect the portfolio', 'refresh the index', 'regenerate the understanding pages', or when the digest reports a member unreachable or a harvest stale; scheduled weekly by the portfolio-default pack. Unattended, idempotent, read-only toward members. Never harvests.

The portfolio's eyes and its memory. It reads each member's substrate as it is, writes what it
saw dated, compiles the index the reviewer queries, and writes the page the model reads
before it answers anything about a member. It narrates nothing beyond the files and changes
nothing in a member.

## The engine

Everything below is deterministic file work and runs as a script, so the weekly collect can run
unattended and behaves the same on every runtime:

```bash
python3 scripts/collect.py --portfolio <portfolio>/project-state all --week [--as-of YYYY-MM-DD] [--dry-run] [--force] [--json]
```

The skill's job is to locate the portfolio, run the script, and read its run summary back to the
operator — never to re-implement the walk in prose. `--dry-run` reports what would be read and
written; `--json` returns the summary for the app. A fresh enable with an empty registry and
`discovery: auto` proposes what is under the workspace and stops; activating rows is onboarding's job.

## Verbs

- `all` — every member with `status` in `{active, paused, closing}`.
- `<member-id>` — one member, even if paused.
- `--dry-run` — show what would be read and written; write nothing.
- `--force` — ignore the unchanged-revision short-circuit.
- `--week` — also write the weekly change note (the scheduled run does this by default).

## Context, every invocation

Read `capabilities.portfolio` from the manifest (`workspace_root`, `discovery`, `index`
windows) and `state/portfolio.json` (cursors) once. Refuse if `workspace_root` is missing or
the literal `REQUIRED`.

## How members are read

`collect.py --transport auto` (the default) reads each `local` or `registry` member through the
local project-state server when that server serves it, else from its files, and each `server`
member through the cloud server. `--transport mcp` refuses the file fallback (a member no server
serves is `unreachable: remote`); `--transport files` never starts a server. Whichever way, the
snapshot is the same and records `read_via: files | local-mcp | cloud`.

**Core.** Without a plan that unlocks portfolio (checked offline, only once the install trusts a
key; the cloud server checks the org's plan), the collect runs as Core: member rows, snapshots,
the registry and the digest checks, with the index, understanding pages, at-a-glance, weekly
note and finding lineage skipped — nothing already written is removed. The run summary says
`core: true` and `portfolio.collect.core` is logged. `--core` forces it.

**A portfolio whose home is the cloud** is collected by the cloud server, not by this script on a
laptop: call `portfolio_collect {project, week}` through the Project State connector (editor on the
portfolio). The server runs this same collector over copies of the members the person can see —
members they cannot see are recorded unreachable, never read around — and commits the snapshots,
index, pages and report to the portfolio through its writer, attributed to them. Discovery there
proposes only the portfolio's own org's projects. Weekly, until the cloud scheduler exists: a configured Codex automation or routine that calls `portfolio_collect` with `week: true` — the connector keeps its
own sign-in, so no token is minted and nothing is installed.

**Two copies, one member.** A local home with a Published mirror (`location.mirror`, or the
registry's cloud list), or a cloud home with the copy a move left on disk: the home copy is read
when it answers, else the other copy. The snapshot records `read_copy: home | mirror | moved-copy`,
and when it is not home, `copy_as_of` and `home_unreachable`; the understanding page opens its
"where it is" with that, and `portfolio.member.read-from-copy` is logged. Never present a copy's
facts as current without saying which copy and how old.

## Per member

1. **Resolve the location.** `local` → must resolve inside `workspace_root` (outside →
   `unreachable: permission`, never read). `registry` → the workspace registry's `ref`
   (`org/project`) resolved to its folder, then as `local`. `server` → the cloud project `ref`,
   read through the cloud server with its org's service token from
   `~/.config/project-state/mcp-tokens.json` (`{org: "ksm_…"}`, 0600; a viewer token a superadmin mints for
   the portfolio, scoped to its members), else `$PS_MCP_TOKEN` or `~/.config/project-state/mcp-token`; the URL
   is `$PS_MCP_URL`, else `~/.config/project-state/mcp-url`, else the cloud's own. This is how a portfolio on
   disk reads cloud members unattended. None configured, a token file others can read, or refused →
   `unreachable: remote`, with the reason in the event; never sign in or ask. `hub` → the local clone `project-admin pull`
   recorded; no clone → `unreachable: remote`; never clone here. `appliance` → the read API
   when configured. Missing directory or manifest → `missing`; unparseable → `malformed`.
   Unreachable: write the cursor, log `portfolio.member.unreachable`, continue.
2. **Short-circuit.** `source_rev` (git HEAD, else substrate-rev, else null) equal to the
   cursor's and no `--force` → skip silently.
3. **Read**, tolerating absence, never a member's external surfaces: `manifest.yaml`,
   `state.json`, `milestones/`, `risks/`, `decisions/`, `reporting-matrix.yaml` (dated
   entries in the deadline window), `people/`, the activity-log tail (activity window),
   `harvest/cursors/`, `documents/index.yaml` (untriaged count; items the member's own triage
   dismissed, with surface, contact, keywords), and each enabled capability's
   `always_surface` against the member's `state/<cap>.json`. Scan member entities for
   `source: portfolio:PF-F-NNN` — the only reverse edge this skill computes.
4. **Fill** `templates/snapshot.yaml`. Counts are counts; `deadlines[]` is the merge of
   milestone ends, matrix dates, decision needed-by dates and capability strip dates. A field
   the member does not carry stays absent — never estimated.
5. **Write** `portfolio/snapshots/<member>/<YYYY-MM-DD>.yaml` through `project-state`; a
   same-day file with a different `source_rev` gets a `-<hhmm>` suffix rather than an
   overwrite. Advance the cursor; log `portfolio.snapshot.captured`.

## After the loop, in order

1. **Compile the index** (spec §4.4): `members`, `milestones`, `risks`, `decisions`,
   `people` (with in-flight milestones and owned deadlines per member), `deadlines`,
   `documents`, `activity-<window>d.ndjson`, `tags` — every row with `member` and `path`.
   Log `portfolio.index.compiled`.
2. **Recompile `portfolio/registry.yaml`**: one row per member — id, name, status, kind,
   priority, owner, phase, milestones done/total and at-risk count, open risks and max
   score, pending decisions, next deadline, last event, events 7d, worst harvest cursor age,
   reachable. Log `portfolio.registry.compiled`.
3. **Regenerate understanding pages** from `templates/understanding.md`, one per active
   member, eight fixed headings, every line cited to a member file, "what changed" computed
   against the previous snapshot. Log `portfolio.understanding.generated`.
4. **Weekly change note** (scheduled runs, or `--week`): per member what moved since the
   previous collect, cross-member deadlines in the next 14 days, findings that moved, the
   hopper, index counts, checks fired → `portfolio/reports/week-<date>.md`. Log
   `portfolio.report.generated`.
5. **Discovery** (`discovery: auto`): each workspace-registry project within `workspace_root`
   that no row covers → a `proposed` row with `location: {type: registry, ref}`; each project in
   the registry's `cloud` list (`scripts/build-registry.py`, read from the cloud's project list)
   that no row covers and that has no copy on this disk → a `proposed` row with
   `location: {type: server, ref}`; then any other `*/project-state/manifest.yaml` under
   `workspace_root` → a `proposed` `local` row. `source_row: discovery`. Never activate.
6. **Lineage**: append `{member, entity, at}` to a finding's `became` for each
   `source: portfolio:` reference seen.

## Discipline

- **Read-only toward members.** Opens member files for reading only; never writes, locks or
  logs inside a member. Reads a member mid-write anyway — a dated snapshot of a moving target
  is still dated truth.
- Never fabricate: unreachable is unreachable; absent is absent.
- All portfolio writes through `project-state`; locks are the memory layer's.
- Unattended-safe: no questions, exit clean on partial failure with the per-member table.
