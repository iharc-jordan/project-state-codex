# Project State (Claude Code plugin)

A generic operational substrate for multi-stakeholder projects. It bundles **41
skills** that turn routine reporting into a byproduct of normal work — milestones,
objectives/KPIs, phase gates, document curation, status reports, funder/grant
compliance, and a local kanban dashboard. Behavior is configured by swappable
**compliance packs**, not hardcoded logic.

## Install

```
/plugin marketplace add Atomic-47-Labs/project-state-plugin
/plugin install project-state@project-state-plugin
```

Then turn on auto-update — **auto-update is off by default for every marketplace that isn't an
official Anthropic one**, so without this your install stays frozen at this version forever, with no
prompt:

```
/plugin  →  Marketplaces  →  project-state-plugin  →  Enable auto-update
```

To check what you have and update by hand:

```
claude plugin list
claude plugin update project-state@project-state-plugin
```

Then start a project:

```
/project-state:project-scaffolder
```

Skills are auto-discovered and namespaced under `project-state:` — e.g.
`/project-state:project-milestone-manager`, `/project-state:project-orchestrator`,
`/project-state:project-kanban`. Claude also invokes them automatically by their
descriptions when you say things like "record a decision" or "draft the weekly".

## What's inside

| Group | Skills |
|-------|--------|
| Foundation | `project-state` (memory layer), `project-scaffolder`, `project-onboarding`, `project-admin` |
| Core ops | `project-phase-gate`, `project-document-curator`, `project-milestone-manager`, `project-goal-tracker`, `project-status-reporter`, `project-inbox` |
| Surfaces & automation | `project-orchestrator`, `project-notifier`, `project-review-meeting`, `project-funder-reporting`, `project-change-register`, `project-blog-publisher`, `project-website-publisher`, `project-jira-publisher`, `project-kanban`, `project-doc-suite`, `project-tech-reports` |
| Compliance (pack-driven) | `project-sred-tracker`, `project-sred-reviewer` |
| Polish | `project-onboarder`, `project-ip-tracker`, `project-external-comms`, `project-lessons`, `project-archive`, `project-git`, `project-harvester`, `project-feedback` |
| Grant | `grant-state`, `grant-scaffolder`, `grant-ingestor` |

**Packs** (`packs/`): `pic-pcais`, `grant-canada`, `sred-canada`, `board-investor`,
`client-services`, `agile-default`, `open-source-community`. Six skills are
profile-driven — they read their behavior from the active pack's YAML profiles.

**Templates** (`templates/`): scaffolder seeds — phase presets, phase manifests,
the manifest/reporting-matrix templates, and the website starter. The kanban
dashboard is bundled in the keep-state-app desktop app, not distributed here.

## The local project-state server (v5)

The plugin starts an MCP server, `project-state`, over the `project-state/` folder of the project you are
in. Skills read and write through it when it serves the project, and every change is:
- checked against the project's kind registry;
- refused if the file changed on disk meanwhile;
- signed and logged.

It has the same tools and views as the cloud server, so an artifact or a skill works the same on a local
project and a cloud one.

- **Needs Node 20.10 or later** on your PATH. Without it the server does not start, and the skills work on
  the files directly, as in v4.
- **Check it:** run `/mcp` in Claude Code, and `project-state` should be connected. Ask *"which project
  does the project-state server see?"* for the folder it found and whose name it signs changes with.
- **Who changes are signed as:** `PROJECT_STATE_ACTOR`, else your `git config user.email`, else your
  operating-system account. Set `PROJECT_STATE_ACTOR` in your environment to choose.
- **Which folder:** `PROJECT_STATE_DIR`, else the nearest `project-state/` above where you started Claude.

## How it works

State is the source of truth. Everything lives in a typed `project-state/`
filesystem (YAML/JSON/NDJSON/markdown) created by the scaffolder. Reports are
generated *from* state; when an artifact disagrees with state, regenerate the
artifact. External sends (Gmail, claims, SC packs, public posts) always stop at a
draft for human review.

## License

MIT — see [LICENSE](./LICENSE).
