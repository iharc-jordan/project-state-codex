# Project State for Codex

Project State keeps durable project facts, milestones, decisions, risks, evidence,
reporting obligations, and activity history in a local-first `project-state/`
facility. This independent Codex adaptation retains Atomic 47 Labs attribution
and the [MIT license](./plugin/LICENSE).

Version **5.5.0** incorporates the public Atomic47
[5.5.0 baseline](https://github.com/Atomic-47-Labs/project-state-plugin-public/commit/a21f28270027b031ec718ebe44dc0fb283be50eb).
The exact upstream revision is recorded separately in [upstream.json](./upstream.json).
`main` is the sole maintained branch. Releases use ordinary semantic versions
and `vX.Y.Z` tags; historical tags remain available.

## Install and update

Use Node.js 18 or newer for the bundled stdio MCP server. In a configured
personal marketplace, clone this repository to the marketplace source directory:

```powershell
git clone https://github.com/iharc-jordan/project-state-codex.git "$env:USERPROFILE\plugins\project-state"
codex plugin add project-state@personal --json
codex plugin list --json
```

For an existing clone, update its `main` checkout, then run the same `plugin add`
command. The personal marketplace must already point `project-state` at that
clone. Start a fresh Codex process after an update so it discovers the new
skills and MCP registration. The stable plugin identity is `project-state@personal`.

Installation makes the workflows available. Capability enablement, connectors,
paid entitlements, project migrations, schedules, and external publishing remain
per-project choices. Installation creates no facility, cache, or recurring job.

## Use

Ask for project state, a milestone update, a status report, or an explicitly
requested initialization. Routine code work does not create a project facility.
The selected model and reasoning settings are inherited from Codex.

The checked MCP server discovers served projects through `project_list` and
provides domain operations plus general entity operations with stale-write
checks. A server refusal cannot be bypassed with file writes. Local projects
that are not served can use the existing filesystem binding; cloud projects
require their configured connector.

Codex currently starts a plugin MCP in its installed directory and does not
provide the active workspace path. To bind the local server to a selected
facility, set the existing `PROJECT_STATE_DIR` environment variable before
starting Codex. Without that binding, `project_list` reports no local facility
and the skill uses the existing file binding for an unserved local project.
This requires no global configuration change.

Available workflows cover core project operations, grants, SR&ED, Tender,
Intel, Portfolio, Research, work-type packs, reporting, scheduling, fanout,
and local HTML snapshots. Installed capability inventory is distinct from
paid entitlement identifiers. `automation/tasks.yaml` remains the project
cadence registry; explicit scheduling requests use Codex native automations.

## Validate and release

Python with PyYAML, Node.js, and Git are needed for repository checks:

```powershell
python scripts/validate_codex_adaptation.py
python -m unittest discover -s tests -v
```

The validator derives its inventory from the pinned upstream commit. Runtime
tests use disposable synthetic facilities. Do not test migrations or writes
against real projects.

Commit validated changes directly on `main`, publish that revision, and tag it
`vX.Y.Z`. Verify the remote revision and installed payload before reporting a
release current. [CODEX-ADAPTATION.md](./CODEX-ADAPTATION.md) describes the host
integration and validation limits.

## Layout

- `.codex-plugin/plugin.json` and `.mcp.json`: supported Codex registration.
- `plugin/CODEX.md`: compact host adapter, read once per active task.
- `plugin/skills/`, `capabilities/`, `packs/`, `templates/`: bundled workflows and contracts.
- `plugin/server/`: upstream checked MCP engine and snapshot renderer.
- `plugin/scripts/start-state-mcp.mjs`: installed-path launcher.
- `scripts/` and `tests/`: package and synthetic runtime validation.

For the original Claude distribution, use the
[Atomic47 public repository](https://github.com/Atomic-47-Labs/project-state-plugin-public).
