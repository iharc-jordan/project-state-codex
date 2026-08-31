---
name: project-document-curator
description: "Classify, index, and manage project documents — proposals, MPAs, signed Schedule A workbooks, PIC templates, quarterly claim forms, meeting minutes, publications, and any other file that lands in the project. Use this skill whenever the user says 'I just dropped a doc', 'classify this file', 'catalog the inbox', 'what docs do we have', 'where is the MPA', 'promote this to source of truth', 'update the document index', 'a PIC form arrived', 'archive the old proposal', 'the signed MPA is here', 'what is the source of truth for X', or any request to ingest, find, classify, or promote documents inside a `project-state/` project. Also trigger when any project-* skill needs to reference a specific document by canonical path, or when the user drops a file into `project-state/documents/inbox/`."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Document Curator

## Purpose

Be the librarian. Every project document (docx, xlsx, pdf, md, docx) has a canonical path and metadata in `project-state/documents/index.yaml`. When a doc arrives, classify it, give it a stable `id`, decide whether it's source-of-truth, move it to the right folder, and cross-reference it from the manifest or a phase.

Without this skill, docs pile up with ambiguous names in the project root and nobody knows what the current MPA version is.

## Trigger phrases (priority order)

1. "I just dropped [filename] into the project" / "there's a new doc"
2. "classify this file" / "catalog the inbox"
3. "where is the MPA" / "where's the latest Schedule A"
4. "promote [id] to source of truth"
5. "update the document index"
6. Any `project-*` skill fetching a document by id or kind

## State routing

All documents live under `project-state/documents/`:

| Folder            | Contents                                                                |
| ----------------- | ----------------------------------------------------------------------- |
| `inbox/`          | New arrivals awaiting classification                                    |
| `source-of-truth/`| Authoritative versions — MPA, signed Schedule A, approval letters       |
| `working/`        | Drafts in progress — claim drafts, pre-submission workbooks             |
| `published/`      | Versions delivered to PIC/Consortium (frozen)                           |
| `pic-templates/`  | PIC-provided blank templates                                            |

The index is at `documents/index.yaml`. Two top-level lists: `docs:` for published-document entries
(canonical; readers tolerate `documents:`/`entries:` but always WRITE `docs:`) and `classified:` for
one entry per ingested document. Its schema is in `docs/SCHEMA.md` → "Document index
(`documents/index.yaml`)". *(Before 2026-08-21 this line pointed at `project-state/SCHEMA.md` entry
"Document registry" — wrong path, and no such section existed. The shape was undocumented.)*

## Provenance & lineage fields (v4.2 — every entry SHOULD carry these)

Location never determines identity — the record does. On registration, stamp:

```yaml
origin: imported            # imported | generated | observed | received | unknown
provenance:
  method: upload            # upload | orient-ingest | harvester | chat-session | report-generator | manual
  actor: <substrate user id>
  session: <chat/job session id, when an agent did the ingesting>
  at: <ISO timestamp>
lifecycle: ingested         # dropped → classified → ingesting → ingested → grounded | parked | superseded
pinned: false               # true = vital key asset; surfaces on the pinned shelf
became: []                  # lineage: what this document produced
  # - { kind: milestone|risk|decision|insight|report, id or path, note }
cited_by: []                # entity ids/paths that cite this document
```

Rules: `origin` is recorded at the moment of arrival by whoever moves the file — never inferred from folder location afterwards. Never fabricate provenance during backfills: use `origin: unknown` when the true origin is not known. When any skill or session derives an artifact from a registered document, it appends a `became:` edge (and the derived entity may record the doc id in its own provenance). A citation is stable as `<slug>@<git commit>` — the commit service's snapshots make any cited revision retrievable.

## The classification decision

When a doc lands, answer these five questions in order:

1. **What kind?** → map to an enum:
   - `mpa` (signed Master Project Agreement)
   - `mpa-template`
   - `schedule-a-workbook` (signed) or `schedule-a-template`
   - `proposal` (submitted full proposal)
   - `approval-letter`
   - `financial-assessment` (step 1 or step 2)
   - `pic-template` (any blank PIC form)
   - `capital-cost-request` / `foreign-cost-request`
   - `change-order` (filled, signed) — but also indexed from `changes/change-orders/` YAML
   - `claim-submission` (filled xlsx submitted to PIC)
   - `sc-agenda` / `sc-minutes`
   - `monthly-brief` / `weekly-report`
   - `publication` / `presentation`
   - `ip-disclosure`
   - `annual-questionnaire`
   - `final-report`
   - `invoice` / `receipt` (expense-eligibility supporting docs)
   - `misc` (use sparingly, ask for a better classification)

2. **What phase does it belong to?** `01-loi` / `02-approval` / `03-planning` / `04-execution` / `05-closeout`. Default to the current phase.

3. **Is this source-of-truth?** An item is SoT if it is THE authoritative version of a fact for the project. The signed MPA is SoT. A pre-signing draft is NOT. A PIC approval letter is SoT. A blank PIC template is NOT. The filled and submitted Q2 claim is SoT for what was submitted; next quarter's draft is not.

4. **Does it supersede an earlier SoT?** If so, set `superseded_by` on the old entry and `supersedes` on the new one. Do not delete the old file — move it to `source-of-truth/archive/` or `published/`.

5. **What does the rest of the state need to know?** Cross-references:
   - If `mpa` (signed) → update `manifest.yaml:dates.mpa_signed`, `project.governing_document_status`
   - If `approval-letter` → update `manifest.yaml:dates.approval_date`, evidence on `phases/02-approval/manifest.yaml:gate_out.evidence`
   - If `schedule-a-workbook` signed → it becomes the authoritative source for milestones; flag the scaffolder to reconcile `milestones/` against it
   - If `sc-minutes` → link from `reports/sc-meetings/<id>.yaml`
   - If `claim-submission` → link from `reports/claims/<id>.yaml` and log `claim.submitted`

## Workflow

### On arrival (`documents/inbox/` → classified)

```
GIVEN a new file in documents/inbox/ (or user says "I added a file")

PRE-CHECK: Has project-inbox already triaged this document?
  → Query documents/index.yaml for this file's path.
  → IF entry exists with triage_state: processed:
      Present the smart inbox pre-classification to the user:
        "Smart inbox pre-classified this document:
          Kind:        {kind}
          Designation: {use_designation}
          Summary:     {extraction_summary}
        Confirm this classification, or correct it?"
      On confirmation: accept the pre-classification and skip questions 1–2 below.
      On correction: proceed with questions 1–2 using the pre-classification as a starting hypothesis.
      In both cases: PRESERVE all smart inbox metadata fields (triage_state, use_designation,
        relevance_score, action_flags, extraction_summary, triage_timestamp, triage_confidence)
        when writing the updated index entry. Do not overwrite them.

1. Read the filename and the first 500 bytes / table of contents.
2. Propose a classification (kind, phase, sot?) and show it to the user for confirmation.
3. On confirmation:
   a. Move the file to the appropriate folder (source-of-truth / working / published / pic-templates).
   b. Assign an id: "doc-<kind>-<yyyy-mm-dd>-<slug>" OR preserve an existing id pattern.
   c. Append a new entry to documents/index.yaml (or update the existing entry if pre-triaged).
      `classified_by` is single-valued and this skill is AUTHORITATIVE over `project-inbox`'s triage
      pre-pass: REPLACE the key, never add a second one. Two skills appending it produced a duplicate
      YAML key on 34 of 198 entries, and a normal loader silently discarded the first (FB-006). The
      inbox's pass is not lost by overwriting — it is already in `logs/activity.ndjson`.
   d. If SoT and supersedes an older entry, update supersedes/superseded_by links.
   e. Update manifest.yaml cross-references where applicable (dates, governing_document_status, phase evidence).
   f. Call project-state to log document.registered (and document.sot.promoted if applicable).
4. Return the canonical path and id.
```

### Lookup (`where is X?`)

```
GIVEN a kind or slug from the user
1. Query documents/index.yaml.
2. If multiple matches, prefer the one with source_of_truth: true and no superseded_by.
3. Return (id, kind, canonical path, last_modified, sot_flag, notes).
```

### Promote (`promote to source of truth`)

```
GIVEN an existing document id
1. Confirm it isn't already SoT.
2. Move the file from working/ or published/ to source-of-truth/.
3. Update its index entry: source_of_truth: true, source_of_truth_for: [...].
4. If it supersedes a prior SoT, set the supersedes/superseded_by links.
5. Call project-state to log document.sot.promoted.
```

### Index audit (`what docs do we have?` / `audit the inventory`)

Walk every file under `documents/`. Compare to `documents/index.yaml`:
- Files in the tree not in the index → `UNINDEXED` warning
- Index entries with missing files on disk → `MISSING` warning
- SoT entries with `superseded_by` pointing nowhere → `DANGLING` warning

Return a short table: total docs, by kind, by phase, SoT count, warnings.

## Integration with other skills

- **project-feedback** — when a classified doc carries `action_flags: [seed-issue]`, `project-feedback capture --from-signals` drafts feedback records from it (one per distinct claim) and registers them as GitHub issues. The curator only sets the flag; it never files.

- **project-inbox** — if a document in `documents/inbox/` has already been triaged by `project-inbox` (i.e., `triage_state: processed` in `documents/index.yaml`), the curator presents the pre-classification for confirmation rather than running the 5-question classification from scratch. Smart inbox metadata fields are always preserved in the index entry.
- **project-state** — all writes to `documents/index.yaml` and `manifest.yaml` go through `project-state`'s locking/logging. This skill reads/writes intent; `project-state` executes.
- **project-phase-gate** — when a doc is registered that matches a gate's `required_artifacts_paths`, populate that path. If all gate artifacts are present, `project-phase-gate` can offer to transition.
- **project-status-reporter** — status reports link to SoT docs by id (never by raw filename). Renames are invisible to reports.

## Reference: example inventory snapshot

At scaffold time the index is typically seeded with source-of-truth docs such as:
- `doc-proposal-full` — Full Proposal or application document
- `doc-program-workbook` — Program Workbook (to be superseded by signed governing agreement)
- `doc-financial-step1` — Financial Assessment Step 1 workbook
- `doc-funder-pm-guide` — Funder Project Management Guide

And non-SoT templates such as:
- `doc-agreement-template`, `doc-financial-step2-template`, `doc-fca-template`

When the signed governing agreement arrives in `inbox/`, it supersedes the program workbook as the authoritative milestone list.
