---
name: project-doc-suite-generator
description: "⚠️ DEPRECATED in v3.0 — use project-doc-suite instead. project-doc-suite generates the same governance Office files plus a full software documentation suite, all from a unified context that reads both project-state/ and the live codebase. This skill will be removed in v3.1. If you are on v2.x and cannot upgrade, this skill still functions: generates index, tracker xlsx, project plan, risk register, milestone specs, architecture overview, and roadmap/KPIs from project-state/ only."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Doc Suite Generator

> ⚠️ **Deprecated in v3.0.** Use `project-doc-suite` instead.
>
> `project-doc-suite` merges `project-state/` substrate data with a live codebase scan, produces the same governance Office files enriched with technical context, adds unified strategic + technical documents (replacing the duplicate Architecture-Overview and Roadmap documents), and adds the full software insight suite — all in one non-overlapping bundle.
>
> **Migration:** replace any invocation of `project-doc-suite-generator` with `project-doc-suite`. The output path changes from `reports/baseline/Baseline-Reports-YYYY-MM-DD/` to `reports/unified-suite/YYYY-MM-DD/`. See `docs/UNIFIED-SUITE-V3.md`.

---

# Project Doc Suite Generator (v2 — legacy)

## Purpose

Produce a complete baseline report bundle — styled `.docx` and `.xlsx` files — from the structured state in `project-state/`. This is the rendering engine that turns YAML/JSON substrate data into professional Office documents matching the quality standard set by production projects (e.g., ai26.10).

**Design principle:** reports are views of state. The generator reads `project-state/`, renders styled documents, and writes them to `reports/baseline/`. If a report is wrong, the state was wrong — fix the state, regenerate.

## Trigger phrases

- "generate baseline reports" / "create the report bundle"
- "produce the docx outputs" / "build the tracker xlsx"
- "baseline report bundle" / "report bundle"
- "generate the office documents" / "create the baseline pack"
- "produce reports for [phase/milestone]"

## When to run

| Trigger | Who initiates |
|---------|---------------|
| Phase transition (via `project-phase-gate`) | Orchestrator or user |
| Milestone completion | Orchestrator or user |
| On demand | User |
| Orchestrator `baseline` routine | `project-orchestrator` |
| Reporting matrix entry (`baseline-report-bundle`) | Orchestrator tick |

## Output bundle

All files land in `project-state/reports/baseline/Baseline-Reports-YYYY-MM-DD/`:

| # | Document | Format | Contents |
|---|----------|--------|----------|
| 00 | Baseline-Reports-Index | .docx | Cover page, table of contents, version history |
| 01 | Project-Tracker-v1.0 | .xlsx | 8+ sheets: Home, Dashboard, Milestones, Deliverables, Risks, Phases, Monthly Gantt, Dependencies, Legend |
| 02 | Project-Plan-and-Timeline | .docx | Phases, milestone summary table, timeline, critical path, surfaces |
| 03 | Risk-Register | .docx | Scoring matrix, summary table, top-3, individual risk entries with description/mitigation/contingency |
| 04 | Milestone-Detailed-Specs | .docx | Per-milestone: metadata, description, technical progress, deliverables table |
| 05 | Architecture-Overview | .docx | Three-layer architecture, skill inventory, pack system, concurrency model, reporting matrix |
| 06 | Roadmap-and-KPIs | .docx | Roadmap phases, KPI table, success criteria, pack maturity targets |

## Implementation

### Dependencies

- `python-docx` — Word document generation with styled tables, headings, fonts
- `openpyxl` — Excel workbook generation with styled sheets, conditional formatting, color fills

### Rendering script

The canonical generator lives at `scripts/generate-baseline-reports.py`. This skill invokes it:

```bash
python3 scripts/generate-baseline-reports.py [--date YYYY-MM-DD] [--output-dir path]
```

Default date is today. Default output is `project-state/reports/baseline/Baseline-Reports-YYYY-MM-DD/`.

### Document styling standard

All documents follow a consistent visual language:

**DOCX styling:**
- Font: Calibri, 10pt body, headings in navy (#1B2A4A)
- Tables: navy header row with white text, alternating light gray (#F0F4F8) rows, thin gray (#BDC3C7) borders
- Bold field labels inline (e.g., **Status:** complete)
- No images or charts — data tables and text only

**XLSX styling:**
- Sheet tab colors: navy (Home/Phases/Dependencies), accent blue (Dashboard/Gantt), green (Milestones/Deliverables), red (Risks), gray (Legend)
- Header row: navy fill, white bold Calibri 10pt
- Data rows: alternating white/light blue, thin gray borders, wrap text
- Status cells: color-coded fills (green=complete, amber=in_progress, red=at_risk/critical)
- Monthly Gantt: colored cells for active milestone months

### Website integration

After generating, the skill:
1. Copies the bundle to `project-state/website/public/downloads/baseline/` for static serving
2. Updates the website reports page with download links
3. Logs a `report.generated` event to `logs/activity.ndjson`

### Pack awareness

The generator reads `manifest.yaml:project` for project identity and `manifest.yaml:packs_loaded` for context. Pack-specific documents (e.g., PIC claim forms, SC agenda templates) are NOT produced by this skill — those belong to `project-funder-reporting` and `project-review-meeting`. This skill produces the generic baseline bundle that every project needs.

## Data sources

| Data | Source file | Used in |
|------|-------------|---------|
| Project identity | `manifest.yaml` | All documents |
| Current phase | `state.json` | All documents |
| Milestones | `milestones/*.yaml` | Tracker, Plan, Specs |
| Risks | `risks/*.yaml` | Tracker, Risk Register |
| Phases | `phases/*/manifest.yaml` | Tracker, Plan |
| Deliverables | `milestones/*.yaml:deliverables[]` | Tracker, Specs |
| Decisions | `decisions/*.yaml` | Index (count only) |
| Reporting matrix | `reporting-matrix.yaml` | Architecture doc |

## Integration

- **project-state** — reads all substrate data through the memory layer
- **project-orchestrator** — triggers this skill at phase transitions and on the `baseline` routine
- **project-phase-gate** — triggers regeneration after a successful phase transition
- **project-website-publisher** — downstream consumer; serves the generated files as static downloads
- **project-notifier** — can route "baseline reports ready" notification to Slack/Gmail
- **outbox** — emits a `doc` card (cover note) into `outbox/queue/` after each bundle
- **project-status-reporter** — shares the same docx rendering primitives for SC packs and final reports

## Outbox emission (queue the bundle for review)

After writing the baseline bundle to `reports/baseline/Baseline-Reports-YYYY-MM-DD/`,
emit an outbox card into `project-state/outbox/queue/` so the bundle surfaces in the
`/queue` UI (contract: `docs/OUTBOX.md`), always `status: queued`. The bundle is many
`.docx`/`.xlsx` files, so the card's artifact is a short **markdown cover note** that
lists the files and links the directory — not the binaries themselves.

- `kind: doc`, `surface: none` (the bundle is downloaded/distributed, not auto-sent).
- `action_required:` "Review the baseline bundle; download from Reports or distribute
  via notifier."
- Reference the bundle directory in the cover note so the reviewer can open it.

```yaml
id: 2026-05-22-baseline-bundle
kind: doc
title: "Baseline report bundle — 2026-05-22"
produced_by: project-doc-suite-generator
produced_at: 2026-05-22T06:00:00Z
status: queued
surface: none
action_required: "Review the baseline bundle (7 files under reports/baseline/Baseline-Reports-2026-05-22/)."
artifact: 2026-05-22-baseline-bundle.md
```

Emission never sends or distributes — it only queues the cover note for review.

## Discipline

- **Never invent data.** Every number in a report traces to a file in `project-state/`.
- **Idempotent.** Running twice on the same date overwrites the same directory — no duplicate bundles.
- **Dated directories.** Each bundle is self-contained in `Baseline-Reports-YYYY-MM-DD/` for audit trail.
- **No auto-send.** Files are generated locally. Distribution is the user's (or notifier's) job.
