---
name: grant-ingestor
description: "Drain grant-state/documents/inbox/ of program guides, eligibility docs, RFPs, and partner materials; produce a strategy pass that maps content to required narrative sections and compliance gates; generate an eligibility verdict. Sub-actions: triage (classify inbox docs), strategy (produce strategy pass memo + section-coverage map), verdict (eligibility verdict with confidence), harvest (pull overnight signals from Gmail/Slack for this submission), lessons (capture lessons from a rejected submission). Use for 'drain the inbox', 'run strategy pass', 'are we eligible', 'what sections do we need', 'harvest overnight grant signals'."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Grant Ingestor

## Purpose

The intelligence layer for grant submissions. Processes raw documents from the inbox, extracts program requirements, maps them to the submission structure, and generates decision-support outputs.

This skill does the reading so the PI and team can do the writing.

## Sub-actions

---

### `triage` (default)

Classify all documents in `grant-state/documents/inbox/` and register them in `grant-state/sources/`.

**Steps:**
1. List all files in `grant-state/documents/inbox/`.
2. For each unprocessed file, classify it:
   - **Doc type**: program-guide | eligibility-doc | rfp | letter-of-intent-guide | partner-letter-template | financial-template | application-form | previous-submission | competitor-submission | academic-paper | other
   - **Relevance score** (0–100): how useful for this submission?
   - **Key extractions**: deadline, word limits per section, required sections list, required letters list, eligibility criteria, stacking rules, compliance gate requirements, cost-share requirements
   - **Action flags**: `updates-section-requirements`, `updates-gate-requirements`, `updates-eligibility-verdict`, `seed-budget`, `reference-only`
3. Write a `grant-state/sources/<slug>.yaml` for each document with classification + extractions.
4. Update `grant-state/program-record.yaml` with any extracted requirements (merge, don't overwrite manual edits).
5. Log `grant.inbox.triaged` with count to `logs/activity.ndjson`.

**Output:**
```
Triage complete — 4 documents processed

  program-guide-2026.pdf      program-guide    relevance: 95  → updates section requirements, gate requirements
  eligibility-checklist.xlsx  eligibility-doc  relevance: 88  → updates eligibility verdict
  partner-template.docx       letter-template  relevance: 60  → reference-only
  budget-workbook.xlsx        financial-template relevance: 90 → seed-budget

Run /grant-ingestor strategy to generate the strategy pass.
```

---

### `strategy`

Produce a structured strategy pass from all ingested sources. Output to `grant-state/strategy-pass.yaml` and `grant-state/documents/working/strategy-pass.md`.

**The strategy pass contains:**

**1. Program fit memo** (~500 words)
- How well does this team/project fit the program's stated objectives?
- What alignment angles are strongest? What are the gaps?
- Are there competing submissions the team should differentiate from?

**2. Eligibility verdict** (see also `verdict` sub-action)
- Likely eligible | Borderline | Likely ineligible
- Confidence: high | medium | low
- Blocking issues (if any)

**3. Section coverage map**
For each required narrative section from `program-record.yaml`:
```
Section: Project Description (3,000 words)
  Status: not-started
  Key requirements extracted:
    - Must demonstrate clear research objectives
    - Must reference HQP training plan
    - Must address knowledge mobilization
  Suggested approach: [1-2 sentence direction]
  Relevant sources: [list of ingested docs]
```

**4. Compliance gate map**
For each gate in `grant-state/gates/`:
```
Gate: GBA+ Analysis (required)
  Status: open
  What's required: Demonstrate consideration of gender, diversity, and inclusion
  Where it appears in the application: Sections 3, 7
  Evidence needed: GBA+ worksheet or narrative
```

**5. Letter requirements**
List required letters with deadlines relative to submission date:
```
Letter type              Required by  Status
Support (lead org)       submission   not-started
Partnership (partner A)  submission   not-started
TTO (IP rationale)       submission   not-started
```

**6. Risk register seed**
3–5 submission risks based on identified gaps:
- Missing requirement areas
- Gates with unclear applicability
- Partner letters not yet requested
- Budget complexity (cost-share verification)

**7. Prioritized work order**
Days-to-deadline-aware recommendation of what to work on next.

**Steps:**
1. Read all `grant-state/sources/*.yaml` (triaged documents).
2. Read `grant-state/gates/*.yaml` (current gate status).
3. Read `grant-state/sections/*.yaml` (current section status).
4. Read `grant-state/manifest.yaml` (program, deadline, consortium).
5. Produce the strategy pass document.
6. Write `grant-state/strategy-pass.yaml` (structured) + `documents/working/strategy-pass.md` (readable).
7. Update `grant-state/sections/` — set `status: draft` for all sections that have content direction from the strategy pass.
8. Log `grant.strategy-pass.generated`.

---

### `verdict`

Produce a standalone eligibility verdict with confidence scoring.

**Output format:**
```
Eligibility Verdict — <program> — <date>

Overall: LIKELY ELIGIBLE (confidence: high)

Criteria assessment:
  Eligible organization type          PASS  (university confirmed)
  Minimum partner requirement         PASS  (3 industry partners confirmed)
  Research focus alignment            PASS  (strong alignment to program themes)
  Budget range                        PASS  ($1.2M within $500K–$5M range)
  Cost-share requirement              BORDERLINE  (partners have verbal; no letters yet)
  Previous award conflicts            PASS  (no concurrent NSERC Alliance confirmed)
  Bilingual requirement               NOT ASSESSED  (translation not yet arranged)

Blocking issues: None
At-risk items:
  - Cost-share letters not yet confirmed (get partner LOIs before internal review)
  - Bilingual abstract needed before submission
```

---

### `harvest`

Pull overnight signals from Gmail and Slack relevant to this submission.

**What to look for:**
- Emails from program officers (priority: high)
- Emails from consortium partners (especially re: letters, commitments, cost-share)
- Slack messages in submission-related channels
- Any funder communications (FAQs, program updates, deadline extensions)

**Steps:**
1. Read `grant-state/manifest.yaml:surfaces` to check which surfaces are enabled.
2. For Gmail (if enabled): search for emails to/from program officer emails listed in `grant-state/program-record.yaml:contacts`, and emails from consortium partner domains.
3. For Slack (if enabled): scan configured channels for keywords matching the submission slug and funder name.
4. For each signal: classify as `action-required` | `informational` | `noise`.
5. Write action-required signals as findings to `grant-state/findings/` (severity: `major` for time-sensitive items).
6. Log `grant.harvest.completed` with signal counts.

**Output:**
```
Harvest — <date>

Gmail: 3 signals found
  ACTION  Email from program officer re: eligibility clarification (see findings/F-001)
  INFO    Partner A confirms letter in progress
  NOISE   Newsletter from funder

Slack: 1 signal found
  INFO    @pi mentioned submission deadline in #research channel

1 new finding added. Run /grant-ingestor strategy to refresh strategy pass.
```

---

### `lessons`

Capture lessons learned from a completed (awarded or rejected) submission. Intended to be run before archiving.

**Steps:**
1. Read `grant-state/award-record.yaml` for outcome.
2. Read all `findings/` (what red-team issues were raised and how resolved?).
3. Read `strategy-pass.yaml` (what was the original plan vs. what shipped?).
4. Produce a structured lessons document:
   - What worked well (sections with strong reviewer feedback if available)
   - What to do differently next time
   - Program-specific tips for this funder
   - Sections worth reusing in future submissions
5. Write to `grant-state/documents/working/lessons-learned.md`.
6. Offer to copy high-scoring sections to a `reuse/` folder.

---

## Program-specific intelligence

When triaging or producing a strategy pass, apply these program-specific checks:

**Tri-Council (NSERC/SSHRC/CIHR)**
- Check for HQP training plan requirement (NSERC Alliance requires it)
- Check for open-access data management plan
- Verify REB/biosafety applicability (CIHR always; SSHRC for human subjects)
- Check bilingual abstract requirement
- Check OCAP if Indigenous data involved

**IRAP**
- Confirm applicant is an SME (NRC-IRAP is SME-only)
- Check milestone-based disbursement structure matches project plan
- Confirm ITA (Industrial Technology Advisor) contact is identified

**SIF**
- Check minimum project size ($10M+ typically)
- Confirm significant Canadian economic benefit narrative
- Verify consortium has industrial anchor

**PIC**
- Confirm protein/agri-food sector relevance
- Check consortium shape (multi-party preferred)
- Verify PCAIS-stream eligibility vs. other PIC streams

**CFI JELF**
- Confirm applicant is an eligible research institution
- Check equipment-focused nature (CFI funds infrastructure, not salaries)
- Verify institution's CFI allocation status

**SR&ED**
- Flags automatically if sred-canada pack is also loaded (complementary)
- Otherwise: note that SR&ED claims are separate from grant submission

---

## Reads
- `grant-state/documents/inbox/` — raw documents to ingest
- `grant-state/sources/` — previously triaged documents
- `grant-state/sections/` — current section status
- `grant-state/gates/` — current gate status
- `grant-state/manifest.yaml` — program, deadline, consortium
- `grant-state/program-record.yaml` — extracted program requirements
- Gmail, Slack (if surfaces enabled, for `harvest` sub-action)

## Writes (via `grant-state`)
- `grant-state/sources/<slug>.yaml` — triaged document records
- `grant-state/program-record.yaml` — merged program requirements
- `grant-state/strategy-pass.yaml` — structured strategy pass
- `grant-state/documents/working/strategy-pass.md` — readable strategy pass
- `grant-state/findings/<id>.yaml` — findings raised during harvest
- `grant-state/logs/activity.ndjson` — events

## Called by
- User directly
- `project-orchestrator` — may suggest `grant-ingestor harvest` in the daily routine if a submission is active

## Calls
- `grant-state` — for all facility reads/writes
