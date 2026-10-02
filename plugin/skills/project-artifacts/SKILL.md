---
name: project-artifacts
description: Create, refresh, or list a local read-only HTML snapshot of a configured project. Use for project snapshot, console, or artifact requests. Project files remain unchanged.
---

# Project snapshots

Read [CODEX.md](../../CODEX.md) once per active task. Use the upstream recorder and HTML renderer bundled under server/; no cloud publishing account or artifact service is required.

## Make or refresh

1. Call the available project_list tool. Select the named local project and its folder. If no server serves the project, locate its explicitly supplied project-state/manifest.yaml. Ask only when the target remains ambiguous. A cloud project needs its configured connector; never substitute an unrelated local copy.
2. Run `node <plugin>/server/state-snapshot.mjs make --root <state-folder>` (use refresh for a refresh). Resolve <plugin> from this skill's ../.., not the project. The recorder launches the checked local server in read-only mode and does not alter the facility.
3. The default file and index live under the operator's ~/.project-state/snapshots/. Refresh reuses the indexed file. An explicit --out and --index may isolate a test or choose another location; both must stay outside repositories. --summary omits the detailed file drawer when requested. Preserve legacy index fields and never publish its old URLs.
4. Preview the output using a task-owned standard static server: `python -m http.server 0 --bind 127.0.0.1 --directory <snapshot-directory>`. Read the assigned port from its output; open http://127.0.0.1:<port>/<encoded-filename> in the Codex browser panel. The root agent inspects the settled rendered content, tabs and read-only controls. Keep the file available and stop the task-owned preview process when it is no longer needed.
5. Return a clickable absolute path to the HTML and the captured timestamp. Disclose any missing reads reported by the recorder. A snapshot reflects that capture, and its controls ask Codex to make changes or refresh; they do not perform writes.

## List

Run `node <plugin>/server/state-snapshot.mjs list`. Show only the recorded project, file and timestamp; do not enumerate or scan projects that were not selected or configured.

Snapshots contain project data. External sharing or publishing is a separate explicitly requested operation using an available destination. Never commit a snapshot, activate a capability, create a recurring job, or modify project state as part of recording or listing it.
