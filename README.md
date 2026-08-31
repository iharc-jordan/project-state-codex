# Project State for Codex

This repository is an independent Codex adaptation of [Atomic 47 Labs' public
Project State plugin](https://github.com/Atomic-47-Labs/project-state-plugin-public),
based on public v4.9.0 commit
[`c0b55ba`](https://github.com/Atomic-47-Labs/project-state-plugin-public/commit/c0b55ba52dfdca9312a1f6150039ed14d569e2db).

Project State is a local-first operating system for multi-stakeholder projects.
Its 43 skills keep shared objectives, milestones, decisions, risks, phases,
stakeholders, compliance evidence, reporting obligations, and report provenance
in a versionable `project-state/` ledger. Routine reports are derived from that
state instead of being recreated from chat history.

The `codex-lean` branch is the public Codex variant and the repository's default
branch. `main` and the `upstream-v4.9.0` tag preserve the unmodified Atomic47
public baseline.

## What the Codex adaptation changes

The adaptation makes Project State useful alongside Codex's native memory,
repository instructions, task tracking, and external issue trackers instead of
duplicating them:

- Codex Memories own personal preferences and recurring operator habits.
- `AGENTS.md` owns repository commands, coding rules, release requirements, and
  execution constraints.
- the active Codex task or Goal owns temporary implementation progress.
- Jira, GitHub, or Linear own individual engineering work items when configured.
- canonical repositories and drives own source-document content.
- Project State owns durable shared project facts, rollups, reporting
  obligations, compliance evidence, provenance, and the corresponding activity
  ledger.

It also removes process duplication:

- one durable fact creates one canonical entity update and one activity event;
- one report owner handles a source event and reporting period;
- optional skills activate only for an applicable pack, capability, configured
  surface, due reporting entry, or explicit request;
- the orchestrator is read-only unless a configured trigger or operator approval
  authorizes a generator;
- the deprecated document-suite generator is only a forwarding alias;
- `automation/tasks.yaml` is the only current automation registry;
- onboarding inspects available sources before asking grouped unresolved
  questions; and
- Claude/Coworker presentation mechanics and dangling private-only references
  are removed without deleting their underlying data, approval, or output
  contracts.

The full reasoning, affected-file matrix, compatibility impact, validation, and
future internal-version disposition are in
[CODEX-ADAPTATION.md](./CODEX-ADAPTATION.md).

## What remains compatible

The Codex branch retains all 43 skill names and automatic discovery, the
`project-state/` and `grant-state/` schemas and paths, IDs, event names, logs,
reports, templates, eight packs, two capabilities, reporting-matrix and
pack-required triggers, Git sharing, provenance, and external-review safeguards.
No alternate Project State format or Codex-only manifest field was added to the
project ledger.

## Install in Codex

Clone the default `codex-lean` branch into the personal Codex marketplace and
install it:

```powershell
git clone --branch codex-lean https://github.com/iharc-jordan/project-state-codex.git "$env:USERPROFILE\plugins\project-state"
codex plugin add project-state@personal
codex plugin list
```

On macOS or Linux, use `$HOME/plugins/project-state` as the clone destination.
If that destination already exists, update or move it deliberately rather than
overwriting it.

The Codex manifest at `.codex-plugin/plugin.json` points to
`./plugin/skills/`. Each skill links to the shared Codex adapter policy in
`plugin/CODEX.md`.

## Repository layout

```text
.codex-plugin/plugin.json       # Codex plugin manifest
.claude-plugin/marketplace.json # preserved upstream marketplace metadata
plugin/CODEX.md                 # Codex ownership, routing, and safety policy
plugin/skills/                  # 43 preserved skill entrypoints
plugin/packs/                   # 8 compliance packs
plugin/capabilities/            # 2 capability definitions
plugin/templates/               # preserved scaffold and report templates
CODEX-ADAPTATION.md             # complete adaptation and validation record
scripts/validate_codex_adaptation.py
```

For the original Claude plugin and its installation instructions, use the
[Atomic47 public repository](https://github.com/Atomic-47-Labs/project-state-plugin-public).

## License and attribution

Atomic47 attribution and upstream links are retained. This adaptation remains
available under the upstream MIT license; see [LICENSE](./LICENSE).
