---
name: project-scheduler
description: "Read or change a project's recurring work: 'move the weekly report to Friday', 'schedule a review', 'what runs next'."
map:
  tier: P2
  stage: control
  requires: [memory]
  reads: [reporting-matrix, automation-tasks, state, milestones]
  writes: [automation-tasks]
---

# Project scheduler

Read the shared Codex adapter (`plugin/CODEX.md`) once per task. The reporting matrix specifies *what* is needed; `project-state/automation/tasks.yaml` is the canonical project cadence registry for *when*. This skill edits the registry. `project-automator` compiles matrix entries; `project-orchestrator tick` evaluates due work. A Codex automation is a host trigger, separate from this registry.

## Locate the schedule

Resolve the current project through `project-state` and `project_list` when the MCP server is available. If the server lists the project, use its tools for state operations; a rejected operation must not be retried against the files. For an unserved local project, locate its `project-state/manifest.yaml` and work through the local project-state binding. Do not select a different project by searching unrelated directories. Read the manifest, `automation/tasks.yaml`, reporting matrix, state, and relevant milestones. If the registry is absent, use `project-automator generate` when the user asked to set up the schedule; otherwise report that no registry exists.

Use `manifest.yaml:automation.timezone` for project dates and fire times. If it is missing, ask for the project's IANA timezone before creating or changing a timed cadence. Do not infer it from the host clock.

## Changes

Resolve the user's words to an existing task, matrix entry, action, preset, or milestone. If multiple tasks match, name the candidates and ask which one. The supported operations are `create`, `reschedule`, `enable`, `disable`, `accept`, `remove`, `run`, and `apply-preset`. Preserve the existing cadence shape (`kind`, `day`, `hour`, `minute`, `dom`, `month`, `start`, and deadline fields as applicable) and other task fields in `automation/tasks.yaml`. Matrix entries retain their own `enabled` authority; changing a matrix entry itself belongs to `project-state`. A `remove` operation only removes a proposed or ad hoc task. Preserve existing operator reschedules and unrelated tasks.

A **direct request to schedule, move, pause, resume, accept, remove, or run** is authorization for that operation. Apply it and report the resulting state and next fire date. A cadence generated as a suggestion or from a preset without such a request is a disabled `status: proposed` task; report that it needs acceptance. Do not add an extra acceptance step to a directly requested schedule. Milestone check-ins use the existing `scope: {milestone, until: due}` contract; a sprint-aligned task is dormant until `state.json:sprint_calendar` is set. `run` dispatches only the selected task through its established project route; do not send, post, or publish from this skill.

For local file writes, follow the project-state write rules and use the existing `automation/tasks.yaml.lock` advisory lock. Append one attributed `scheduler.<op>` event for an applied operation. For served projects use the server's supported operation and event tools; never bypass a server rejection. On contention or stale state, reread and retry only after reconciling the user's intended change.

## Codex automation host

When the user asks for work to **run automatically on a recurring schedule**,
use `mcp__codex_app__automation_update` after resolving whether the requested
work belongs to this conversation or a standalone saved project. First inspect
whether an existing host trigger already invokes the project's due registry;
update it if appropriate, without creating a duplicate trigger:

- Default to a `heartbeat` attached to the current thread for recurring follow-up work here.
- Use `cron` only when the user explicitly requests a standalone scheduled project job. Resolve its project ID with `list_projects` and use the current supported model and reasoning setting; do not pin a model in this skill.
- An explicit scheduling request authorizes creating or updating that job. A generated suggestion does not. Inspect existing automations before updating one and preserve fields the user did not ask to change.
- Installation, registry compilation, and status reads create no Codex automation. Keep the project registry and any host automation aligned with the user's request; do not create two recurring triggers for one cadence.

For read requests, show upcoming tasks by local date, pending proposals, disabled or orphaned entries, and dormant sprint or expired once tasks. State which work is project registry only and which has a verified Codex host trigger. Never present a registry entry by itself as proof that an automation will fire.
