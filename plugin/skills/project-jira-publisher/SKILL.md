---
name: project-jira-publisher
description: "Publish milestones, risks, decisions, objectives and KPIs to Jira — 'push to Jira', 'sync milestones to Jira', 'create Jira issues for the risks'. Idempotent; writes jira_key back."
map:
  tier: P2
  stage: generate
  requires: [memory, python, connector:jira]
  reads: [milestones, risks, decisions, objectives]
  writes: [milestones, risks, decisions, objectives]
  delivers: [jira]
---

# project-jira-publisher

> **When to use.**
>
> Publish project-state entities to Jira via the REST API — milestones, risks, decisions, objectives and KPIs become Jira issues. Idempotent: the first run creates an issue and writes the returned key back onto the entity (jira_key: PROJ-123); later runs update that issue, never duplicating. Non-secret config (base_url, project_key, issue types) lives in manifest.yaml surfaces.jira; the API token comes from the JIRA_API_TOKEN env var so it never touches the substrate. Use whenever the user says 'publish to Jira', 'push milestones to Jira', 'sync to Jira', 'create Jira issues from the project', 'export the project to Jira', or 'set up Jira'. Preview with --dry-run first. A direct request to publish or sync the selected entities authorizes that push; ask only if its target or scope is unresolved, or publication has not been authorized.

Push the project's structured entities into Jira and keep them linked, so a Jira-using
team sees the plan without leaving Jira. The work is done by `publish.py` (a stdlib +
PyYAML REST script in this skill folder); this doc is how to drive it.

Resolve the project through `project-state` and `project_list` first. For an
unserved local facility, use the bundled script with an explicit `--state-dir`.
For a served facility, read the selected entities and non-secret Jira config
through MCP into a task-owned staging folder outside the project, run the same
script against that staging folder, then patch returned `jira_key` values through
MCP using each entity's last-read `base_sha256` and append the attributed activity
event through the state gateway. Do not run a file-writing publisher against a
served facility. If a key write is refused after Jira accepted a change, retain
the returned mapping and report the partial result; reconcile the missing link
before retrying publication so it cannot create a second issue. Remove staging
only after its useful result is preserved. Cloud projects require their actual
configured state connector.

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
2. **Resolve authorization and scope.** Reuse authorization already given for the
   selected Jira target and entities. A setup or preview request alone does not
   authorize a live push; ask only for missing authorization or material choices.
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

- **Preview, then publish within the authorized scope.** Resolve any material
  ambiguity before sending; do not require a second approval for a direct request.
- **Token only in env**, never in `manifest.yaml` or any committed file.
- **`jira_key` is the link** — re-runs update, they don't duplicate. Don't strip it.
- Jira Cloud REST v2 (plain-text descriptions). For Jira Server/Data Center, the same
  endpoints work with a PAT; set `JIRA_EMAIL` to any value and use the PAT as the token,
  or adapt the auth header in `publish.py`.

## Integration

Invoked by `project-orchestrator` when the user asks to publish to Jira, or directly.
Reads the substrate (milestones, risks, decisions, objectives, kpis) and writes back
only the `jira_key` field. Does not send email or post elsewhere.
