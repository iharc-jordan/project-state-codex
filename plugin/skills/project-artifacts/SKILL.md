---
name: project-artifacts
description: "Show a project as a Claude artifact — 'make me a snapshot of the project', 'refresh my snapshot', 'publish the project as an artifact'. Records a read-only page from the local folder; publishes it privately."
map:
  tier: P2
  stage: generate
  requires: [memory, shell, local-fs]
  reads: [manifest, state, milestones, objectives, risks, decisions, documents, references, log, reporting-matrix]
  delivers: [artifact, chat]
---

# Project Artifacts (a project's screens as a private Claude artifact)

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Turn a project that lives on this computer into a Claude artifact: the Project State Console
> (Today, milestones, calendar, risks and decisions, goals, reporting, the capability glances, the
> wiki and the file drawer) filled with the project's data, published privately to the person's
> claude.ai account. Trigger on 'make me a snapshot of the project', 'show the project as an
> artifact', 'publish the project state console for me', 'refresh my snapshot', 'update the
> artifact', 'which snapshots do I have', 'where is my project artifact'. Reads only: nothing in the
> project changes. Trigger: /project-artifacts [make|refresh|list] [project]

## Why a snapshot

A Claude artifact reaches data three ways: the **Project State connector** (cloud projects), a
**host bridge** to the local server (`host:` in the page's capabilities), or data **inside the
page**. The host bridge is refused from Code sessions on at least one account ("host servers
aren't available in this session"; `docs/CLOUD-STATUS-AND-GAPS.md`, S0a), and a folder on disk has
no connector. So this skill uses the third: the recorder starts the plugin's local project-state
server over the folder, read-only, makes every read the Console's screens make, and writes the page
with the answers inside (`window.PS_SNAPSHOT`). The page declares no capabilities, so there is
nothing for the artifact service to refuse, and it opens anywhere the person is signed in.

What that means for the person, said plainly when you hand them the link:
- **It is a picture, not a window.** The page is as current as the moment it was recorded; its
  status bar says when. "Refresh my snapshot" records again and republishes to the **same URL**.
- **It is read-only.** Buttons that would change something say to ask Claude; make the change
  through the other skills, then refresh.
- **It is private.** Only the person who published it can open it until they share it from
  claude.ai. It holds the project's data: sharing it shares that data.

## What it needs

- **The local server's plugin (v5.3 or later)** — the recorder ships beside it, at
  `<this skill>/../../server/state-snapshot.mjs`, with the page it fills at
  `<this skill>/../../server/artifacts/project-state.html`. The recorder finds both by itself.
- **Node 20.10 or later**, the same as the local server.
- **The Artifact tool** — Claude Code in the desktop app or a terminal signed in to claude.ai.
  Without it, say so and stop: the recorded page is still on disk, and the person can open it in a
  browser, but do not publish it anywhere else.

## Flow

### 1. Find the folder

Call `project_list` (the local server's tool). Each row names the project and its `folder`. Use the
project the person named, else the session's own (the first row). A project whose `home` is `cloud`
already has live pages through the Project State connector: say so, and snapshot it only if the
person still wants a picture of the local copy.

If the local server is not connected, the recorder finds the nearest `project-state/` above the
working directory by itself; pass `--root` only when the person named a different folder.

### 2. Record

```bash
node "<this skill>/../../server/state-snapshot.mjs" --root "<folder>" --out "<scratchpad>/snapshot-<project>.html"
```

- `--out`: into the session's **scratchpad directory** when the system prompt lists one (the
  Artifact tool publishes from there without questions). Without one, leave `--out` off: the
  default is `~/.project-state/snapshots/<name>.html`. **Never write a snapshot inside a
  repository**, and never commit one — it is the project's data in a single file.
- The recorder prints the file, the title, how many reads it captured, its size, and one of:
  - `artifact: <url> (republish to this URL)` — this folder was published before: go to step 3 as a
    **refresh**;
  - `artifact: none yet` — a first publish.
- Over 15.5 MB it leaves the file drawer out by itself and says so (`trimmed:`); `--lean` does the
  same on purpose. A `missing:` line names reads that failed; those spots say "not in this snapshot"
  on the page. Mention either in one line; neither stops the publish.

### 3. Publish

- **First publish:** the Artifact tool with the recorded file as `file_path`, **no
  `capabilities`**, `icon: "dashboard"`, and a one-sentence `description` such as "Northline's
  Project State Console, recorded from ~/work/northline/project-state on 2026-09-28." Then remember
  the URL for the next refresh:
  ```bash
  node "<this skill>/../../server/state-snapshot.mjs" --root "<folder>" --remember "<artifact url>"
  ```
- **Refresh:** the same call with `url: "<the remembered url>"` and the new file, so the link the
  person has (and anyone they shared it with) shows the new picture. No `icon` on a republish. If
  the tool says the artifact changed or asks for a read first, read it (`action: "read"`), then
  publish the new recording — the recording replaces the page wholesale; there is nothing to merge.
  If the remembered URL no longer opens (deleted), publish fresh and `--remember` the new URL.

Give the person the link, when it was recorded, and the one-line reminder that it is a picture to
refresh, not a live view.

### 4. List

"Which snapshots do I have":

```bash
node "<this skill>/../../server/state-snapshot.mjs" --list
```

prints each folder, its page title, the artifact URL and when it was last recorded.

## Rules

- **Reads only.** The recorder runs the server with `PROJECT_STATE_READ_ONLY=1`; nothing in the
  project is written, logged or signed. This skill never calls a write tool.
- **Private by default.** Publish without sharing; the person shares from claude.ai if they want to.
- **One person's index.** Snapshot URLs live in `~/.project-state/snapshots/index.json`, not in the
  project's manifest: an artifact belongs to the person who published it, and a teammate cannot
  open it, so it is not project state.
- **No capabilities on the page.** A snapshot needs none; adding `mcp` or `host:` entries is what
  gets a page refused.
- **Never commit a snapshot** and never write one inside a repository.

## Not this skill

- Live pages for **cloud** projects (read and edited through the Project State connector): the
  artifact pages in `artifacts/project-state-views/` are published once, with the connector
  declared, and read live.
- The **kanban** (`/project-kanban`): the full local app, live and editable, on this machine.
- Documents for other people (`/project-onepager`, `/project-status-reporter`): a snapshot is the
  app's screens, not a written report.
