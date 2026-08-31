---
name: project-harvester
description: "Harvest external signals from configured Slack, Gmail, Google Docs, scsiwyg, Jira, Confluence, Linear, and GitHub surfaces into project-state/documents/inbox. Activate only when at least one surface is configured or harvesting is explicitly requested, and use only connectors available in the current host; GitHub may use its connector or gh CLI. Track per-user cursors and preserve the configured local or explicitly supplied deposit binding."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# project-harvester

Pull compact external signals relevant to a project into
`project-state/documents/inbox/` for curation. Source systems remain authoritative
for full issue bodies, comments, and document content. Project State stores stable
identity/reference, provenance, and only the status or bounded excerpt necessary
to decide whether a durable shared fact changed. Create a managed copy only when
an active pack/output contract explicitly requires one.

---

## Philosophy

The harvesters (work-harvester-slack, gmail, gdocs, scsiwyg) ingest *everything* into `~/work-state/` as canonical event envelopes. `project-harvester` is a **focused lens** that runs *after* or *independently* of those harvesters and asks: "of all the signals in these surfaces, which ones are relevant to *this project right now*?"

Relevance is determined from the project manifest — no hardcoded rules. Every project configures its own surfaces, contacts, channels, and keyword terms.

---

## What gets harvested

### Slack
- All messages in `surfaces.slack.channel` (and any additional channels in `surfaces.slack.extra_channels[]`) since the cursor.
- DMs from any person in the project's `consortium.*.contacts[]` list.
- Threads where a project keyword appears in `#general` or other monitored channels.

### Gmail
- All threads involving any `consortium.*.contacts[].email` address (sent or received).
- Threads where subject or body contains any `surfaces.gmail.keywords[]` (if set).
- Drafts under `surfaces.gmail.from_identity` that reference project keywords (if `drafts_only: true`, skip inbound filtering).

### Google Docs
- Docs in `surfaces.gdocs.gdocs_root` folder that were modified since the cursor.
- Also: docs shared *with* or *by* known consortium contacts.

### scsiwyg
- Posts on `surfaces.scsiwyg.site_slug` published or updated since the cursor.
- Posts on any *other* configured sites that contain project keywords in title or body — this catches consortium partner writing that references the project.

### Jira *(via the Atlassian MCP connector)*
- Issues in `surfaces.jira.projects[]` (project keys, e.g. `PROJ`) created or **updated** since the cursor — stable key/URL, title, status, assignee, and updated timestamp. Do not copy full bodies or comments.
- Issues matching `surfaces.jira.jql` (an explicit JQL filter) if set — overrides the project-key scan for power users.
- Issues mentioning a project keyword in summary/description, and issues assigned to / commented on by anyone in the contact roster.

### Confluence *(via the Atlassian MCP connector)*
- Pages in `surfaces.confluence.spaces[]` (space keys) created or updated since the cursor.
- Pages matching `surfaces.confluence.cql` (explicit CQL) if set.
- Pages whose title or body contains a project keyword (catches partner documentation that references the project).

### Linear *(via the Linear MCP connector)*
- Issues in `surfaces.linear.teams[]` (team keys) or `surfaces.linear.projects[]` updated since the cursor — stable id/URL, title, state, assignee, and updated timestamp. Do not copy full bodies or comments.
- Issues matching `surfaces.linear.query` (free-text/filter) if set.
- Issues mentioning a project keyword, or assigned to / commented on by a contact-roster member (matched by email where Linear exposes it).

---

## Manifest keys consumed

```yaml
# project-state/manifest.yaml

surfaces:
  slack:
    enabled: true
    channel: "#project-updates"         # primary project channel
    extra_channels: []                  # additional channels to watch
    workspace: ~                        # Slack workspace name (optional; MCP default if null)
  gmail:
    enabled: true
    from_identity: "operator@example.com"  # replace with the authorized send-as identity
    drafts_only: false                  # if true, skip inbound filtering (pre-award mode)
    keywords: []                        # optional subject/body keywords to match inbound mail
  gdocs:
    enabled: true
    gdocs_root: ~                       # Google Drive folder ID; null = skip folder scan but still scan by contact
  scsiwyg:
    enabled: true
    site_slug: ~                        # slug of the project's own blog; null = skip own-site scan
    watch_sites: []                     # other site slugs to watch for keyword mentions
  jira:                                 # via the Atlassian MCP connector
    enabled: false
    projects: []                        # Jira project keys to watch, e.g. ["PROJ","PLAT"]
    jql: ~                              # optional explicit JQL; overrides the project-key scan
    site: ~                             # Atlassian site/cloud id if the connector serves several
  confluence:                           # via the Atlassian MCP connector
    enabled: false
    spaces: []                          # Confluence space keys to watch, e.g. ["PROJ","ENG"]
    cql: ~                              # optional explicit CQL
    site: ~                             # Atlassian site/cloud id if the connector serves several
  linear:                               # via the Linear MCP connector
    enabled: false
    teams: []                           # Linear team keys to watch, e.g. ["ENG","PLAT"]
    projects: []                        # optional Linear project ids/names to scope to
    query: ~                            # optional free-text/filter query
  github:                               # via the GitHub MCP connector OR the gh CLI
    enabled: false
    repos: []                           # "owner/repo" to watch, e.g. ["example-org/example-repo"]
    events: [commits, pulls, releases, issues]  # which activity to pull (subset ok)
    branch: ~                           # limit commits to a branch (null = default branch)
    query: ~                            # optional GitHub search qualifier (overrides repo scan)

# Consortium contacts are the other key input:
consortium:
  members:
    - contacts:
        - email: "partner@example.org"
          name: "Partner Contact"
  lead_applicant:
    contact:
      email: "lead@example.org"
      name: "Lead Contact"
```

---

## Substrate binding — where reads and writes go

The skill persists through five verbs — `read-context`, `seen?`/`mark-seen`, `write-doc`, `advance-cursor`, `append-activity` — with two interchangeable bindings (resolver owned by the `project-state` memory-layer skill; see its "Substrate binding" section):

- **File binding (default).** Root = `$PROJECT_STATE_DIR`, else `./project-state`. All verbs are the file operations described in this document. Local users and compatible headless runners use this binding. **No remote adapter config → this binding, byte-identical behavior — never ask about remote setup.**
- **Deposit binding (conditional).** The private backend protocol is not bundled
  in the public package. Use this binding only when an installed internal adapter
  supplies the five persistence verbs and the operator explicitly configures and
  authorizes it. Preserve atomic server dedup/cursor/activity behavior and never
  fall back to local writes when that endpoint is unreachable.

**Harvester identity** (used for cursor ownership and provenance): an explicitly
configured identity, else `git config user.email`, else `local`. A supported
deposit adapter must resolve identity server-side rather than trust a claimed one.

---

## Cursor management

Cursors are file-per-entity — one YAML file per (identity, surface) at:

```
project-state/harvest/cursors/{email}--{surface}.yaml
```

```yaml
# project-state/harvest/cursors/operator@example.com--slack.yaml
surface: slack
email: operator@example.com
cursor: "2026-07-20T00:00:00Z"
updated_at: "2026-07-23T09:12:00Z"
```

File-per-cursor means N people (and a supported server adapter) can harvest the same project concurrently with no lock contention and no clobbering — the concurrency rule is the same file-per-entity rule the rest of the substrate uses. **Org-scoped server harvests** use the reserved identity `server` — one project-grain cursor per surface, e.g. `server--slack.yaml`.

Default cursor when missing: 7 days ago. Cursor is only advanced after a surface is fully harvested without errors.

**Migration from v1 cursors:** if `project-state/state.json` still contains a `harvest_cursors` map, on first run copy each value to `harvest/cursors/{identity}--{surface}.yaml` for the current identity, then delete the `harvest_cursors` key from `state.json` (under its advisory lock). One-way, once.

---

## Output — inbox documents

Each harvested item becomes a compact reference/signal markdown file in
`project-state/documents/inbox/`. For tickets, the body contains only the status
snapshot and why it may affect shared Project State. For externally owned
documents, it contains identity/provenance/reference and a bounded excerpt when
needed for classification, not a replacement copy:

```
YYYY-MM-DD-{surface}-{slug}.md
```

### File format

```markdown
---
source: slack                          # slack | gmail | gdocs | scsiwyg | jira | confluence | linear | github
source_id: "C123/1714389612.123456"   # channel/ts, thread_id, doc_id, post_id, issue_key, page_id
harvested_at: "2026-05-04T12:00:00Z"
surface_timestamp: "2026-05-04T09:30:00Z"
author: "Partner Contact"
author_contact: "partner@example.org"
channel: "#project-updates"            # slack only
subject: ~                             # gmail only
doc_title: ~                           # gdocs only
post_title: ~                          # scsiwyg only
issue_key: ~                           # jira/linear only (e.g. PROJ-142)
issue_url: ~                           # jira/linear only — link back to the issue
issue_status: ~                        # jira/linear only (e.g. "In Progress")
page_id: ~                             # confluence only
page_url: ~                            # confluence only
space: ~                               # confluence only (space key)
relevance_signals:                     # why this was flagged
  - contact_match: "partner@example.org"
  - channel_match: "#project-updates"
harvested_by: "operator@example.com" # server-resolved or operator-confirmed identity
harvest_plane: local                   # local | server | desktop | claude-ai (legacy provenance value)
status: inbox                          # always "inbox" on write; curator promotes
---

# {title or first line or subject}

{full text or rich excerpt}

---
_Harvested by project-harvester from {surface} on {date}._
```

The `status: inbox` field is what `project-document-curator` looks for when it scans the inbox. The `relevance_signals` array tells the curator why this doc landed here, which helps it decide how to classify it.

---

## How a harvest run works

### Step 1 — Load manifest and cursors

Read `project-state/manifest.yaml`:
- `surfaces.*` config
- Build the **contact roster**: all emails from `consortium.*.contacts[].email` + `consortium.lead_applicant.contact.email`
- Build the **keyword list**: project `id`, project `name`, any explicit `surfaces.*.keywords[]`

Read this identity's cursor files from `project-state/harvest/cursors/{email}--{surface}.yaml` (run the v1 migration first if `state.json` still has `harvest_cursors`). Default missing cursors to 7 days ago. A supported deposit adapter supplies the equivalent context through its `read-context` verb.

### Step 2 — Slack harvest (if `surfaces.slack.enabled`)

```
channels_to_watch = [manifest.surfaces.slack.channel] + manifest.surfaces.slack.extra_channels
cursor_ts = harvest_cursors["slack"]

for each channel in channels_to_watch:
  mcp__42fdfc76__slack_read_channel(channel, oldest=cursor_ts)
  → messages since cursor

  for each message:
    emit inbox doc if:
      - any message (it's a project channel, all messages are relevant)
      - OR author is in contact_roster
      - OR text contains a project keyword
```

Also search DMs from known contacts:
```
mcp__42fdfc76__slack_search_public_and_private(
  query="{contact_name} OR {contact_email}",
  after=cursor_ts
)
→ filter to DMs involving self and the contact
```

### Step 3 — Gmail harvest (if `surfaces.gmail.enabled`)

Build search queries:
```
contact_query = "from:({emails joined by OR}) OR to:({emails joined by OR})"
keyword_query = manifest.surfaces.gmail.keywords joined by OR (if any)
combined = f"({contact_query}) after:{cursor_date}"
if keywords:
  combined += f" OR ({keyword_query} after:{cursor_date})"

mcp__81e68767__search_threads(query=combined, max_results=50)
for each thread:
  mcp__81e68767__get_thread(thread_id)
  → extract messages, build inbox doc per thread
```

One inbox doc per Gmail thread (not per message) — threads are the natural unit of conversation.

### Step 4 — GDocs harvest (if `surfaces.gdocs.enabled`)

```
if gdocs_root is set:
  mcp__aab407bf__search_files(
    query="modifiedTime > '{cursor_date}' and '{gdocs_root}' in parents"
  )
  → for each file: mcp__aab407bf__read_file_content(file_id)
  → emit inbox doc

# Also scan for docs shared by/with known contacts:
mcp__aab407bf__list_recent_files(count=20)
→ filter by: sharedWithMe == true AND (lastModifyingUser in contact_roster)
→ for each: read and emit
```

### Step 5 — scsiwyg harvest (if `surfaces.scsiwyg.enabled`)

```
if site_slug is set:
  mcp__scsiwyg__list_posts(site_slug, includeUnpublished=false)
  → filter to posts updatedAt > cursor
  → mcp__scsiwyg__get_post(post_id)
  → emit inbox doc

for each watch_site in surfaces.scsiwyg.watch_sites:
  mcp__scsiwyg__list_posts(watch_site)
  → filter to posts where title or body contains project keyword
  → emit inbox doc
```

> **Connectors note (Jira / Confluence / Linear).** These surfaces use an available
> Atlassian or Linear connector in the current Codex host, not a
> project-state-owned server. The exact tool names vary by which connector build
> is installed, so **discover the available `mcp__*` tools at runtime** and use the
> ones that match the operations below. If the connector for a surface isn't
> connected, skip that surface and log it (same as any other surface). All access is
> read-only.

### Step 5b — Jira harvest (if `surfaces.jira.enabled`, Atlassian MCP connected)

```
# Prefer an explicit JQL; otherwise build one from the project keys + cursor.
jql = surfaces.jira.jql or
      "project in (" + join(surfaces.jira.projects) + ") AND updated >= '{cursor_date}'"

<atlassian-mcp search-issues tool>(jql, limit=50)        # e.g. searchJiraIssuesUsingJql / jira_search
for each issue:
  fetch/select only missing stable metadata (key, URL, title, status, assignee, reporter, updated)
  emit inbox doc if:
    - the issue is in a watched project (all such issues are relevant), OR
    - the configured JQL or returned summary matches a project keyword, OR
    - assignee/reporter email ∈ contact_roster
  → frontmatter: source=jira, source_id=issue.key, issue_key, issue_url, issue_status,
    author=assignee||reporter, surface_timestamp=issue.updated
  do not persist the issue body or comments; the issue URL is the evidence reference
```

### Step 5c — Confluence harvest (if `surfaces.confluence.enabled`, Atlassian MCP connected)

```
cql = surfaces.confluence.cql or
      "space in (" + join(surfaces.confluence.spaces) + ") AND lastmodified >= '{cursor_date}'"

<atlassian-mcp search-pages tool>(cql, limit=50)          # e.g. searchConfluenceUsingCql / confluence_search
for each page:
  fetch stable metadata and, only when classification needs it, a bounded source excerpt
  emit inbox doc if: in a watched space, OR the configured CQL/title/excerpt matches a keyword
  → frontmatter: source=confluence, source_id=page.id, page_id, page_url, space,
    doc_title=page.title, surface_timestamp=page.lastModified
  retain page_url and version as evidence; do not copy the full page without an output contract
```

### Step 5d — Linear harvest (if `surfaces.linear.enabled`, Linear MCP connected)

```
# List issues for watched teams/projects updated since the cursor (or run the query).
<linear-mcp list-issues tool>(
  team=surfaces.linear.teams, project=surfaces.linear.projects,
  query=surfaces.linear.query, updatedAfter=cursor_ts, limit=50
)
for each issue:
  fetch/select only stable metadata (identifier, URL, title, state, assignee, creator, updatedAt)
  emit inbox doc if:
    - the issue is in a watched team/project, OR
    - configured query or returned title contains a project keyword, OR
    - assignee/creator ∈ contact_roster (by email where exposed)
  → frontmatter: source=linear, source_id=issue.identifier, issue_key=issue.identifier,
    issue_url=issue.url, issue_status=issue.state, author=assignee, surface_timestamp=issue.updatedAt
  do not persist the issue body or comments; the issue URL is the evidence reference
```

### Step 5e — GitHub harvest (if `surfaces.github.enabled`)

The engineering pulse of the project: commits, pull requests, releases, and issues
in the watched repos since the cursor. This is where "what the code did this week"
becomes project intel the curator can link to milestones.

> **Access.** Two paths, discovered at runtime — use whichever is present:
> an available **GitHub connector**, or the **`gh` CLI** when already authenticated.
> Both are read-only. If
> neither is available, skip the surface and log it.

```
for each repo in surfaces.github.repos:   # or run surfaces.github.query instead
  # --- commits (grouped, not one doc per commit) ---
  if 'commits' in events:
    <gh api repos/{repo}/commits?since={cursor}&sha={branch}>   # or the MCP list-commits tool
    → ONE inbox doc per repo per day summarizing that day's commits (sha, message
      first line, author) — a commit digest, so a busy day is one signal not fifty.
  # --- pull requests ---
  if 'pulls' in events:
    <gh pr list --repo {repo} --state all --search "updated:>={cursor_date}">
    → one reference per PR touched since cursor: number, URL, title, state
      (open/merged/closed), author, merged_at.
  # --- releases ---
  if 'releases' in events:
    <gh release list --repo {repo}>  → filter published/updated > cursor
    → one reference per release: tag, URL, name, published timestamp.
  # --- issues ---
  if 'issues' in events:
    <gh issue list --repo {repo} --state all --search "updated:>={cursor_date}">
    → one reference per issue touched: number, URL, title, state, labels, author, updated timestamp.

  emit each item if:
    - it's in a watched repo (all such activity is relevant), OR
    - title or commit-message metadata contains a project keyword, OR
    - author/committer/assignee ∈ contact_roster (by GitHub login or email where exposed)
  → frontmatter: source=github, source_id="{repo}#{kind}:{id}" (kind ∈ commit-digest|
    pr|release|issue; id = date | pr-number | tag | issue-number),
    repo, ref_url (link back), issue_status (PR/issue state), author,
    surface_timestamp = committed/updated/published time
```

Commits are **digested per repo per day** (not one doc per commit) so a heavy push
lands as a single readable signal; PRs, releases, and issues are one doc each since
those are already the natural units.

### Step 6 — Write inbox docs

For each item flagged for ingest:
1. Build the filename: `{YYYY-MM-DD}-{surface}-{slug}.md` where slug = sanitized title or channel+ts
2. Check if file already exists (dedup by source_id hash) — skip if so
3. Write the markdown file to `project-state/documents/inbox/` (file binding) or
   pass it to the supported deposit adapter's `write-doc` operation
4. Append a one-line entry to `project-state/harvest/harvest.log`:
   ```
   2026-05-04T12:00:00Z  slack   #project-updates/1714389612.123456  → 2026-05-04-slack-project-updates-abc123.md
   ```

### Step 7 — Advance cursors

For each surface that completed without error, write this identity's cursor file:

| Surface | New cursor value |
|---|---|
| slack | max message timestamp seen |
| gmail | max thread date seen |
| gdocs / scsiwyg | now |
| jira / confluence / linear | max issue/page updated seen |
| github | max commit/PR/release/issue timestamp seen |

File binding: rewrite `harvest/cursors/{email}--{surface}.yaml` (single-writer per identity — no lock needed). A supported deposit adapter advances the cursor atomically only past accepted documents.

### Step 8 — Report

Return a summary:
```
## Harvest complete — 2026-05-04

| Surface    | Items found | Written | Skipped (dup) | Errors |
|------------|-------------|---------|---------------|--------|
| Slack      | 14          | 12      | 2             | 0      |
| Gmail      | 3           | 3       | 0             | 0      |
| GDocs      | 1           | 1       | 0             | 0      |
| scsiwyg    | 0           | 0       | 0             | 0      |
| Jira       | 6           | 6       | 0             | 0      |
| Confluence | 2           | 2       | 0             | 0      |
| Linear     | 4           | 4       | 0             | 0      |
| GitHub     | 9           | 9       | 0             | 0      |

12 new docs in project-state/documents/inbox/ — run /project-document-curator to classify.
```

---

## CLI invocation

```bash
/project-harvester                          # all surfaces, use cursors
/project-harvester --since 7d              # override cursor with lookback
/project-harvester --surface slack         # single surface only
/project-harvester --surface gmail,gdocs   # comma-separated surfaces
/project-harvester --surface jira,linear   # connector surfaces (jira | confluence | linear)
/project-harvester --surface github        # commits (digested), PRs, releases, issues
/project-harvester --dry-run               # show what would be written, don't write
/project-harvester --no-advance-cursor     # harvest but don't move cursors (re-run safe)
```

---

## Deduplication

Dedup key: `{surface}:{source_id}`. Stored in `project-state/harvest/seen.json` as a set of hashed keys. On each write attempt, hash the key and check the set. If present, skip. After writing, add to set.

`seen.json` is append-only — never prune. It stays small (one 12-byte hash per harvested item).

Dedup is **load-bearing across harvesters**, not just re-run safety: two users watching the same Slack channel, or a user and a supported server adapter harvesting the same surface, must produce one inbox doc. A deposit adapter owns server-side dedup; the client check is only an optimization.

---

## SR&ED evidence proposals (when the `sred` capability is enabled)

If `manifest.yaml → capabilities.sred.enabled` is true, the sweep additionally matches
harvested signals against the project's SR&ED capture lens (`sred/criteria.yaml →
harvester_hints`) and against active EX records (linked milestones, people). Matches are
dropped into `sred/inbox/` as candidate evidence stubs (`{date, source: {surface, ref},
suggested_ex, tier, description_draft, excerpt?, people}`) and `sred.evidence.proposed`
is emitted.

Sources are swept by evidence tier (schema `evidence_source_tiers`):

- **Tier 1 — Jira** (`hints.jira`): stable references and timestamps for matching issues and
  explicitly cited worklog/comment evidence in the configured projects, plus anything labeled per
  `hints.jira.labels`. Reference is the issue key or evidence permalink (durable,
  server-timestamped); bodies and comments remain in Jira. An issue labeled `sred-ex-NN` /
  `sred-tu-NN` is author-asserted linkage: the proposal arrives pre-linked to that entity
  with high confidence — still confirmed by a human, never auto-logged.
- **Tier 1 — Confluence** (`hints.confluence`): pages in the configured spaces matching
  keywords or carrying the labels. Reference is `<page-id>@<version>` so the citation
  survives later edits. Same `sred-*` label pre-linking convention.
- **Tier 1 — GitHub** (`hints.github`): commits, PRs, issues, and CI build results for the
  watched repos (the existing Step 5e sweep, filtered through the frontier keywords/paths).
  `ci_build` failures on experiment branches are machine-timestamped failed-trial
  evidence — propose them, don't skip them.
- **Tier 2 — Slack** (`hints.slack.channels`) and **Google Docs** (`hints.gdocs.folders`):
  matched the same way, but the stub MUST capture a verbatim `excerpt` and permalink at
  propose time — these sources are editable/deletable, and the excerpt is what survives
  retention. Proposals are marked `tier: 2` so the tracker records them as corroborating.

**Correlation pass (after the per-source sweep) — sources are a cohort, not streams.**
Join matched records across sources on the links dev tooling already creates: Jira issue
keys in commit messages / branch names / PR titles; PR↔issue references; `ci_build` →
commit sha; Confluence↔epic links; `sred-*` labels anywhere. When records join, propose
ONE cluster stub (`{suggested_ex, records: [...], window, corroboration: <distinct source
count>}`) instead of N singles — a Jira issue plus its commits plus a failed build is one
thread of work, and one confirm decision. Rules:

- **Follow links one hop from a match** — a matched Jira issue pulls its linked commits,
  PRs, and builds even if those didn't independently match the keywords; that is the
  cohort finding evidence the keyword sweep would miss.
- **Corroboration is counted, not asserted**: distinct source *types* in the cluster.
  Tier-2 records join clusters as corroborating members but never raise the count on
  their own.
- **Singles still propose** — an unjoinable match is a normal single-record stub. Never
  hold evidence hostage to correlation.
- Confirming a cluster writes each record to the evidence log with `corroborated_by`
  cross-references — the human still confirms; correlation only assembles.

Discipline: candidates are **never** auto-appended to the evidence log —
`project-sred-tracker confirm_evidence` promotes them, a human decision at a time. The
`description_draft` is the source's own words (e.g. the commit subject line), never an
interpretation. If no `sred/criteria.yaml` exists, skip SR&ED matching entirely and note it
once in the harvest summary ("sred enabled but no criteria — run define_criteria").

## Integration with project-orchestrator

`project-orchestrator` calls this skill as the **first step** of its daily routine (before checking milestones, deadlines, etc.) so that the inbox is populated before curator recommendations are made.

```yaml
# Orchestrator daily routine order:
1. project-harvester              ← pull fresh intel
2. project-document-curator       ← classify inbox docs
3. project-milestone-manager      ← check at-risk milestones
4. project-phase-gate             ← check gate items
5. project-status-reporter        ← draft weekly if due
```

---

## Error handling

| Error                              | Behavior                                      |
|------------------------------------|-----------------------------------------------|
| MCP not connected for a surface    | Skip that surface; log; continue with others  |
| Rate limit on a surface            | Pause 5s, retry once; then skip + log         |
| Malformed message/doc              | Skip item; log; continue                      |
| Disk write failure                 | Halt; do NOT advance cursor; report error     |
| `project-state/` not found        | Fail fast — wrong working directory (file binding) |
| Configured deposit adapter unreachable | Retry once; then stop and report. Cursor unchanged. Do NOT write local files instead |
| Deposit adapter rejects the write  | Stop; report authorization problem; nothing written |

---

## What this skill does NOT do

- Does not classify or promote docs — that's `project-document-curator`
- Does not send or modify anything on any surface — read-only
- Harvests GitHub as a first-class surface (Step 5e) — commits (digested per repo/day), PRs, releases, issues for the watched repos. (This supersedes the earlier "GitHub lives only in work-state" stance; work-state remains the raw event store, project-harvester is the project-scoped lens.)
- Does not run sentiment analysis — that's downstream
- Does not replace the work-state harvesters — it's a project-scoped lens on the same surfaces
