# Codex adaptation 5.5.0

This release incorporates Atomic 47 Labs Project State 5.5.0 at
`a21f28270027b031ec718ebe44dc0fb283be50eb`. Upstream provenance is in
[upstream.json](./upstream.json); Codex package versions are ordinary semantic
versions, independent of the upstream baseline. The existing Git history and
historical tags are retained. Only `main` is maintained.

The bundled domain engine, schemas, capability modules, packs, and templates
remain upstream components. Codex changes concern host integration and concise
instructions:

- `.mcp.json` launches the bundled Node stdio server through a small installed-path adapter.
- Served projects use checked MCP tools. Generic entity and log calls are separate operations; a partial failure is reported and reconciled without duplicating an event.
- The state gateway shares deterministic event identity calculation with validation. Repeat suppression checks the existing canonical event or result before writing; raw `log_append` is not idempotent.
- Scheduling uses `automation/tasks.yaml` and Codex native automations. Explicit scheduling requests authorize their jobs; generated suggestions remain proposals.
- Research uses bounded native workers with inherited model and reasoning settings. The parent owns canonical writes and the final report.
- Artifact make, refresh, and list use the upstream recorder and renderer, a personal snapshot index, and local HTML previews outside project repositories.
- The compact host adapter is read once per task. Domain rules remain with the owning skills, with detailed references loaded when relevant.

Existing facilities are not migrated by installation. Unknown manifest fields,
optional absent `caches`, legacy Tender configuration, activity history, and
operator schedules remain supported. Capability migration runs only for an
explicit enable or update operation using bundled migration scripts. Disabling
a capability retains its data. Bundled capability availability does not imply
a paid entitlement or a configured connector.

Codex resolves the MCP `cwd: "."` against the installed plugin root but does
not supply its session workspace path to the server. `PROJECT_STATE_DIR` remains
the optional explicit local binding; unserved local projects retain filesystem
operation. No process inspection or custom workspace registry is introduced.
The snapshot adapter also fixes Windows line endings, UTF-8 declaration, and
null children in read-only views. Local reads no longer create an inbox or
finalize jobs while listing them.
Identical milestone status/progress updates return unchanged after the normal
staleness check, preserving the timestamp and activity log. The gateway compares
canonical final values before repeating other domain updates.

Current user direction and applicable requirements govern the task. Ordinary
authorized local work proceeds without repeated confirmation; external sends
and publication require authorization already supplied or obtained for that
action. Routine tasks do not scaffold facilities. Reporting keeps a single
owner and routes material shared facts to their canonical entities.

## Validation

Run the package validator and synthetic tests described in [README.md](./README.md).
The validator derives skills, packs, capability names, and required payload
paths from the pinned upstream tree, then checks parsing, references, and script
syntax. It does not require per-file rationale matrices or special commit headings.

Synthetic runtime checks exercise actual stdio MCP requests, attributed writes,
stale-hash refusal, read-only behavior, and preservation of legacy data. Release
verification also reviews a rendered synthetic snapshot and fresh Codex discovery.
Model behavior probes are bounded observations, not a guarantee for every task.
No real project writes, recurring jobs, or external messages are validation effects.

The shared adapter was reduced from 1,576 to 496 words and from 11,587 to 3,395
UTF-8 bytes compared with the previous release. These are instruction-size
measurements; they do not establish runtime token or latency savings.

Atomic47 authorship, repository attribution, and the MIT license are preserved.
This repository is an independent adaptation, not an official Atomic47 release.
