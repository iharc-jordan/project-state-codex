---
name: project-sred-tracker
description: "Continuous SR&ED work capture for Canadian T661 claims. Records technological uncertainties (TUs), experiments (EXs), technological advancements (ADVs), and contemporaneous evidence entries into sred/ substrate. Enforces TU→EX→ADV traceability. Runs gap analysis, weekly progress digests, quarterly completeness reviews, cost roll-ups, and the innovation-criteria interview. Active when the sred capability is enabled. Use whenever the user says 'record a technical uncertainty', 'log SR&ED work', 'add an experiment', 'capture an advancement', 'SR&ED evidence', 'what's our SR&ED status', 'weekly SR&ED update', 'SR&ED digest', 'quarterly SR&ED review', 'gap analysis', 'define innovation criteria', 'what counts as innovation here', 'is this SR&ED', 'evaluate this SR&ED opportunity', 'screen this for SR&ED', or any request to track or screen experimental development work for CRA."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project SR&ED Tracker

## Purpose

Capture SR&ED-eligible work at the time it happens — not reconstructed at year-end. Every T661 claim is strengthened or weakened by the quality and timing of the underlying records. This skill is the substrate interface for all SR&ED entities in `project-state/sred/`.

The three entity types map directly to T661 sections:
- **Technological Uncertainties (TU)** → Section E [242]
- **Experiments / Work Streams (EX)** → Section F [244]
- **Technological Advancements (ADV)** → Section G [246]

Plus the **evidence log** (`sred/evidence-log.ndjson`) — the contemporaneous record that CRA may request in an audit.

**Design principle:** capture at the time of the work. A TU record created before the experiment is far more defensible than one backdated to match the T661. The evidence log is append-only and timestamped.

## Trigger phrases

- "record a technical uncertainty" / "we have an SR&ED uncertainty"
- "log SR&ED work" / "capture experiment" / "add a work stream"
- "we found an advancement" / "record a technological advancement"
- "SR&ED evidence entry" / "log this work for SR&ED"
- "what's our SR&ED status" / "quarterly SR&ED review"
- "SR&ED gap analysis" / "are we ready for the T661"
- "how much SR&ED work have we captured"
- Any milestone completion that involved experimental development

## Entity schemas

### Technological Uncertainty — `sred/uncertainties/TU-NN-<slug>.yaml`

```yaml
schema_version: 1
entity: "technological_uncertainty"
id: "TU-01"
slug: "tenant-isolation-enforcement"

# CRA Section E language
uncertainty_statement: |
  It was uncertain whether... [complete statement in CRA-preferred language]
standard_practice_gap: |
  No established method was identified for... [why existing tools/knowledge didn't apply]

# Classification
uncertainty_type: "software_engineering"  # or: materials, process, other
field_of_science: "2.02.09"               # CRA code

# Traceability
linked_experiments: []      # EX-NN IDs — populated as experiments are created
linked_milestones: []       # which project milestones involve this uncertainty

# Timing (critical for CRA)
identified_date: "YYYY-MM-DD"    # when the uncertainty was first documented — before work began
work_start_date: "YYYY-MM-DD"    # when experimental work started
work_end_date: ~                  # when resolved (or null if ongoing)
fiscal_year: "YYYY"

# Status
status: "active"    # active | resolved | removed
resolution: ~       # if resolved: brief statement of how uncertainty was resolved

# Meta
created_by: "TODO"
last_modified: "YYYY-MM-DDThh:mm:ssZ"
```

### Experiment / Work Stream — `sred/experiments/EX-NN-<slug>.yaml`

```yaml
schema_version: 1
entity: "experiment"
id: "EX-01"
slug: "schema-policy-enforcement-trials"

# CRA Section F language
linked_tu: "TU-01"
hypothesis: |
  Whether [specific technical outcome] could be achieved by [approach] under [constraints].
method_and_trials: |
  [Describe what was done: implementations attempted, tests run, architectures tried.
   Include failures, iterations, and what changed between attempts.]
observations_and_results: |
  [What was observed: measured results, failure modes, unexpected constraints,
   non-obvious findings. If an initial assumption failed, say so explicitly.]
limitations: |
  [What remained unresolved or required further work]

# Evidence references (pointers to contemporaneous records)
evidence_records:
  - type: "code_commit"         # code_commit | meeting_note | test_output | email | design_doc | other
    reference: "TODO"           # commit hash, file path, meeting date, etc.
    date: "YYYY-MM-DD"
    description: "TODO"
  - type: "test_output"
    reference: "TODO"
    date: "YYYY-MM-DD"
    description: "TODO"

# Cost allocation basis (for cost-categorization.yaml)
people_involved:
  - name: "TODO"
    role: "TODO"
    eligible_days: 0    # approximate days of eligible work on this experiment

# Traceability
linked_advancements: []   # ADV-NN IDs — populated when ADVs are created
linked_milestones: []

# Timing
start_date: "YYYY-MM-DD"
end_date: ~
fiscal_year: "YYYY"

# Status
status: "in_progress"  # in_progress | complete | abandoned
abandonment_reason: ~  # if abandoned: why

# Meta
created_by: "TODO"
last_modified: "YYYY-MM-DDThh:mm:ssZ"
```

### Technological Advancement — `sred/advancements/ADV-NN-<slug>.yaml`

```yaml
schema_version: 1
entity: "technological_advancement"
id: "ADV-01"
slug: "cross-layer-authorization-knowledge"

# CRA Section G language
linked_tu: "TU-01"
linked_experiments: ["EX-01"]
advancement_statement: |
  The work established that... [knowledge gained, not product delivered]
knowledge_gained: |
  [More detailed description of what is now known that was not known before.
   Be proportionate: don't claim broader knowledge than the experiments support.]

# Proportionality check (internal — not filed)
proportionality_note: |
  [Internal note: does this advancement match the scope of the linked experiment's results?
   If the experiment was narrow, the advancement should be narrow too.]

# Timing
established_date: "YYYY-MM-DD"  # when the advancement was achieved / knowledge confirmed
fiscal_year: "YYYY"

# Meta
created_by: "TODO"
last_modified: "YYYY-MM-DDThh:mm:ssZ"
```

### Evidence Log Entry — appended to `sred/evidence-log.ndjson`

```json
{
  "date": "YYYY-MM-DD",
  "timestamp": "ISO8601",
  "entry_type": "experiment|test|failure|iteration|advancement|meeting|publication",
  "tu_id": "TU-01",
  "ex_id": "EX-01",
  "adv_id": null,
  "description": "Brief contemporaneous description of what was done/found",
  "people": ["Name"],
  "milestone_id": "M03",
  "record_type": "code_commit|meeting_note|test_output|email|design_doc",
  "record_reference": "commit abc123 / path/to/file / meeting YYYY-MM-DD",
  "logged_by": "name",
  "logged_at": "ISO8601"
}
```

## Operations

### `record_uncertainty(fields)`

Create a new TU-NN record. Required fields:
- `uncertainty_statement` — in CRA-preferred language ("It was uncertain whether...")
- `standard_practice_gap` — why existing knowledge didn't resolve it
- `identified_date` — ideally before experimental work begins
- `field_of_science` — CRA code
- `linked_milestones` — which project milestones involve this uncertainty

Enforce: if `identified_date` is after any linked experiment's `start_date`, warn — this is a backdating risk.

### `record_experiment(fields)`

Create a new EX-NN record. Required fields:
- `linked_tu` — must reference an existing TU-NN
- `hypothesis` — what was being tested
- `method_and_trials` — what was done (ask for this if not provided)
- `observations_and_results` — what was found
- `evidence_records` — at least one

Enforce: if `observations_and_results` is empty or sounds like pure feature delivery, warn and ask for more detail. The result must include at least one of: failure, limitation, unexpected finding, iteration, refinement.

Automatically append an entry to `sred/evidence-log.ndjson`.

### `record_advancement(fields)`

Create a new ADV-NN record. Required fields:
- `linked_tu` — must reference an existing TU-NN
- `linked_experiments` — must include at least one EX-NN
- `advancement_statement` — in CRA-preferred language ("The work established that...")

Enforce:
- Advancement must be proportionate to the linked experiments' observed results
- Language must describe knowledge gained, not product delivered
- Flag any risky language from the pack profile's `risky_language_patterns` list

### `log_evidence(fields)`

Append one entry to `sred/evidence-log.ndjson`. This is the lightweight daily capture:
```
"log SR&ED work on EX-01 today — tested three token-handling approaches, two failed"
→ append evidence entry with today's date, description, EX-01 link
```

Minimal required fields: `date`, `tu_id` or `ex_id`, `description`, `people`.

**Evidence source tiers** (schema `evidence_source_tiers`): tier-1 records (commits,
test outputs, Jira issues/worklogs, Confluence page versions, repo-versioned design
docs) stand as primary evidence — cite the durable reference (issue key,
`<page-id>@<version>`). Tier-2 records (Slack, Google Docs, meeting notes, email)
corroborate only and MUST carry a verbatim `excerpt` plus permalink captured at log
time — the source may be edited or deleted later; the excerpt is what survives.
When an EX's evidence is entirely tier-2, say so at capture time and suggest a
tier-1 anchor (file the finding as a Jira comment, commit the note to the repo).

**Cluster confirmation:** when a `sred/inbox/` proposal is a correlation cluster
(one thread of work joined across Jira/GitHub/Confluence — see the harvester's
correlation pass), `confirm_evidence` writes one evidence entry per record with
`corroborated_by` cross-references to the rest of the cluster, and records the
cluster's earliest source timestamp. One human decision, N cross-referenced
receipts. **Date corroboration:** if a cluster's earliest timestamp predates the
linked TU's `identified_date` or EX's `start_date`, surface it — either the dates
need correcting toward the (defensible, server-timestamped) source record, or the
work predates the declared uncertainty and the framing needs an honest look.

### `gap_analysis()`

Scan all TU/EX/ADV records and evidence log for completeness gaps:

| Check | Risk if failed |
|-------|---------------|
| TU with no linked EX | High — uncertainty without investigation |
| EX with no linked TU | High — work without a declared uncertainty |
| EX with no evidence_records | High — no contemporaneous records |
| EX with no observations_and_results | High — no documented outcome |
| ADV with no linked EX | High — advancement without experimental basis |
| TU identified after EX start_date | Medium — backdating appearance |
| EX completed >90 days ago with no ADV | Medium — work without declared knowledge gain |
| Evidence log entry gap >30 days for active EX | Medium — stale capture |
| Milestone with experimental description and no linked TU | Medium — potential SR&ED work uncaptured |
| Work landed in a declared candidate uncertainty area (sred/criteria.yaml) with no TU on file | High — the criteria say this is frontier work and nothing was captured |
| High-activity correlation cluster (Jira/GitHub/Confluence joined) with no linked EX | High — the cohort found a work thread nothing claims |
| EX evidenced by a single source type | Low — suggest corroborating from the cohort (linked issue, build, page) while records are fresh |
| Cluster's earliest source timestamp predates linked TU identified_date / EX start_date | Medium — dates need correcting toward the server-timestamped record, or the framing needs review |
| Criteria status still `draft`, or last_refreshed older than 2 quarters | Low — capture lens going stale |

Return a prioritized gap list with recommended actions and deadlines.

### `quarterly_review()`

Run `gap_analysis()` and produce a structured quarterly review report:
1. SR&ED substrate summary: TU count, EX count, ADV count, evidence log entry count
2. Completeness gaps (from gap_analysis)
3. Cost allocation status: are people's time entries current?
4. 18-month deadline status: days remaining per fiscal year
5. Milestones completed since last review — any experimental work uncaptured?
6. Recommended actions before next quarter

Save to `reports/adhoc/sred-quarterly-YYYY-QN.md`. Offer to route to SR&ED lead via `project-notifier`.

### `traceability_map()`

Generate the full uncertainty → experiment → advancement chain for a given fiscal year:

```
TU-01 → EX-01 → ADV-01  ✓ complete
TU-01 → EX-02 → (no ADV) ⚠ advancement missing
TU-02 → (no EX) ✗ no experimental work recorded
```

Used as input to the evidence-map template and T661 narrative generation.

### `milestone_sred_check(milestone_id)`

Fired via the `sred.evidence-capture` matrix entry on `milestone.completed`. Asks:
- Does this milestone involve any experimental development? **Test against the criteria
  layers first** (`sred/criteria.yaml` candidate areas and declared-routine list, then the
  pack's `innovation-criteria` company baseline): a milestone linked to a candidate area is
  presumed to need a TU; one squarely in declared-routine is presumed not to, and says so.
- If yes: are TU/EX records current?
- If no TU exists for this milestone: suggest creating one or confirming SR&ED non-applicability

### `evaluate_opportunity(subject)`

Screen any piece of work — a milestone, a Jira epic or issue, a Confluence design page,
a proposal, an idea in chat — through the evaluation ladder. Four rungs, in order, each
capable of ending the evaluation:

1. **Routine check** (project criteria). Is the subject squarely inside
   `declared_routine`? → verdict **routine**: say so, offer to record a one-line
   non-applicability note, stop. No CRA framing wasted on CRUD.
2. **Frontier check** (project + company criteria). Does it land in a
   `candidate_uncertainty_areas` entry, or fall outside the company
   `technology_baseline`? Landing in a declared area = strong candidate; outside both
   lists = evaluate on the merits at rung 3.
3. **The five questions** (Layer 0, `schema/eligibility-baseline.yaml`). Walk each:
   uncertainty, hypothesis, systematic investigation, advancement sought, records kept.
   Apply the **field-level rule** hard: "no one on our team knew how" is rung-3 failure
   unless it can be honestly reframed as a gap in the field's established practice.
4. **Capture decision.** Verdicts:
   - **capture-now** — knowledge gap is live and work is starting: create the TU
     (`record_uncertainty`) immediately, before the work; link the source (Jira epic,
     Confluence page) as the first evidence record.
   - **watch** — plausibly frontier but not yet concrete: add/extend a candidate area in
     `sred/criteria.yaml` so the harvester and milestone hook watch for it (emits
     `sred.criteria.updated`).
   - **routine** — record the non-applicability decision so the question isn't re-litigated.
   - **borderline** — capture as if eligible (a TU costs one file; a missed TU costs the
     claim) and flag for the advisor. Never resolve borderline toward "skip".

Output: a short screening note (subject, rung reached, verdict, reasoning, action taken).
Verdicts are capture decisions, not eligibility determinations — say so in the note.

### `weekly_digest()`

The weekly capture-discipline instrument (matrix entry `sred.weekly-progress`, Mondays).
NOT a mini-claim — the quarterly review owns completeness and audit posture. Five sections,
half a page:

1. **Captured this week** — new TUs/EXs/ADVs; evidence entries appended, grouped by EX.
2. **Uncaptured but candidate** — through the criteria lens: milestones advanced, commits
   or harvested signals in `candidate_uncertainty_areas` with no TU/EX on file. This
   section cannot exist without `sred/criteria.yaml`; if criteria are missing, say so and
   offer `define_criteria`.
3. **Going stale** — active EXs with no evidence entry in 14+ days.
4. **Inbox** — unconfirmed candidates in `sred/inbox/` (count + oldest).
5. **Deadline line** — per open FY: claim status, days to target and hard deadline,
   current escalation tier.

Save to `reports/adhoc/sred-weekly-YYYY-Wnn.md`; offer routing to the SR&ED lead via
`project-notifier` (Slack). Quiet weeks are reported as quiet — one line per empty
section, never padded.

### `define_criteria()`

Guided interview that authors or refreshes `sred/criteria.yaml` (Layer 2) — ideally with
the SR&ED advisor in the room. Reads the Layer 0 baseline
(`capabilities/sred/schema/eligibility-baseline.yaml`) and the company Layer 1 profile
(pack `innovation-criteria.yaml`) first, then walks:

1. **Frontier** — "Where in this project does the field's standard practice run out?" Name
   each candidate uncertainty area (id, label, field-relative description), link milestones.
2. **Routine boundary** — "What is explicitly NOT a candidate here?" Declared-routine list.
3. **Harvester hints** — keywords, repo paths, people whose work is likely eligible.
4. **Confirm framing** — every area description must be field-relative; rewrite any
   "new to us" phrasing on the spot, citing the Layer 0 field-level rule.

Write the file from `templates/criteria.yaml`, `status: draft` until PL sign-off flips it
to `reviewed`. Emit `sred.criteria.updated` with areas added/removed — criteria drift is
audit-relevant and must be visible in the activity log. The quarterly review nudges a
refresh when `last_refreshed` ages past a quarter.

## Discipline rules

- **Capture at the time of the work.** Evidence entries should reference dates contemporaneous with the actual work — not the date they were entered into the system. If an entry is being back-filled, note the distinction.
- **Never invent experiments or results.** If the user provides insufficient detail, ask for it. Do not generate hypotheses or observed results that the user didn't provide.
- **Never imply eligibility certainty.** This skill captures and structures information. Eligibility determinations require a qualified SR&ED consultant. Flag borderline situations clearly.
- **Enforce the traceability chain.** Every ADV must trace to a TU and an EX. The skill will not create an ADV without both links.
- **Proportionality.** Advancement claims must match the scope of the experimental evidence. Warn when an advancement sounds broader than what the linked experiments support.
- **The 18-month deadline is hard.** When it is within 180 days, surface it prominently on every SR&ED interaction.
- **Criteria are a capture lens, never an eligibility argument.** The standard-practice test is field-level; "new to us" is ineligible. Criteria decide what gets recorded and investigated — eligibility framing stays field-relative and the final call is the advisor's.

## Integration

- **project-state** — all writes route through it; TU/EX/ADV are entities like milestones
- **project-milestone-manager** — calls `milestone_sred_check()` on completion; milestones link to TU/EX records
- **project-funder-reporting** — consumes TU/EX/ADV entities to generate T661 narrative via sred-canada pack profile
- **project-sred-reviewer** — receives the T661 draft for audit-risk review before advisor handoff
- **project-orchestrator** — quarterly review triggered via reporting matrix `sred.quarterly-log-review` entry
- **project-change-register** — significant scope changes may affect SR&ED eligibility; flag for advisor review

## Reference schema files

- `packs/sred-canada/templates/t661-narrative.md` — narrative template (Sections E/F/G)
- `packs/sred-canada/templates/evidence-map.md` — evidence map template
- `packs/sred-canada/templates/cost-categorization.yaml` — cost allocation template
- `packs/sred-canada/profiles/funder-reporting.yaml` — language guidance and cadence config
