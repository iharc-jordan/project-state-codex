---
name: project-git
description: "Deliberate Git checkpointing and team synchronization for Project State facilities. Use for checkpoint, push, sync, status, sharing, or end-of-session requests when the facility is Git-backed. Never fetch, pull, commit, or push automatically; compare only locally known refs until the operator authorizes a Git action, and require explicit resolution when two clones edit the same entity."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Git

## Purpose

Strategic git checkpointing for `project-state/` facilities. Git is not in the
write path. Material implementation-linked state normally travels in the same
branch/PR and protected/default-branch merge as the companion code. State-only
checkpoints remain legitimate for meetings, decisions, reports, governance, and
post-commit evidence when linked to their reason or revision.

The append-only ledger and file-per-entity schema reduce conflict frequency, but
they do not coordinate separate clones. Advisory lockfiles work only for writers
sharing one filesystem or server-backed substrate. Two clones that edit the same
entity still require an explicit Git conflict resolution.

## Session synchronization warning

At the first Project State operation in a session, if an upstream branch is
configured, compare `HEAD` with the locally known upstream ref using read-only Git
state (for example, `git status --short --branch` and
`git rev-list --left-right --count HEAD...@{upstream}`). Warn once if the branch
is known to be behind or diverged. This check must not fetch or otherwise contact
the remote, so it may be stale; say that plainly. Never auto-fetch, pull, commit,
or push.

## Finding the repo root

Walk up from `project-state/` to find `.git`. That directory is the git root. All git commands run from there. If no `.git` is found, report clearly: "This facility is not in a git repository. Run `git init` in the parent directory to enable checkpointing."

## Sub-actions

---

### `checkpoint [--include <path> ...]` (default)

Commit local facility changes with an auto-generated message. When the operator
explicitly supplies companion implementation paths, stage exactly those paths
plus the related `project-state/` changes. Do not force an implementation-linked
fact into a separate state-only commit.

**Steps:**

1. Find the git root (walk up from `project-state/`).
2. Run `git status --short` to see what has changed. If nothing, report "Nothing to checkpoint — working tree is clean." and stop. Resolve each
   `--include` path against the repository and show the exact staging set.
3. Run the Project State validation/reconciliation dry-run. Refuse the checkpoint
   on parse/schema errors, duplicate deterministic event IDs, or unresolved
   incompatible same-entity edits. Report locally known behind/diverged state;
   do not contact the remote.
4. Read the bounded tail of `project-state/logs/activity.ndjson` — the events since the last commit. To find events since last commit:
   ```bash
   git log -1 --format="%H %aI" HEAD   # get last commit hash + timestamp
   # filter activity.ndjson for events with ts > last commit timestamp
   ```
   If no prior commits exist, read the last 20 lines of the activity log.
5. Build the commit message from the activity log events:
   ```
   project-state: <one-line summary>

   <detail lines — one per distinct event type, consolidated>

   Facility: <project short name from manifest.yaml:project.name>
   ```
   Summary rules:
   - If only one event type: name it directly. "milestone.updated M03 → 45%"
   - If 2–4 event types: list them. "milestone.updated, 2 decisions recorded, inbox triage"
   - If 5+ event types: summarize by count. "12 events — milestones, decisions, documents"
   - Always lead with the most significant event (completions > updates > reads)
6. Run one of:
   ```bash
   # Deliberate state-only governance/reporting checkpoint
   git add project-state/

   # Implementation-linked checkpoint; paths were explicitly selected
   git add project-state/ <path> [<path> ...]

   git commit -m "<generated message>"
   ```
7. Report what was committed: file count, event summary, commit hash (short),
   and whether it was state-only or implementation-linked.

**Example output:**
```
Checkpoint complete — 7 files committed (a3f2c1d)

  project-state: M03 complete, 2 decisions recorded, SC meeting scheduled

  Files changed:
    milestones/M03-data-pipeline.yaml    (updated — status: complete)
    decisions/2026-05-12-hire-acme.yaml  (new)
    decisions/2026-05-12-swap-infra.yaml (new)
    reports/sc-meetings/2026-Q2-02.yaml  (new)
    logs/activity.ndjson                 (4 events appended)
    documents/index.yaml                 (2 entries extended)
    state.json                           (counters updated)
```

---

### `push`

Share committed checkpoints with the team.

**Steps:**

1. Find the git root.
2. Check that a remote exists: `git remote -v`. If none, report "No remote configured. Add one with: `git remote add origin <url>`" and stop.
3. Check for unpushed commits: `git log @{u}..HEAD --oneline`. If none, report "Nothing to push — already up to date with remote."
4. Run `git push`.
5. On success: report how many commits were pushed and the commit range.
6. On failure (remote has new commits): report "Remote has changes you don't have locally. Run `project-git sync` first, then push."

---

### `sync`

Pull teammates' changes into the local facility after explicit invocation.
Append-only files reduce conflicts but do not make the operation semantically
safe by themselves.

**Steps:**

1. Find the git root.
2. Check for a remote: `git remote -v`. If none, report "No remote configured." and stop.
3. Check for uncommitted local changes: `git status --short`. If any exist, warn:
   "You have uncommitted local changes. Checkpoint or otherwise preserve them
   before syncing." Stop unless the operator explicitly chooses to continue.
4. Run `git pull --rebase`.
5. On clean success: report what came in — commits received, files changed, and any new activity log events from teammates (read the new NDJSON lines appended from remote).
6. On rebase conflict, report exactly which file conflicted and what both sides
   changed. Never choose a same-entity winner automatically; show both versions
   and require explicit resolution.

**Example output (clean sync):**
```
Synced — 3 commits received from origin/main

  Karen's changes:
    milestone.updated: M02 → 60% (was 45%)
    decision.recorded: 2026-05-11-platform-choice
    risk.opened: R-12-vendor-dependency

  2 new milestones updated, 1 new decision, 1 new risk.
  Your local state is now current.
```

---

### `status`

Show what has changed locally since the last commit, and what's in the activity log that hasn't been checkpointed yet.

**Steps:**

1. Find the git root.
2. Run `git status --short` and `git diff --stat HEAD`.
3. Read activity log events since last commit timestamp (same method as checkpoint step 3).
4. Run `git log --oneline -5` to show recent checkpoint history.

**Output format:**
```
Facility: project-state (project-state/)
Last checkpoint: 2026-05-12 09:30 — "M01 complete, plugin packaged" (a3f2c1d)

Uncommitted changes (4 files):
  M  milestones/M03-data-pipeline.yaml
  M  logs/activity.ndjson
  A  decisions/2026-05-12-hire-acme.yaml
  A  risks/R-12-vendor-dependency.yaml

Activity since last checkpoint (3 events):
  09:45  milestone.updated   M03 → 55%
  10:12  decision.recorded   2026-05-12-hire-acme
  10:30  risk.opened         R-12-vendor-dependency

Recent checkpoints:
  a3f2c1d  M01 complete, plugin packaged
  b2e1f0c  M02 updated, SC meeting minutes filed
  c4d9a8b  Inbox triage — 6 documents processed

→ Run `project-git checkpoint` to commit these changes.
```

---

### `log`

Show recent checkpoint history with activity summaries.

**Steps:**

1. Run `git log --oneline -10` from the git root.
2. For each commit, parse the commit message summary line.
3. Display as a clean list with relative timestamps.

---

## Commit message format

All auto-generated commit messages follow this structure:

```
project-state: <one-line summary under 72 chars>

<detail lines — one per event group>

Facility: <project.name from manifest.yaml>
```

Event group consolidation rules:
- Multiple `milestone.updated` events → "N milestones updated (M01, M03, M07)"
- Multiple `decision.recorded` events → "N decisions recorded"
- `milestone.completed` always called out explicitly — never collapsed
- `phase.transition` always called out explicitly
- `inbox.triage.*` events → "inbox triage — N documents processed"
- `report.generated` → "report generated: <id>"

The message is generated from the activity log, not from git diff. The activity log has the semantic meaning; git diff has the file changes. Both are in the commit.

---

## .gitattributes — set once at scaffold time

The scaffolder (`project-scaffolder`) should write this to the repo root at facility creation. If not present, `project-git sync` adds it automatically before the first pull:

```
# project-state git merge configuration
# Append-only logs: retain distinct lines from both sides for later validation
project-state/logs/*.ndjson merge=union
```

This lets Git retain lines from both sides when teammates append distinct activity
events. It does not resolve duplicate or contradictory semantic events, and it
does not apply to two edits of the same canonical entity; validate the merged log
and resolve those cases explicitly.

The protected/default-branch merge is the serialization point for separate Git
clones. Before accepting merged state, detect stale base revisions where known,
duplicate deterministic event IDs, and incompatible edits to the same entity.
Require explicit human resolution. Do not claim that `merge=union` means
"merge equals union," do not use lockfiles as cross-clone coordination, and do
not create a parallel state-change request ledger.

---

## When to checkpoint

This skill is called deliberately. Suggested moments:

- **End of a work session** — "checkpoint the project, end of day"
- **Before a review meeting** — "checkpoint and push before the SC meeting"
- **After a milestone completion** — `milestone.completed` events always worth a dedicated checkpoint
- **After a phase transition** — ditto
- **Before running an external report** — so the report reflects committed state
- **Before syncing** — protect local work before pulling teammates' changes

Never checkpoint automatically. The user decides when their work is ready to be recorded.

---

## Reads

- `project-state/logs/activity.ndjson` — to generate commit messages
- `project-state/manifest.yaml` — for facility name in commit message
- `git log`, `git status`, `git diff` — for status and checkpoint history

## Writes

- Nothing to `project-state/` — this skill does not modify facility data
- Git commits and pushes only

## Called by

- User directly
- `project-orchestrator` (may suggest checkpoint at end of session)

## Calls

- `project-state` — to read manifest and validate facility before git operations
