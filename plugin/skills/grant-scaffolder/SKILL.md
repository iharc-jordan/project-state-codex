---
name: grant-scaffolder
description: "Initialize the standard grant-state facility only on an explicit grant-scaffolding or award-handoff request. Inspect supplied program sources first, propose but do not infer the matching playbook or eligibility, and preserve narrative, gate, budget, phase, freeze, and project handoff contracts. Never create an external surface or sibling project without confirmation."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Grant Scaffolder

## Purpose

Initialize a `grant-state/` submission facility and manage the award handoff to `project-state/`. Used twice per grant:
1. **At submission start** — scaffold the facility.
2. **On award** — freeze the facility, spawn `project-state/`, carry forward artifacts.

## Codex flow

Use ordinary Markdown. Inspect supplied program sources before this flow, then:

1. **Program selection** — show the 19 playbooks and their matching terms in a
   compact table. Propose the source-supported candidate with confidence and
   require confirmation; use `_agnostic-core` when none is confirmed.
2. **Project inputs** — summarize the fields below with attribution and group
   unresolved required questions. Do not enable Slack, Gmail, Calendar, or any
   other surface unless the operator confirms it and the surface is available.
3. **Compliance preview** — render the applicable gate map as Mermaid and a
   required / recommended / not-applicable table. Preserve every gate rule below.
4. **Review and confirm** — show all inputs and the exact facility tree. Obtain
   explicit confirmation before creating files or initializing Git.
5. **Build result** — show a checklist of files created and the next intake step.

For an award handoff, show the award fields and carry-forward counts in Markdown,
including the grant-state to project-state flow. Obtain explicit confirmation
before freezing the grant facility or creating the sibling Project State
facility.

## Inputs (ask only when unresolved after source inspection)

1. **Program name** — which Canadian program? (used to match playbook)
2. **Deadline** — ISO date, or `null` for continuous-intake programs
3. **Project short name** — slug used as directory name
4. **Project long name** — full descriptive title
5. **Lead organization** — signs the submission
6. **PI name and email**
7. **Consortium shape** — `single-applicant` | `single-pi-with-partners` | `multi-party-consortium`
8. **Provinces/regions** — for regional agency eligibility checks
9. **Indigenous engagement** — `yes` | `no` | `unsure` (drives OCAP gate default)
10. **Surfaces** — Slack / Gmail / Calendar desired?
11. **Parent directory** — where to create the facility

## Playbook matching

Match `program_name` against the playbook library (case-insensitive, fuzzy):

| Playbook ID | Matches |
|---|---|
| `tri-council-nserc-alliance` | NSERC Alliance, NSERC Alliance-Industry, NSERC |
| `tri-council-nserc-discovery` | NSERC Discovery |
| `tri-council-sshrc` | SSHRC, Social Sciences, Humanities |
| `tri-council-cihr` | CIHR, Health Research |
| `irap` | IRAP, NRC-IRAP, Industrial Research Assistance |
| `sif` | SIF, Strategic Innovation Fund |
| `pic` | PIC, Protein Industries Canada, PCAIS |
| `cfi-jelf` | CFI, JELF, John R. Evans Leaders Fund |
| `mitacs-accelerate` | Mitacs, Accelerate, Elevate |
| `ngen` | NGen, Next Generation Manufacturing |
| `scale-ai` | SCALE.AI |
| `genome-canada` | Genome Canada, Genomics |
| `pacifican-bsp` | PacifiCan, BSP, Pacific Economic Development |
| `feddev-ontario-bsp` | FedDev, FedDev Ontario |
| `fednor` | FedNor, Northern Ontario |
| `ced-quebec` | CED, Développement économique Canada |
| `acoa` | ACOA, Atlantic Canada Opportunities |
| `cannor` | CanNor, Canadian Northern Economic Development |
| `sred` | SR&ED, Scientific Research, Experimental Development |
| `_agnostic-core` | fallback for unrecognized programs |

Match confidence:
- `exact` — program name matches playbook keyword directly
- `fuzzy` — partial match; confirm with user before proceeding
- `fallback-agnostic` — no match found; use agnostic-core and note gaps

## What gets scaffolded

```
grant-state/
├── manifest.yaml              (seeded from inputs + playbook)
├── state.json                 (phase: prospect, counters zeroed)
├── program-record.yaml        (program requirements from playbook)
├── sections/                  (one YAML per required narrative section from playbook)
├── gates/                     (one YAML per compliance gate — see gate defaults below)
├── letters/                   (empty; letter stubs added per playbook requirements)
├── budget/                    (budget scaffold from playbook)
├── sources/                   (empty; grant-ingestor populates)
├── citations/                 (empty)
├── findings/                  (empty)
├── documents/
│   ├── inbox/
│   └── working/
└── logs/
    ├── activity.ndjson        (project.scaffolded event)
    └── decisions.ndjson
```

## Compliance gate defaults by geography and engagement

Seed gates with applicability based on inputs:

| Gate | Required when |
|---|---|
| `ocap` | `indigenous_engagement == yes` |
| `gba-plus` | Tri-Council, SIF, NGen, SCALE.AI, CFI |
| `bilingual` | All federal programs (required or recommended) |
| `tto-routing` | Any program requiring IP declaration |
| `stacking` | All programs (disclosure of co-funding) |
| `ip-declaration` | All programs |
| `indigenous-engagement` | `indigenous_engagement == yes or unsure` |
| `environmental` | CFI, SIF, programs with physical infrastructure |
| `cost-share` | Programs with cash/in-kind requirements |
| `ethics-reb` | CIHR, SSHRC, programs involving human subjects |
| `biosafety` | CIHR, Genome Canada, programs with biological materials |
| `data-sovereignty` | Any program involving Indigenous data |

## Git initialization

After scaffolding, initialize a git repo in the facility's parent directory:
1. Check for existing `.git`. If present, skip `git init`.
2. Run `git init` in parent directory (or project root if nested).
3. Write `.gitattributes`:
   ```
   grant-state/logs/*.ndjson merge=union
   ```
4. Leave the new facility uncommitted. Offer a scoped Git checkpoint as a
   separate, deliberate action and require explicit acceptance before staging.

## Output

After scaffolding, render Step 5 — Build Output (see Presentation Protocol above):
1. Show the facility tree (StatusRows or code block per surface).
2. Show which sections were seeded and gates set to required / recommended / not-applicable.
3. Log `grant.scaffolded` to `logs/activity.ndjson`.
4. Show next step: "Drop the program guide and eligibility docs into `grant-state/documents/inbox/`, then run `/grant-ingestor triage`."

---

## Award handoff

When the user says "we won the grant" / "record award" / "award confirmed":

### Inputs needed
- Award date (ISO)
- Sponsor reference number
- Award amount
- Award conditions (if any)
- Target directory for `project-state/` (usually sibling of `grant-state/`)

### Steps

1. **Write `grant-state/award-record.yaml`:**
   ```yaml
   id: award-record
   kind: award-record
   outcome: awarded
   award_date: <ISO date>
   sponsor_ref: <ref>
   award_amount: <amount>
   conditions: <any special conditions>
   frozen_at: <ISO-8601 UTC>
   ```

2. **Freeze the facility.** Write `grant-state/state.json:phase = awarded` and `frozen: true`. Add a `FROZEN.md` to `grant-state/`: "This submission facility is frozen. All subsequent project work is in `../project-state/`."

3. **Read carry-forward artifacts:**
   - Consortium people (from `manifest.yaml:consortium_members`)
   - IP rationale (from `sources/` + `gates/ip-declaration.yaml`)
   - Gate snapshots (all cleared gates)
   - Milestones from `program-record.yaml:required_milestones` (re-baseline to execution dates)
   - `grant-state/` path (for provenance references in `project-state/`)

4. **Call `project-scaffolder`** to initialize `project-state/` in the target directory. Pass the grant-canada pack and the carry-forward data as pre-fill.

5. **Populate `project-state/` with carry-forward data:**
   - `people/` — consortium member YAMLs with roles from the submission
   - `documents/inbox/ip-rationale.md` — IP rationale narrative from submission
   - `milestones/` — re-baselined milestone YAMLs with `source: grant-state/<slug>` provenance
   - Decision: "Adopted project-state/ facility — award from <program> (ref: <sponsor-ref>)"

6. **Log events:**
   - In `grant-state/logs/activity.ndjson`: `award.recorded`, `facility.frozen`, `project-state.spawned`
   - In `project-state/logs/activity.ndjson`: `project.scaffolded`, `grant-state.carryforward-applied`

7. **Report:**
   ```
   Award handoff complete.

   Frozen: grant-state/<slug>/  (read-only; provenance preserved)
   Created: project-state/      (execution facility, execution phase)

   Carried forward:
     N consortium members → project-state/people/
     IP rationale         → project-state/documents/inbox/
     N milestones         → project-state/milestones/ (re-baselined to execution dates)
     N gate snapshots     → project-state/compliance/

   Next: run `/project-onboarding` in project-state/ to complete setup.
   ```

---

## Rejection handling

When "we didn't get it" / "submission rejected":
1. Write `grant-state/award-record.yaml` with `outcome: rejected`.
2. Set `state.json:phase = rejected`.
3. Offer: "Run `/grant-ingestor lessons` to capture submission lessons learned before archiving."
4. Offer to copy promising sections to a `reuse/` folder for next submission cycle.

---

## Discipline

- **Idempotent.** If `grant-state/` exists, abort with warning; offer `grant-state validate` instead.
- **Confirm before writing.** Confirm inputs and playbook match before creating files.
- **Never overwrite existing files.**
- **On award: never auto-create `project-state/` without user confirmation.**

## Integration

- **grant-state** — all facility reads/writes route through it.
- **grant-ingestor** — called after scaffold to drain inbox and produce strategy pass.
- **project-scaffolder** — called on award to spawn execution facility.
- **project-git** — git initialization is part of scaffolding; subsequent checkpointing via `project-git`.
