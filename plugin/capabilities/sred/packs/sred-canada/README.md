# SR&ED Canada Pack

**Pack ID:** `sred-canada`
**Version:** 1.0.0
**Compatible core:** ≥4.1
**Maturity:** beta
**Shape:** bundled default pack of the `sred` capability (`capabilities/sred/`) — behavior only. Entities, skills, templates, validator, and the authoritative public rules ship with the capability, not this pack.

## What this pack does

Integrates Canadian SR&ED (Scientific Research & Experimental Development) tax credit tracking and claim preparation into the project-state substrate. SR&ED is CRA's T661/T2SCH1 program — a federal tax incentive for companies performing R&D in Canada.

The pack solves the most common SR&ED failure mode: **reconstructing claims from memory at year-end** instead of capturing contemporaneous records during the work. It adds a lightweight capture workflow so that technological uncertainties, experiments, and advancements are recorded as the project progresses — making the T661 narrative a byproduct of normal work rather than a scramble in February.

## What's different about SR&ED vs. other packs

All other packs configure a funder or customer relationship. SR&ED is neither — it is a tax mechanism. CRA is not a project stakeholder. The "filing" is a T2 corporate tax return amendment, not a project deliverable. But the _preparation_ for that filing runs in parallel with every other aspect of the project, and the quality of that preparation depends entirely on records created during the work itself.

The **capability** (`capabilities/sred/`) extends the substrate with the SR&ED entities and
ships the two skills (`project-sred-tracker`, `project-sred-reviewer`). This **pack** supplies
the behavior: the fiscal-year-anchored claim chain, CRA language guidance, gate injections,
publication coordination, and the archive tail.

## The three SR&ED entities

Every T661 claim requires traceability across three entity types:

| Entity | Directory | CRA section | Purpose |
|--------|-----------|-------------|---------|
| Technological Uncertainty (TU) | `sred/uncertainties/` | Section E [242] | Knowledge gap that couldn't be resolved by standard practice |
| Experiment / Work Stream (EX) | `sred/experiments/` | Section F [244] | Systematic investigation: hypothesis → trial → result |
| Technological Advancement (ADV) | `sred/advancements/` | Section G [246] | Knowledge gained, traceable back to a TU and an EX |

Every advancement must trace to at least one uncertainty and one experiment. The `project-sred-tracker` skill enforces this chain.

## The evidence log

`sred/evidence-log.ndjson` is an append-only contemporaneous record of SR&ED work. Each entry records:
- date of the work
- what was done (experiment, test, failure, iteration)
- which TU/EX it relates to
- who performed the work
- what records exist (commit hash, meeting note, test output, etc.)
- which milestone it relates to (links SR&ED to project delivery)

CRA may request contemporaneous records in an audit. This log is the first line of defence.

## The annual cycle

| When | What |
|------|------|
| During the year | Capture TUs, EXs, ADVs + evidence as work happens (project-sred-tracker) |
| Q4 / fiscal year-end | Review evidence log completeness; flag gaps; categorize costs |
| Within 18 months of FY end | File T661 with T2 return (hard CRA deadline) |
| Before filing | Run project-sred-reviewer for audit-risk check |

The reporting matrix seeds a quarterly `sred-log-review` entry and an annual `t661-draft` entry.

## Pairing with other packs

SR&ED pairs with any project-type pack. Common combinations:

| Combination | Context |
|---|---|
| `sred-canada` + `pic-pcais` | Government-funded AI consortium doing experimental work — both PIC claims and SR&ED claims run in parallel |
| `sred-canada` + `client-services` | Consulting project with R&D component — SR&ED on the experimental streams, client reporting on delivery |
| `sred-canada` + `agile-default` | Software product team with SR&ED-eligible technical innovation |
| `sred-canada` + `board-investor` | VC-backed startup; SR&ED refund improves cash position reported to investors |

## Important constraints

- **CRA is not a project stakeholder.** Do not add CRA contacts to the Steering Committee or reporting matrix stakeholder list. The `funder.cra` namespace is reserved for the reporting matrix entry only.
- **Not tax advice.** The pack helps capture and structure SR&ED information. Eligibility determinations, filing decisions, and claim amounts require a qualified SR&ED consultant or tax advisor.
- **Contemporaneous records matter.** CRA can deny claims where records were clearly created after the fact. Capture TUs and evidence at the time of the work, not at claim time.
- **The 18-month deadline is hard.** Missing it means losing the claim for that fiscal year permanently.

## Skills (shipped by the capability, configured by this pack)

- `project-sred-tracker` — continuous TU/EX/ADV capture + evidence log + cost roll-up
- `project-sred-reviewer` — T661 audit-risk review; its verdict gates the advisor handoff
