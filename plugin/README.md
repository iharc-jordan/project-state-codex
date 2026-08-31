# Project State payload for Codex

This directory contains the Project State runtime payload loaded by the Codex
manifest at `../.codex-plugin/plugin.json`.

Project State is a local-first operational substrate for multi-stakeholder
projects. Its 43 skills turn routine reporting into a byproduct of maintaining
shared objectives, milestones, decisions, risks, phases, stakeholders,
compliance evidence, and report provenance.

## Contents

- `skills/`: 43 Codex-discoverable skill entrypoints.
- `packs/`: eight swappable compliance and operating packs.
- `capabilities/`: SR&ED and tender-intelligence capability definitions.
- `templates/`: the preserved scaffolder and reporting templates.
- `CODEX.md`: the shared Codex ownership, routing, authorization, and
  compatibility policy read by every skill.

## Runtime model

The checked-in `project-state/` or `grant-state/` directory is the shared source
of truth for durable project facts. Reports are derived views. Personal
preferences remain in Codex Memories, repository execution rules remain in
`AGENTS.md`, temporary progress remains in the active Codex task or Goal, and
individual engineering work items remain in the configured issue tracker.

All external sends, issue creation, deployment, and repository mutations require
the authorization defined in `CODEX.md`. Unconfigured optional surfaces remain
inactive.

Installation, branch policy, compatibility details, and the complete adaptation
matrix are documented in the repository-level [README](../README.md) and
[CODEX-ADAPTATION.md](../CODEX-ADAPTATION.md).
