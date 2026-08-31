---
name: project-admin
description: "Manage Project State projects in a local-first, optional GitHub-hub model. Create can scaffold locally and, with explicit authorization, create and push a private state repository; pull clones an authorized state repository; list reports locally known or explicitly configured projects. Register with an external viewer only when the operator supplies that viewer configuration and requests registration. Never assume access to Atomic47's private infrastructure."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Admin

> **Public-package boundary:** the Atomic47 keep-state-app viewer is not bundled,
> and no internal team, project, token, or dashboard URL is assumed. Local
> scaffolding works independently. GitHub repository creation/push and optional
> viewer registration require explicit operator authorization and supplied scope.

Manage project-state **projects** in the local-first model: local substrate is
authoritative, an optional per-project GitHub repo is the hub, and a configured
viewer may read the repos listed in its `GITHUB_STATE_REPOS` environment variable.

**Members/roles are NOT managed here** — they are GitHub repo permissions
(collaborators / org teams). To add an editor, grant them `write` on the state
repo; to add a viewer, share the dashboard URL + a view token.

## Conventions

- A project `org/name` maps to one **private GitHub state repo** by convention
  (for example, `org/project-state`).
- The repo holds the substrate at `project-state/` in its root.
- An optional configured viewer may read the map environment variable
  `GITHUB_STATE_REPOS` = `{"<org>/<name>": "<owner>/<repo>", ...}`.

## Optional provider prerequisites

Require an authenticated `gh` session with appropriate repository scope before
GitHub operations. For viewer registration, require an operator-supplied team,
project, and an already authenticated provider CLI/session. Never scrape, print,
or copy a bearer token from a local authentication file.

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
4. Only when the operator explicitly requests it and supplies an authorized
   viewer, register it in that viewer's `GITHUB_STATE_REPOS` (read → merge key → upsert):
   read the current value from Vercel, add `"<org>/<name>": "<owner>/<repo>"`,
   and use the authenticated provider CLI or API for the supplied project/team
   with `{key:"GITHUB_STATE_REPOS", value:<merged json>, type:"encrypted", target:["production","preview","development"]}`.
5. Report the local path, repository URL, and viewer URL only when each exists.
   Do not launch a kanban app unless the operator supplies an existing checkout;
   it is not part of this public package.

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
   The `project-git` skill can commit and push later changes back to the hub.
3. If they already have a local copy, prefer `project-git sync` (rebase-safe
   pull) instead of a fresh clone.
4. Report the local path and confirm `project-state/manifest.yaml` is present.

---

## `list`

Show the registered projects (the viewer's registry).

1. If an authorized viewer is configured, read its `GITHUB_STATE_REPOS` value
   through the authenticated provider CLI/API. Otherwise list locally known
   checkouts or repositories the operator explicitly names; do not probe
   Atomic47 infrastructure.
2. Parse the JSON map and present a table: `org/name → owner/repo`, grouped by
   org. Optionally annotate each with its latest commit (`gh api repos/<repo>/commits --jq '.[0].commit.committer.date'`).
3. For a configured viewer, this map is the source of truth for what it shows.

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
