# Codex adapter

This adapter applies to Atomic 47 Labs Project State v4.9.0 from public commit
`c0b55ba52dfdca9312a1f6150039ed14d569e2db`.

- Resolve bundled `packs/`, `templates/`, and `capabilities/` paths from this
  `plugin/` directory, not from the operator's project. From a normal skill
  directory the plugin payload is `../..`; from
  `skills/project-inbox/project-intake/` it is `../../..`. Resolve a script or
  reference stored inside the active skill from that skill's own directory.
- Use regular Markdown and conversation output in Codex. Claude artifact,
  Coworker, and interactive-HTML presentation mechanics are not executable
  Codex surfaces. Preserve their substantive data and approval rules without
  claiming live artifacts or clickable HTML controls.
- Use only tools and connectors actually available in the current Codex host.
  Discover matching tools at runtime and report a configured surface as
  unavailable when its connector is absent. Do not install or connect a service
  unless the operator requests it.
- Translate shell examples to the current operating system and shell. On
  Windows, use PowerShell or cross-platform Python instead of macOS `open`,
  Unix-only paths, or `crontab`.
- Obtain explicit operator authorization before external sends, posts, issue
  creation, deployments, repository mutations, or similar external effects.
  Stricter draft-only rules in individual skills remain in force.
- The public archive does not include its private design documents,
  keep-state-app/project-kanban desktop app, deposit backend, or upstream
  auto-updater. Do not invent missing specifications or claim those optional
  surfaces work. The skill instructions and bundled files are authoritative for
  workflows that are present.
- Bundled scripts do not run on install. Inspect prerequisites and run them only
  when the selected workflow requires them.
