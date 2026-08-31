---
name: project-onepager
description: "Own audience-specific one-pagers, briefs, deep-dives, and whitepapers from Project State. Invoke only for an explicit audience-specific document request, a due enabled onepager matrix entry, or an active pack profile that requires it. Preserve recipes, provenance, established paths, and change reporting. Draft once per source event and period for human review; never send or publish automatically."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project One-Pager (documents as views over state)

Long-form documents — from a 400-word leave-behind to a structured whitepaper —
generated from the substrate, framed for an audience, and regenerable. The core
principle applied to prose: **state is the source of truth; when a document
disagrees with state, regenerate the document.**

Two invariants that make these documents worth more than nicely written PDFs:

1. **Receipts.** Every substantive claim cites the record it came from —
   `[M10]`, `[R-09]`, `[decision 2026-07-06]`, `[kpi:weekly-actives]`. In the
   rendered HTML these are small provenance chips; in a dispute, every sentence
   is auditable back to a typed record.
2. **Regeneration.** A document is produced *as-of* a state snapshot recorded in
   its recipe. Re-running the recipe against newer state produces a fresh
   document plus a **change note** (what moved since last generation). Frozen
   copies are for sending; the recipe is the living object.

## The recipe (stored in `reports/custom-defs/<slug>.yaml`)

```yaml
recipe: onepager                     # discriminator for this skill
slug: funder-onepager                # output naming
audience: funder                     # resolves a voice profile (see below)
altitude: onepager                   # onepager | brief | deepdive | whitepaper
purpose: >                           # one sentence: what this doc must achieve
  Reassure the funder the project is on track and surface the M10 decision.
evidence:                            # selection over state (all optional)
  objectives: true                   # objectives/ + kpis/
  milestones: { include: all }       # or: [M07, M10] / { phase: current }
  decisions: { last_days: 90 }
  risks: { min_severity: high }
  activity: { last_days: 30 }        # momentum from logs/activity.ndjson
  documents: []                      # extra corpus for deepdive/whitepaper
omit: [internal-costs, people-names] # audience-safety filters (profile adds more)
sections: default                    # or explicit section list (whitepaper)
last_generated: null                 # skill maintains: {at, activity_seq, artifact}
```

## Altitude ladder (same evidence tree, different pruning)

| altitude | length | shape |
|---|---|---|
| `onepager` | ~400 words, 1 page | headline claim → 3 proof points (with receipts) → one honest risk → the ask |
| `brief` | 2–3 pages | + milestone table, decision highlights, KPI movement |
| `deepdive` | 5–8 pages | + approach/architecture (wiki + docs corpus), full risk posture, roadmap |
| `whitepaper` | thesis-driven | outline first → per-section drafts → assembly → consistency pass; diagrams per section; run as a queued job, not one prompt |

## Audience profiles

Resolution order: pack profile `packs/<pack>/profiles/onepager.yaml` (audience
key) → built-in defaults below. A profile sets: `tone`, `leads_with`,
`must_include`, `must_omit`, `provenance` (chips | footnotes | none),
`format` (html+pdf | docx | md), `signoff_required`.

Built-in defaults when no pack profile covers the audience:

- **funder** — formal, milestones/deliverables-forward, spend only if asked,
  no internal risk language beyond the register's own wording; provenance: footnotes.
- **exec / board** — outcomes over outputs: objectives, KPI deltas, the crucial
  few, decisions owed, one ask; provenance: chips.
- **technical** — architecture and approach forward, honest constraint list,
  links into wiki/docs; provenance: chips + repo paths.
- **public** — story-mode, no internal identifiers, no numbers not already
  published; provenance: none (claims must still be state-true).

`omit` filters are a safety contract, not a suggestion: content matching them
must not appear in any form, including paraphrase.

## Workflow

1. **Resolve** — load recipe (or build one from the user's ask and save it);
   resolve audience profile; read bounded summaries through `project-state`,
   then open only evidence selected by the recipe. Deep full-ledger reads are
   reserved for an explicitly requested deepdive/whitepaper.
   Compute the deterministic event identity from source event, reporting period,
   this owner, canonical artifact path, recipe, and exact source revision. If the
   same identity and artifact/card already exist, return them without regenerating.
2. **Draft** — write the document at the requested altitude. Every claim that
   states a fact about the project carries a provenance marker. The honest-risk
   section is mandatory at every altitude except `public` (where it becomes
   "what we're working on") — documents without acknowledged risk read as
   marketing and die in diligence.
3. **Render** — fill `templates/onepager/onepager-template.html` (terracotta
   document theme, print CSS). Artifact: `reports/onepagers/<YYYY-MM-DD>-<slug>.html`.
   PDF (when requested/profiled): headless Chrome `--print-to-pdf` over the HTML.
4. **Queue** — emit an outbox card into `outbox/queue/` (kind: `onepager`,
   artifact path, audience, signoff role from profile). **Never** publish, mail,
   or post directly — approval routes to `project-blog-publisher`,
   `project-website-publisher`, or `project-notifier`.
5. **Record** — for a new identity only, update recipe `last_generated`
   (timestamp, activity-log sequence, artifact path); append the existing
   `onepager_generated` event with the deterministic canonical `id`.
6. **Regenerate** (on re-run) — diff current state against `last_generated`
   markers; produce the fresh artifact plus a change note (moved milestones,
   new/closed decisions and risks, KPI deltas) prepended to the outbox card.

## What it owns / doesn't

Owns: recipes, drafting, rendering, provenance, regeneration diffs, the outbox
card. Doesn't own: cadence (reporting matrix), delivery (notifier/publishers),
approval (humans), pack voice profiles (packs).
