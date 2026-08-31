---
name: project-admin
description: "Manage project-state projects in the local-first + GitHub-hub model. Sub-actions: create (scaffold a new project-state substrate, create its private GitHub state repo, push, and register it in the Vercel viewer's GITHUB_STATE_REPOS map), pull (clone an existing project's state repo to a local working copy), list (show registered projects from the viewer registry). Use when the user says 'create a new project', 'new project-state', 'pull down project X', 'clone the state for X', 'check out a project', 'list projects', 'what projects exist', 'register a project with the dashboard', or any request to create, fetch, or enumerate project-state projects. Members and roles are managed via GitHub repo permissions, not here."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Admin

Manage project-state **projects** in the local-first model: local substrate is
authoritative, a per-project GitHub repo is the hub, and the Vercel viewer reads
the repos listed in its `GITHUB_STATE_REPOS` env var.

**Members/roles are NOT managed here** — they are GitHub repo permissions
(collaborators / org teams). To add an editor, grant them `write` on the state
repo; to add a viewer, share the dashboard URL + a view token.

## Conventions

- A project `org/name` (e.g. `worksona/q3-fun`) maps to one **private GitHub
  state repo** (e.g. `worksona/q3-fun-state`).
- The repo holds the substrate at `project-state/` in its root.
- The Vercel viewer (project `kanban`, team `atomic47`) reads the map env var
  `GITHUB_STATE_REPOS` = `{"<org>/<name>": "<owner>/<repo>", ...}`.

## Finding the Vercel token / team / project

```bash
TOK=$(cat "$HOME/Library/Application Support/com.vercel.cli/auth.json" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
TEAM=team_erg4sFyoOjgPXtD2EtTaCKqR   # atomic47
PROJECT=kanban
```
Require `gh` authenticated with `repo` scope for repo create/clone/collaborators.

---

## `create`

Create a new project end to end.

1. Confirm `org`, `name`, and compliance `pack` with the user. Derive the state
   repo name (default `<name>-state`, owner = the GitHub org).
2. Scaffold the substrate locally by invoking **`project-scaffolder`** in the
   target directory — it creates `project-state/` with the chosen pack.
3. Create the private repo and push:
   ```bash
   gh repo create <owner>/<repo> --private --description "project-state: <org>/<name>"
   cd <project-dir>
   git init -b main 2>/dev/null || git checkout -B main
   git add project-state && git commit -m "Initialize <org>/<name> substrate"
   git remote add origin "https://github.com/<owner>/<repo>.git" 2>/dev/null || git remote set-url origin "https://github.com/<owner>/<repo>.git"
   git push -u origin main
   ```
4. Register it in the viewer's `GITHUB_STATE_REPOS` (read → merge key → upsert):
   read the current value from Vercel, add `"<org>/<name>": "<owner>/<repo>"`,
   and PATCH/upsert via `POST /v10/projects/$PROJECT/env?teamId=$TEAM&upsert=true`
   with `{key:"GITHUB_STATE_REPOS", value:<merged json>, type:"encrypted", target:["production","preview","development"]}`.
5. Report the dashboard URL: `https://kanban-atomic47.vercel.app/dash/<org>/<name>/kanban`.
6. **Launch the project context page automatically** — no manual navigation needed:
   ```bash
   # Start the local kanban on port 3355 if it isn't already running
   if ! lsof -ti tcp:3355 > /dev/null 2>&1; then
     KANBAN_DIR="$(pwd)/project-state/kanban"
     [ ! -d "$KANBAN_DIR/node_modules" ] && (cd "$KANBAN_DIR" && npm install)
     cd "$KANBAN_DIR" && npm run dev > /tmp/project-kanban.log 2>&1 &
     for i in $(seq 1 15); do lsof -ti tcp:3355 > /dev/null 2>&1 && break; sleep 1; done
   fi
   open http://localhost:3355/onboarding
   ```
   Print: `✓ <org>/<name> created. Opening the setup page — select your compliance packs and orient the project.`

---

## `pull`

Fetch an existing project's state to a local working copy (to edit locally).

1. Resolve the repo: from the argument, or look it up in `GITHUB_STATE_REPOS`
   (see `list`). If given `org/name`, map → `<owner>/<repo>`.
2. Clone it:
   ```bash
   gh repo clone <owner>/<repo> <dest-dir>
   ```
   The substrate is at `<dest-dir>/project-state/`. The user works there; the
   Stop hook / `project-git` skill commit+push changes back to the hub.
3. If they already have a local copy, prefer `project-git sync` (rebase-safe
   pull) instead of a fresh clone.
4. Report the local path and confirm `project-state/manifest.yaml` is present.

---

## `list`

Show the registered projects (the viewer's registry).

1. Read `GITHUB_STATE_REPOS` from Vercel:
   ```bash
   curl -s "https://api.vercel.com/v9/projects/$PROJECT/env?teamId=$TEAM&decrypt=true" \
     -H "Authorization: Bearer $TOK" | python3 -c "..."   # find key GITHUB_STATE_REPOS
   ```
2. Parse the JSON map and present a table: `org/name → owner/repo`, grouped by
   org. Optionally annotate each with its latest commit (`gh api repos/<repo>/commits --jq '.[0].commit.committer.date'`).
3. This is the source of truth for "what the dashboard shows." The read-only
   `/overview` page in the Vercel app renders the same data plus members.

---

## Reads
- `GITHUB_STATE_REPOS` (Vercel env) — the project registry
- GitHub repos via `gh`

## Writes
- New GitHub repos (`create`), local clones (`pull`)
- The `GITHUB_STATE_REPOS` Vercel env var (`create` registers a new project)
- Never edits members/permissions — that is GitHub-native

## Related
- `project-scaffolder` — creates the substrate (called by `create`)
- `project-git` — manual commit/push/sync; the Stop hook is the auto path
