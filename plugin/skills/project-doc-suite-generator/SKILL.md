---
name: project-doc-suite-generator
description: "Deprecated compatibility alias. Forward any legacy baseline-report, Office-bundle, tracker-workbook, or project-doc-suite-generator request to project-doc-suite exactly once. This alias never generates files itself; the canonical output is the unified suite."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Doc Suite Generator — forwarding alias

This entrypoint exists only to preserve the public skill name. Pass the caller's
request and context to `project-doc-suite` once, then stop. Do not recreate the
unbundled v2 script, emit a second outbox card, or write the retired
`reports/baseline/Baseline-Reports-YYYY-MM-DD/` tree.

The canonical owner and output are:

- skill: `project-doc-suite`
- path: `project-state/reports/unified-suite/YYYY-MM-DD/`
- mutation boundary: the suite writes its derived bundle, then logs canonical
  pointers and activity through `project-state`
