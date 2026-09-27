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

## How it works

State is the source of truth. Everything lives in a typed `project-state/`
filesystem (YAML/JSON/NDJSON/markdown) created by the scaffolder. Reports are
generated *from* state; when an artifact disagrees with state, regenerate the
artifact. External sends (Gmail, claims, SC packs, public posts) always stop at a
draft for human review.

## License

MIT — see [LICENSE](./LICENSE).
