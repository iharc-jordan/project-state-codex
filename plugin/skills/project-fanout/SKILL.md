---
name: project-fanout
description: "Check or run a named routine across explicitly selected projects or an existing project registry."
map:
  tier: P2
  stage: control
  requires: [memory]
  reads: [manifest, automation-tasks, log]
  calls: [project-harvester, project-orchestrator]
  delivers: [chat]
---

# Project fanout

Read the shared Codex adapter (`plugin/CODEX.md`) once per task. Use this skill when the user explicitly asks for the same bounded operation across several projects, or asks about runs already recorded by an existing configured registry. It does not discover projects by scanning the machine, install unattended routines, or assume a private tooling checkout.

## Select projects

Use the project IDs the user named. If the user refers to an existing configured project group, read that registry and select only its entries. If neither yields a definite set, ask which projects should be included. Resolve each selected project through `project_list` when the Project State MCP is available. A listed project uses server tools for all state operations; never bypass a server rejection with filesystem writes. For a selected local project not served by MCP, use its local project-state binding.

Check each selected project's manifest and enabled capabilities before acting. Preserve the existing run order when the registry specifies one. If no order is specified, use the user's order. Report a missing or inaccessible project as skipped with the reason; do not substitute a similar name.

## Operations

- `status`: summarize existing run records for the selected projects, with the time window and source. Distinguish an absent record from a failed run. Do not infer that a nightly or morning routine exists merely because a registry has cadence entries.
- `list <phase>`: list the selected projects eligible for `harvest`, `tick`, or `digest`, and why any are skipped. A project's `automation/tasks.yaml` is its cadence registry.
- `run <phase>`: run the phase for the selected projects now, or for one named project. `harvest` routes to `project-harvester`; `tick` routes to `project-orchestrator tick`; `digest` uses the orchestrator's read-only briefing. Keep each project's writes and attribution in that project's state. Follow that skill's own restrictions on external sends.
- `digest`: give one concise consolidated answer from the selected projects' actual state or existing digests, identifying any missing results. One owner reports the result to the user.

Run independent selected projects in parallel only when useful and within the host's available agent capacity. Assign each worker one project and one phase, with the relevant requirements path and a bounded result. The parent owns the final consolidation. Do not create custom worker infrastructure or pin a model or reasoning level; inherit the active host selection.

## Recurrence

A direct request for recurring fanout work can use `mcp__codex_app__automation_update`. Prefer a thread heartbeat for follow-up work in this conversation. Use a standalone cron only when the user explicitly requests a standalone saved-project job; resolve the saved project with `list_projects`. The automation prompt must name the configured registry or the exact selected projects and phase, so a future run does not broaden the selection. Inspect an existing automation before changing it. Do not create recurring jobs for a generated suggestion, a status request, or plugin installation.

The project cadence remains in `automation/tasks.yaml`; `project-scheduler` owns edits to it. Report whether a Codex host automation is actually registered, rather than treating a cadence record as execution proof. External messages, publishing, and cross-project state changes require the authority supplied by the originating user request and the invoked skill.
