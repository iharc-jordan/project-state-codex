---
name: project-archive
description: Project closeout and archival drive. Generic core handles final reports, lessons summary assembly, archive directory creation, audit-trail finalization. Funder/customer-specific closeout items (PIC final reports, FTE confirmation, holdback release, MPA close) come from the active pack's archive profile. PIC pack ships the v1.x closeout flow. Client-services pack ships customer-final-deliverable + sunset workflow. Use whenever the user says 'close the project', 'closeout', 'final report', 'wrap up', 'submit final reports', 'archive the project', 'ready to close', 'holdback release', 'project end', or any request related to the closeout phase.
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Archive (v2.0 — generic core + pack-driven closeout)

Drives the closeout phase: final reports, lessons-learned summary, IP final reporting, financial reconciliation, archive directory creation, audit-trail finalization.

In v2.0 the skill splits into a **generic closeout core** and **pack-driven closeout items**:

**Generic core** (always runs):
- Final lessons-learned summary assembled from `lessons-learned/`
- All milestones marked complete or explicitly archived-incomplete
- Audit trail finalized (last `activity.ndjson` entry timestamped)
- Archive directory created at `project-state/archive-<closeout-date>/`
- Final state.json snapshot
- Closeout README pointing future readers at the archived state

**Pack-driven items** (from active pack's `archive.yaml` profile):
- PIC pack: PIC final report per consortium member (~90-day pre-close template distribution, drafts by close date, finalized 30 days post-close), IP final reporting workflow, FTE confirmation, holdback release tracking, Annual Questionnaire close-out.
- Client-services pack: customer final deliverable handover, customer signoff on completion, post-engagement support window setup, customer documentation freeze.
- Open-source pack: archive notice on README, contributor recognition publication, governance handoff or sunset declaration.

## What it owns

- Closeout phase orchestration (gate-in: project end date reached; gate-out: all required artifacts complete)
- Final-report drafting per the active pack's template(s)
- Lessons-learned summary
- Archive directory + final state snapshot
- Closeout audit trail

## What it does not own

- Submitting final reports — drafts only, PL signs off
- Releasing holdback (or any payment) — humans coordinate that with the funder
- Defining what "closed" means — the gate-out criteria are in the phase manifest + pack profile
- Closing an increment — that is `project-phase-gate`; this skill produces the *artefacts* of a
  closure, not the state transition

## Closing a project vs. closing an increment (v2.1)

Branch once, on `state.json:lifecycle`.

First run the `project-state` reconciliation dry-run. Terminal closeout requires
consistent required objectives, milestones, gates, phase authority, and reports.
Continuous closeout requires a meaningful current increment and freezes only
that increment. Missing, stale, or contradictory data is a finding and blocks
the close; never derive a convenient phase or invent an increment. Exact repeat
requests for an already closed boundary return its existing records without
another report, snapshot, counter change, or activity event.

**`terminal` (or absent) — unchanged in every respect.** Final report at
`reports/final-report-<date>.md`, archive directory at `project-state/archive-<closeout-date>/`, the
full pack-driven closeout. This is the overwhelming majority of facilities and nothing about their
path is different.

**`continuous` — the artefacts belong to the increment.** The word *final* is a claim, and on a
facility with work still coming it is a false one. A second increment producing a second
`final-report-<date>.md` leaves two "finals" with nothing indicating which one closed what.

| | terminal | continuous |
| --- | --- | --- |
| Closeout report | `reports/final-report-<date>.md` | `increments/INC-<NN>-<label>/reports/closeout-<date>.md` |
| Lessons summary | assembled facility-wide | assembled for the increment, from lessons dated within its span |
| Archive directory | `archive-<closeout-date>/` | **not created** — the facility is not being archived |
| Final state snapshot | yes | frozen `phases/` + `gates.json`, written by `project-phase-gate` |
| Pack-driven items | all | those the pack's `archive.yaml` marks `per_increment: true` |

After writing the report, hand back to `project-phase-gate close_increment` with its path, so the
increment manifest records `closeout_report` and the freeze happens under one lock.

**Never draft a closeout report for a continuous facility without `closed_what`.** Ask for it first —
one or two sentences on what this closure closed *and what it did not* — and open the report with it.
That sentence is what makes a later reopening legible as the next increment rather than as an admission
that this closure was a formality, and it is the single cheapest thing in the whole continuous design
(spec §9).

**Genuine sunset is still available.** `client-engagement-default` keeps `05-archive` and
`open-source-default` keeps `04-archived` after their increment boundaries, precisely so that a
continuous facility can still actually end. Reaching those phases runs the full terminal closeout,
archive directory and all. Continuous means *not necessarily ending*, not *unable to end*.

The lifecycle and increment rules above are authoritative for the public package.

## Migration from v1.x

The skill name is unchanged. The PIC-specific closeout items (final report template, FTE confirmation, holdback release, ~90-day pre-close window, 30-day post-close finalization) move from hard-coded to `packs/pic-pcais/profiles/archive.yaml`. Existing closeout work-in-progress is unchanged.

For non-grant projects the generic closeout core still runs (lessons summary, archive directory, final snapshot) — pack-driven items contribute additional steps.
