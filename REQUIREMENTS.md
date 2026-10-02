# Project State for Codex decisions

Only later explicit direction from Jordan supersedes these scoped decisions.

## Standard releases and one maintained branch
- Date: 2026-09-30.
- Source: Jordan, this conversation: "It should just be a standard version number" and "not have random naming conventions or feature branches"; the subsequently approved implementation plan specifies `5.5.0`, `v5.5.0`, and `main`.
- Scope: This Codex adaptation, its package metadata, active release instructions, release tags, and distribution.
- Decision: Use ordinary `X.Y.Z` semantic versions and `vX.Y.Z` release tags. Maintain `main` as the sole branch. Record upstream provenance separately from the package version. Preserve historical commits and tags; remove `codex.lean.N` from active release conventions.

## Codex adaptation and existing project compatibility
- Date: 2026-09-30.
- Source: Jordan, this conversation, explicit approval of the "Update Project State for Codex to 5.5.0" implementation plan.
- Scope: The plugin upgrade and subsequent operation of its adapted workflows.
- Decision: Reuse upstream components with Codex-native host integration. Preserve existing facilities, unknown fields, activity history, operator schedules, attribution, and licensing. Installation does not enable project capabilities, create recurring jobs, migrate facilities, or publish project data. Honor the selected model and reasoning settings; do not change global configuration or introduce custom agent orchestration infrastructure.
