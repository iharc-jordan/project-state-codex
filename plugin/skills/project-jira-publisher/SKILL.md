---
name: project-jira-publisher
description: "Publish project-state entities to Jira via the REST API — milestones, risks, decisions, objectives and KPIs become Jira issues. Idempotent: the first run creates an issue and writes the returned key back onto the entity (jira_key: PROJ-123); later runs update that issue, never duplicating. Non-secret config (base_url, project_key, issue types) lives in manifest.yaml surfaces.jira; the API token comes from the JIRA_API_TOKEN env var so it never touches the substrate. Use whenever the user says 'publish to Jira', 'push milestones to Jira', 'sync to Jira', 'create Jira issues from the project', 'export the project to Jira', or 'set up Jira'. Always preview with --dry-run first and confirm before the live push; nothing is sent without the user's go-ahead."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# project-jira-publisher

Push the project's structured entities into Jira and keep them linked, so a Jira-using
team sees the plan without leaving Jira. The work is done by `publish.py` (a stdlib +
PyYAML REST script in this skill folder); this doc is how to drive it.

## What maps to what

| Substrate | Jira | Labels |
|-----------|------|--------|
| `milestones/M<NN>.yaml` | issue (default `Task`; set `Epic` per-kind if you want) | `milestone`, status |
| `risks/R-<NN>.yaml` | issue | `risk`, status |
| `decisions/*.yaml` | issue | `decision` |
| `objectives/O<NN>.yaml` | issue | `objective`, horizon |
| `kpis/KPI-<NN>.yaml` | issue | `kpi` |

Each issue's summary is the entity title/metric; the description carries the narrative,
status, dates, and (for KPIs) baseline → current → target.

## Idempotency — the core discipline

The first publish **creates** the issue and writes `jira_key: PROJ-123` back onto the
entity's YAML. Every later run **updates** that issue by key. So re-running after edits
syncs changes and never duplicates. The `jira_key` is the link of record; don't remove it.

## Configure (once)

Add a `jira` surface to `manifest.yaml` (non-secret config only):

```yaml
surfaces:
  jira:
    enabled: true
    base_url: https://yourco.atlassian.net
    project_key: PROJ
    issue_type: Task              # default for every kind
    issue_types: { milestone: Epic }   # optional per-kind override
    email: you@yourco.com         # the account the API token belongs to
```

The **API token is never stored in the substrate.** Create one at
id.atlassian.com → Security → API tokens, then export it for the run:

```bash
export JIRA_API_TOKEN=…           # required
# optional overrides: JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_EMAIL
```

## The routine

1. **Preview** — always dry-run first and show the user the plan:
   ```bash
   python3 publish.py --dry-run            # all kinds
   python3 publish.py --dry-run --only milestones,risks
   ```
   It prints CREATE/UPDATE per entity with the issue type and labels. Nothing is sent.
2. **Confirm with the user.** Publishing creates/edits issues in an external system —
   never run the live push without an explicit go-ahead.
3. **Publish** — drop `--dry-run`:
   ```bash
   export JIRA_API_TOKEN=…
   python3 publish.py --only milestones,risks,decisions,objectives,kpis
   ```
   It creates new issues (writing `jira_key` back) and updates ones already linked.
4. **Report** the result: N created, M updated, and that the `jira_key`s were written
   back (so the project-state files now carry the Jira links). Suggest a
   `project-git checkpoint` since entity files changed.

## Scope & flags

- `--only <kinds>` — comma list of `milestones,risks,decisions,objectives,kpis`.
- `--dry-run` — preview only.
- `--state-dir <dir>` — point at a specific `project-state/` (defaults to walking up
  from cwd for `manifest.yaml`).

## Discipline

- **Preview, confirm, then publish.** Mirrors the suite's review-not-author rule for
  external surfaces — Jira issues are outward-facing.
- **Token only in env**, never in `manifest.yaml` or any committed file.
- **`jira_key` is the link** — re-runs update, they don't duplicate. Don't strip it.
- Jira Cloud REST v2 (plain-text descriptions). For Jira Server/Data Center, the same
  endpoints work with a PAT; set `JIRA_EMAIL` to any value and use the PAT as the token,
  or adapt the auth header in `publish.py`.

## Integration

Invoked by `project-orchestrator` when the user asks to publish to Jira, or directly.
Reads the substrate (milestones, risks, decisions, objectives, kpis) and writes back
only the `jira_key` field. Does not send email or post elsewhere.
