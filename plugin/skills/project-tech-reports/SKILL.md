---
name: project-tech-reports
description: "Own the 11-report technical-intelligence suite for one project. Invoke only for an explicit technical-intelligence request, a due enabled tech-report matrix entry, or a required active-pack trigger. Merge a verified live source with Project State, preserve versioned report paths and history, and run once per source event and period. Never invent unverifiable claims or fan out to another report owner."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Tech Reports

## Purpose

Produce a focused, **single-project** intelligence suite of 11 markdown reports that explain what this project is, how it's built, and how ready/novel/extensible it is — every claim traceable to something observable in the codebase or the `project-state/` substrate. Cross-portfolio synthesis and the "portfolio position" report are intentionally excluded.

**Two source layers, merged before writing:**
- **The source under study** — a codebase (the enclosing repo, or a connected GitHub repo) OR an alternative source (Jira/Confluence). Owns HOW. **Required** — see *Resolving the source*.
- **`project-state/` substrate** — manifest, milestones, risks, decisions, phases, reporting matrix, people. Owns WHO / WHAT / WHEN (the product intel).

A report is good when it answers from both layers and invents nothing.

## Resolving the source (required)

These reports study a **source**. Resolve it in this priority — and if none resolves, **stop and report that no source is available** (do NOT fabricate technical content from project-state alone):

1. **`tech_reports.source` in `manifest.yaml`**, if set:
   - `kind: local` / `path: <dir>` — study that local directory.
   - `kind: github`, `repo: owner/name` — clone/fetch it with `gh`/`git` (the team token grants read) into a temp dir and study it.
   - `kind: jira` / `kind: confluence` — study that connector's corpus (per `surfaces.jira` / `surfaces.confluence` scope) instead of a codebase.
2. **`kind: auto` (default) →** the **enclosing repo**: the folder that contains `project-state/` (walk up from the substrate dir). Use it when it looks like code (`.git`, `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `src/`…).
3. If the enclosing folder has no code, fall back to `tech_reports.source.repo` (GitHub), then to an enabled `jira`/`confluence` surface.
4. **No source → stop.** Emit a short note that a source is required (enclosing repo, a connected GitHub repo, or Jira/Confluence) and generate nothing.

## Trigger phrases
- "tech reports" / "generate the tech suite" / "refresh the tech reports"
- "technical intelligence reports" / "document the codebase"
- A **Refresh** from a separately installed compatible viewer (job id `tech-reports`)

## The report catalog (11 types)

| id | Report | What it answers |
|----|--------|-----------------|
| `00-executive-summary` | Executive Summary | The one-page orientation; "what is this project"; pointers to every other report |
| `01-project-overview` | Project Overview | What it is, tech stack, architecture, how to run |
| `01b-technical-specification` | Technical Specification | Component architecture, data models, API surface, deployment topology, security, key decisions |
| `02-business-benefits` | Business Benefits | Value propositions, target users, cost implications, competitive advantages |
| `03-innovation-themes` | Innovation Themes | What's technically novel; where it advances the state of the art |
| `04-features-capabilities` | Features & Capabilities | Concrete inventory of what the project does |
| `05-extensibility` | Extensibility | Plugin points, API surfaces, config options, how it grows |
| `06-work-zones` | Work Zones | Functionality grouped into thematic zones of development activity |
| `08-technical-readiness` | Technical Readiness | Production maturity across 10 engineering dimensions, with a scored readiness card |
| `09-worksona-themes` | Worksona Leadership Themes | Alignment to the 7 Worksona leadership-runbook commands |
| `10-worksona-first-principles` | Worksona First Principles | Alignment to the 16 worksona.fp structural principles + a Work Graph perspective |

> Numbering matches the original suite (07 = portfolio-position is intentionally absent).

## Output — versioned, history-keeping

Each report is written to its own **versioned** path — never overwrite a prior version:

```
project-state/reports/tech/<report-id>/<stamp>.md
```

where `<stamp>` is a filename-safe UTC timestamp `YYYY-MM-DDTHH-MM-SSZ` (colons → hyphens),
e.g. `project-state/reports/tech/01b-technical-specification/2026-06-02T18-00-00Z.md`.

- Use a **single run timestamp** for every report generated in one run.
- The newest file in a report's folder is its "latest"; older files are the history the app surfaces.

Also **append** the run to `project-state/reports/tech/manifest.json` (create it if missing — never drop prior runs):

```json
{
  "project": "<short_name>",
  "runs": [
    { "stamp": "2026-06-02T18:00:00Z", "git": "<short hash>", "reports": ["01b-technical-specification", "08-technical-readiness"] }
  ]
}
```

> `runs` is append-only. The app derives each report's version list by scanning the per-report
> folders, so the manifest is for run-grouping/provenance, not the source of truth.

## Workflow

1. **Resolve & scan the source** (see *Resolving the source* — required). For a **codebase**: walk it from its root — detect languages/frameworks, map the directory structure and entry points, enumerate dependencies/integrations, read existing READMEs/docs, note config/deploy (Dockerfile, CI, vercel/netlify, tauri…). For a **Jira/Confluence** source: pull the configured projects/spaces and treat issues/pages as the corpus. Capture a structured scan you reuse for every report. If no source resolves, stop here and report it.

2. **Load the substrate.** Read `project-state/manifest.yaml`, `milestones/`, `risks/`, `decisions/`, `phases/`, `reporting-matrix.yaml`, and the tail of `logs/activity.ndjson`. This is the product intel — business/funder/governance context — merged with the source scan in every report.

3. **Determine the scope.** The invoking prompt says either "ALL 11 reports" or "ONLY these reports: `<id>, <id>…`". Generate **only the requested ids** (default to all 11 if unspecified). Generating a subset must NOT touch the other reports' folders.

4. **Generate each requested report** into its versioned path `project-state/reports/tech/<report-id>/<stamp>.md` (one shared `<stamp>` for the run), in catalog order (later reports may reference earlier ones generated this run or already on disk). For 09 and 10, read the bundled reference docs:
   - `references/worksona-leadership-runbook.md` — the 7 commands, for `09-worksona-themes`.
   - `references/worksona-fp-compendium.md` — the 16 principles, for `10-worksona-first-principles`.

5. **Append the run** to `project-state/reports/tech/manifest.json` (create if missing; never drop prior runs): a `runs[]` entry with `stamp` (ISO), `git` (short HEAD if a git repo), and `reports` (the ids generated this run). Set/refresh top-level `project`.

6. **Append one activity event** to `project-state/logs/activity.ndjson`:
   `{"ts":"<ISO>","actor":"<operator>","event":"report.generated","detail":"Tech Reports — generated <N> report(s): <ids>."}`

## Report format

Each report starts with:

```markdown
# [Project Name] — Tech Reports — Report [NN]: [Title]

> **Project:** [name] | **Generated:** [date] | **Version:** [git hash if available]

## Executive Summary
[2–3 sentences]

## [Main sections — vary by report]

## Key Takeaways
[bullets]

## Cross-References
[links to sibling reports in this suite]
```

`00-executive-summary.md` uses the title `# [Project Name] — Tech Reports — Executive Summary` and links each sibling report by relative path (e.g. `[Technical Specification](01b-technical-specification.md)`).

## Principles

- **Evidence-based.** Every claim traces to a file, dependency, pattern, or config value. Name specifics (paths, functions, modules) over generalities.
- **Honest about gaps.** Missing tests, thin docs, rough edges — say so constructively. Technical readiness must reflect reality.
- **Consistent voice.** All 11 reports read as one thoughtful analyst.
- **No invention.** If something can't be verified from the codebase or substrate, leave it out.
- **Versioned, never overwrite.** Each run writes new timestamped files under each report's folder; prior versions are kept as history. Generating a subset leaves the other reports untouched.
- **Markdown only.** No Office files — this suite is the markdown intelligence set (the governance Office bundle lives in `project-doc-suite`).
