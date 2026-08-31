---
name: project-doc-suite
description: "Unified documentation suite generator. Merges project-state/ substrate (milestones, risks, phases, manifest, reporting matrix) with a live codebase scan to produce one non-overlapping report bundle. Replaces and supersedes project-doc-suite-generator (governance Office bundle) and doc-suite-generator-v2 (software markdown suite). Use whenever the user says 'generate docs', 'unified suite', 'report bundle', 'full documentation', 'document this project', 'build the suite', 'create the docs', or any request for structured project documentation. Also triggered by phase transitions, milestone completions, and the orchestrator baseline routine. See docs/UNIFIED-SUITE-V3.md for the full design."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Doc Suite

## Purpose

Produce a single, non-overlapping documentation bundle by reading from two source layers — the `project-state/` substrate (governance, milestones, risks, budget, funder context) and a live codebase scan (architecture, components, dependencies, technical readiness) — and merging them into a unified context object before any document is generated.

Every document in the output tree knows both layers. No document covers the same ground as another. The bundle replaces two previously separate suites that produced conflicting, partially-overlapping artifacts.

**Design principle:** two truths, one document tree. The substrate owns WHO, WHAT, and WHEN. The codebase scan owns HOW. A document is unified when it answers both.

## Trigger phrases

- "generate docs" / "build the docs" / "create the report bundle"
- "unified suite" / "full documentation suite"
- "document this project" / "generate the baseline pack"
- "report bundle" / "unified docs"
- "create the office documents + markdown docs"
- Any call from `project-orchestrator` via `baseline` routine or reporting matrix entry

## Output tree

All files land in `project-state/reports/unified-suite/YYYY-MM-DD/`.

| Band | File | Format | Description |
|------|------|--------|-------------|
| E | `00-suite-index.md` | .md | Cover + full document tree with one-line summaries. Replaces both the governance Index.docx and the software executive-summary.md. |
| A | `01-project-tracker.xlsx` | .xlsx | Milestone/risk/Gantt tracker, enriched with two new columns per milestone: **primary components** (which codebase modules deliver it) and **technical readiness score** (from scan). |
| B | `02-project-plan.docx` | .docx | Phases, timeline, critical path — plus a **Component Delivery Map** table (phase → components entering production). |
| B | `03-risk-register.docx` | .docx | Risk scoring matrix and entries — plus a **Technical Debt Risks** section auto-populated from scan readiness gaps. |
| B | `04-milestone-specs.docx` | .docx | Per-milestone metadata, progress, deliverables — plus a **Delivery Components** section per milestone. |
| C | `05-architecture-and-tech-spec.md` | .md | **UNIFIED** — replaces Architecture-Overview.docx + project-overview.md + technical-specification.md. System architecture from both the substrate three-layer model and the live codebase (components, API surface, dependencies, deployment). |
| C | `06-strategic-roadmap.md` | .md | **UNIFIED** — replaces Roadmap-and-KPIs.docx + business-benefits.md. Phase gates and KPIs (substrate) + business value analysis, target users, competitive advantages (scan). |
| D | `07-technical-readiness.md` | .md | 10-dimension readiness scoring. Flags which gaps directly threaten upcoming milestone completion criteria. |
| D | `08-innovation-themes.md` | .md | What's technically novel. Notes which innovations are funded deliverables vs. enabling infrastructure. |
| D | `09-extensibility.md` | .md | Plugin points, API surfaces, extension patterns. |
| D | `10-features-capabilities.md` | .md | Concrete feature inventory. |
| D | `11-work-zones.md` | .md | Thematic development work zones. |
| D | `12-portfolio-position.md` | .md | Portfolio context (multi-project runs only). |
| D | `13-worksona-themes.md` | .md | Leadership runbook alignment. |
| D | `14-worksona-first-principles.md` | .md | Structural principle alignment. |
| — | `README.md` (project root) | .md | Standardized root README updated in two passes (before and after Band C). |

## Generation pipeline

### Phase 0 — Context assembly (required before any document)

```
0.1  Read project-state/ via project-state skill
     → manifest.yaml (identity, budget, dates, funder, packs_loaded)
     → state.json (current phase, health, counters)
     → milestones/*.yaml
     → risks/*.yaml
     → phases/*/manifest.yaml
     → reporting-matrix.yaml

0.2  Run codebase scan (project-scanner from doc-suite-generator-v2 pipeline)
     → tech stack, architecture patterns, components, entry points
     → dependencies, API surface, config model, test coverage
     → deployment signals, code quality patterns, existing docs quality

0.3  Build cross-links
     → milestone_to_components: for each milestone, identify primary codebase modules
       (match milestone title/description keywords against component names/paths)
     → technical_risks: scan readiness gaps → candidate risk entries (R-NN format)
     → readiness_by_milestone: for each in-progress milestone, score its delivery components

0.4  Assemble unified_context object (see docs/UNIFIED-SUITE-V3.md for full schema)
```

Context assembly is the most important step. If the context is wrong, all documents are wrong. Check:
- `substrate.milestones` is non-empty — if zero milestones found, warn and pause
- `scan.components` is non-empty — if scan returns nothing useful, report and pause
- `cross_links.milestone_to_components` has at least one populated entry — if all milestones map to zero components, the match heuristic may need refinement; ask the user for guidance

### Phase 1 — README standardization (first pass)

Call `readme-standardizer` with:
- Project name and one-liner from `substrate.project`
- Tech stack from `scan.tech_stack`
- Current phase and health from `substrate.current_phase`

Write to project root `README.md`. Mark for second-pass enrichment after Phase 3.

### Phase 2 — Governance documents (enriched)

Use `python-docx` and `openpyxl`. These retain Office format because funder, finance rep, and SC audiences need it.

**2.1 — `01-project-tracker.xlsx`**
Build the standard 8-sheet tracker workbook (Home, Dashboard, Milestones, Deliverables, Risks, Phases, Monthly Gantt, Dependencies, Legend) as in v2, then:
- Add column `Primary Components` to the Milestones sheet — populated from `cross_links.milestone_to_components`
- Add column `Technical Readiness` to the Milestones sheet — numeric score from `cross_links.readiness_by_milestone`; color-coded green/amber/red
- Add a **Technical Debt** tile to the Dashboard sheet showing count of technical risks identified in Phase 0

**2.2 — `02-project-plan.docx`**
Standard phases and timeline content, then append a **Component Delivery Map** table:
| Phase | Components entering production | Readiness |

Populate from `cross_links.milestone_to_components` grouped by `substrate.phases`.

**2.3 — `03-risk-register.docx`**
Standard risk scoring and entries from `substrate.risks`. After the last entry, append a new section:

> **Technical Debt Risks (auto-detected)**
> The following risks were identified from the codebase scan. They are not yet in the formal risk register. Review and promote any that meet the materiality threshold.

List each entry from `cross_links.technical_risks` in the standard R-NN format.

**2.4 — `04-milestone-specs.docx`**
Standard per-milestone blocks. After the Technical Progress field of each block, append:

> **Delivery Components:** [component list from cross_links.milestone_to_components]
> **Component Readiness:** [score and primary gap from cross_links.readiness_by_milestone]

### Phase 3 — Unified strategic + technical documents

These are the new documents that did not exist in either prior suite.

**3.1 — `05-architecture-and-tech-spec.md`**

Structure:
```
# [Project] — Architecture and Technical Specification

## System Architecture
  ### Substrate layer (from project-state/ model)
  ### Skills layer (skill inventory from substrate)
  ### Surfaces layer (channels from reporting matrix)

## Technical Architecture (from codebase scan)
  ### Component inventory
  ### Entry points
  ### API surface
  ### Data models
  ### Dependencies
  ### Deployment topology

## Cross-layer integration
  ### How the substrate informs the codebase (e.g., milestone schedule drives feature flags)
  ### How the codebase delivers the substrate's milestones (component-to-milestone map)

## Technical decisions log (from substrate decisions/*.yaml, technical framing from scan)

## Configuration and environment model
```

Input from both `substrate.*` and `scan.*`. Call the `technical-specification` specialist skill for the codebase half; generate the substrate half from the project-state data directly.

**3.2 — `06-strategic-roadmap.md`**

Structure:
```
# [Project] — Strategic Roadmap and Business Value

## Project context
  ### Funder and program (from substrate.funder, budget)
  ### Governance (MPA, Steering Committee, reporting cadence)

## Business value analysis
  ### Target users and use cases (from scan — user personas, UX patterns)
  ### Value propositions (from scan — business-benefit-analysis specialist)
  ### Cost implications and ROI framing
  ### Competitive advantages

## Delivery roadmap
  ### Phases and gate criteria (from substrate.phases)
  ### Milestone schedule (Gantt summary from substrate.milestones)
  ### KPIs and success criteria (from substrate roadmap + scan capability evidence)

## Risks and mitigations
  ### Top 3 governance risks (from substrate.risks, highest score)
  ### Top 3 technical risks (from cross_links.technical_risks)

## Strategic recommendations
  ### Where to accelerate (low readiness + near deadline milestones)
  ### Where the technical foundation is strongest (high readiness components)
```

Input from both layers. Call the `business-benefit-analysis` specialist skill for the business value sections.

### Phase 4 — Software insight documents

Call each specialist skill from the `doc-suite-generator-v2` pipeline, passing `unified_context` so each skill has substrate metadata available.

| Step | Skill | File | Substrate context passed |
|------|-------|------|--------------------------|
| 4.1 | `technical-readiness` | `07-technical-readiness.md` | Milestone completion criteria — flag readiness gaps that block specific milestones |
| 4.2 | `innovation-themes` | `08-innovation-themes.md` | `substrate.project.funder` — note which innovations are funded deliverables |
| 4.3 | `extensibility-analysis` | `09-extensibility.md` | Pack system model from substrate |
| 4.4 | (derived) | `10-features-capabilities.md` | Milestone deliverables as authoritative feature names |
| 4.5 | `work-zone-mapper` | `11-work-zones.md` | Phase boundaries — map work zones to phases |
| 4.6 | (multi-project only) | `12-portfolio-position.md` | Other projects' substrate data for comparison |
| 4.7 | `worksona-themes` | `13-worksona-themes.md` | None required |
| 4.8 | `worksona-first-principles` | `14-worksona-first-principles.md` | None required |

### Phase 5 — README enrichment pass

Re-call `readme-standardizer` in enrichment mode:
- Update Description with value propositions from `06-strategic-roadmap.md`
- Update User Experience section with user persona data from business-benefit-analysis
- Update Light Spec with key technical decisions from `05-architecture-and-tech-spec.md`
- Add cross-links from Resources section to `docs/unified-suite/` files
- Update Last Updated timestamp

### Phase 6 — Index generation

Generate `00-suite-index.md`:
- Project identity block from `substrate.project` (name, funder, program, phase, health)
- Generation metadata (date, git hash if available, context assembly stats)
- Document tree table with one-sentence description per file and format badge
- Quick-reference section: milestone count / health / next deadline
- Key themes pulled from Phase 3-4 summaries (3 bullets each from architecture, roadmap, readiness)

### Phase 7 — Website sync

Copy the bundle to `project-state/website/public/downloads/unified-suite/YYYY-MM-DD/`.
Update the website reports page with download links.
Log `report.generated` to `logs/activity.ndjson` with `target: "unified-suite"` and `doc_count: 15`.

### Phase 8 — Notification (optional)

Via `project-notifier`:
- Slack post to `alerts` channel: "Unified suite generated — 15 documents in reports/unified-suite/YYYY-MM-DD/"
- Offer Gmail draft to PIC PM if the suite was triggered by a phase transition or claim cycle

## Pack extensions

A pack profile at `packs/<pack-id>/profiles/doc-suite.yaml` may add outputs to Band B or Band D:

```yaml
# packs/<pack-id>/profiles/doc-suite.yaml
doc_suite:
  phase_2_extras:
    - claim-ready-milestone-appendix.docx   # PIC MS & financial tracking form layout
    - sc-agenda-template.docx               # PIC Appendix A agenda seeded from substrate
  band_d_extras:
    - regulatory-readiness.md               # Canadian AI regulatory context
  index_footnote: |
    Documents marked ★ are produced for PIC/ISED funder reporting under the Master Project Agreement.
```

The skill checks `substrate.packs_loaded` and loads the corresponding `doc-suite.yaml` profile for each active pack before Phase 2.

## Discipline

- **Never invent data.** Every governance fact traces to a file in `project-state/`. Every technical fact traces to a file in the codebase scan.
- **Fail loudly on empty context.** If Phase 0 produces zero milestones or zero scan components, stop and report — do not generate partially-contextualized documents.
- **Idempotent.** Running twice on the same date overwrites the same directory.
- **Dated directories.** Each bundle is self-contained in `YYYY-MM-DD/` for audit trail.
- **No auto-send.** Generate locally. Distribution is the user's (or notifier's) job.
- **Cross-links are advisory.** `milestone_to_components` uses keyword heuristics. Always present the mapping to the user for confirmation before embedding in governance .docx files.

## Integration

- **project-state** — reads all substrate data
- **project-orchestrator** — triggers this skill at phase transitions and on `baseline` routine
- **project-phase-gate** — triggers regeneration after successful phase transition
- **project-website-publisher** — serves generated files as static downloads
- **project-notifier** — routes "suite generated" notification
- **project-status-reporter** — shares docx rendering primitives for SC packs; does not duplicate this skill's output
- **doc-suite-generator-v2** — specialist skills from this global skill are called in Phase 4; that skill remains the correct tool for projects with no `project-state/` substrate

## Deprecation notice

`project-doc-suite-generator` is deprecated as of v3.0. It will be removed in v3.1. Use `project-doc-suite` instead. The output path changes from `reports/baseline/Baseline-Reports-YYYY-MM-DD/` to `reports/unified-suite/YYYY-MM-DD/`.

## Reference files

- `docs/UNIFIED-SUITE-V3.md` — full design document (document map, context schema, collapse rationale, open questions)
- `scripts/generate-baseline-reports.py` — v2 governance rendering script (reference only; v3 will supersede it)
