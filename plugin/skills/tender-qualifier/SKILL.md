---
name: tender-qualifier
description: "Score or qualify tenders only when tender-intelligence is enabled with applicable profiles and tender records, the operator explicitly requests it, or tender-harvester emits the configured trigger. Preserve deterministic/semantic evidence, requirement extraction, dedupe, and eligibility-confidence outputs. Never infer capability activation or mark compliance without human approval."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# tender-qualifier

Turn discovered tenders into scored, explained, human-decidable opportunities. Reads and writes tender entities through the `project-state` memory layer only.

## Preconditions

Locate the facility; confirm the package is enabled; load enabled `tenders/profiles/*.yaml` (respect `profiles_enabled` in the package block; skip `enabled: false` profiles). If no profiles exist, stop and offer to create them from `templates/tender/tender-profile-template.yaml`.

## Sub-actions

### `score` (default)

Target set: tenders with `matching.relevance_score: null`, tenders whose source data changed since last scoring, or an explicit id list.

**Stage 1 — deterministic filtering** (per profile):

1. **Hard exclusions first.** Any `exclude.exact_phrases` hit in title or synopsis → profile ineligible for this tender; record the exclusion term.
2. **Timeline gate.** Days remaining until `closing_at` < `commercial.minimum_days_remaining` → gate failure (tender can still score for visibility, but recommendation caps at Watch; record the gate).
3. **Geography gate.** Regions intersect `geography.preferred` (or tender is remote-eligible and profile accepts remote) → pass; regions in `geography.excluded` → fail.
4. **Inclusion signal.** Count `include.exact_phrases` and `include.concepts` matches across title + synopsis; match commodity codes when the source provides them; match buyer type against `buyers.preferred_types`.
5. A tender with zero inclusion signal on every profile → `matching.relevance_score: 0–15` band, no semantic pass, recommendation Dismiss (auto-dismissal still requires the pipeline's dismissal flow — never delete).

**Stage 2 — semantic matching** (profiles that survived stage 1):

Compare title + synopsis against the profile's concept set as a capability description. Produce, per profile: matched capabilities; the specific evidence passages (verbatim quotes from tender text); confidence 0–1; missing information; likely service category. Only source text may be cited — never invent scope.

**Score composition** (spec §11.4, weights from the best-fit profile):

```text
20% title and synopsis match       20% capability alignment
15% mandatory eligibility          10% reference-project fit
10% buyer fit                      10% geography and delivery fit
 5% commercial attractiveness       5% timeline feasibility
 5% strategic value
```

Before documents are retrieved, the eligibility/reference components are scored from available signal at reduced confidence — the entity keeps `qualification.status: preliminary` and the card carries *"Preliminary match — full documents not yet reviewed."*

Also compute `strategic_value_score` (buyer strategic value, repeat-business potential, reusable-IP potential) and `urgency_score` (days remaining, mandatory-meeting proximity, question-deadline proximity).

**Recommendation thresholds:** 85–100 Act now · 70–84 Review · 55–69 Watch · 35–54 Low priority · 0–34 Dismiss. A mandatory disqualifier overrides any score (recommendation Dismiss with reason).

**Write-back** (memory layer): `matching.*` (profiles ranked best-first, matched_terms, scores, evidence[]), `summary.generated_summary` (2–3 sentences, sourced), and log `tender.scored`. If score ≥ 85, note in output that the notifier's immediate-alert rule fires. Suggest `tender-pipeline` transitions (`preliminary_match`, `documents_required`).

### `qualify`

Run after a document package is linked (`documents.retrieved: true`). Steps:

1. Read the linked documents via `documents/index.yaml` (respect `access_classification` — quote restricted documents only into the entity/analysis, never into public surfaces).
2. Run `extract` (below) if not already done.
3. Evaluate spec §11.3: mandatory compliance; reference requirements; personnel requirements; budget suitability; contract conditions; schedule feasibility; delivery geography; security requirements; strategic fit.
4. Classify every mandatory requirement: `met` | `likely_met` | `unmet` | `unknown` — each with a document + section/page citation.
5. Any `unmet` mandatory → `qualification.status: disqualified`, log `tender.disqualified` with the reason; recommendation Dismiss regardless of relevance score:

```yaml
matching: { relevance_score: 91 }
qualification:
  status: disqualified
  reason: "Mandatory security clearance cannot be met."
```

6. Otherwise → `qualification.status: qualified` **candidate**: write findings, set `human_approved: false`, log `tender.qualified`, and prompt the reviewer. **`human_approved: true` may only ever be set by a person, via the pipeline's review step.**
7. Re-run scoring with document-grounded eligibility components; update scores and evidence.

### `extract`

Structured requirement extraction from a retrieved package (spec §10.10). Output written to `qualification.mandatory_requirements[]` and a `requirements` block on the entity, every item carrying `source_document`, `section`, and `page` where determinable:

mandatory eligibility · submission requirements (format, copies, portal, envelope) · technical requirements · experience requirements · financial requirements (bonding, statements) · insurance requirements (types, limits) · security requirements (clearances, data residency) · certifications · reference-project requirements (count, comparability, recency) · mandatory meetings (date, attendance rule) · question deadline · submission deadline (with timezone) · required forms · evaluation criteria (with weights when stated) · pricing structure · contract duration · renewal options · ownership and IP clauses.

Distinguish **fact** (quoted) from **inference** (flagged `inferred: true` with rationale). Anything not found is listed in `qualification.missing_information[]` — never invented. Extracted deadlines are offered to `tender-pipeline` as pursuit milestones.

### `dedupe`

Within-facility duplicate detection, cascade order (spec §10.6):

1. exact source ID match → same tender, merge source blocks silently (log `tender.merged`);
2. solicitation-number match;
3. buyer + solicitation-number match;
4. normalized title + closing-date match;
5. canonicalized source URL match (strip tracking params, normalize host);
6. semantic similarity of title + synopsis (propose only, threshold high).

Levels 2–6 **propose** a merge for human confirmation; only level 1 merges automatically. Merge behavior: keep the earlier entity id; union `sources[]` (all references preserved); prefer the richer field values; union evidence; append a merge note; log `tender.merged` with both ids. The dismissed duplicate file is replaced by a 3-line tombstone entity (`kind: tender`, `workflow.status: closed`, `merged_into: <id>`) so ids never dangle.

## AI-output requirements (binding, spec §11.6)

Every assessment must: cite the tender text or document section it relies on; distinguish facts from inference; state uncertainty explicitly; avoid inventing requirements; show source document and page; and never mark a tender fully compliant without human approval. Material judgments stop at a draft for human review — same discipline as every external send in the substrate.

## Output format

```
Scored 4 tenders — <facility>

  91  Act now   t-2026-0128  AI Strategy and Workflow Modernization Services — City of Example
                profiles: atomic47-ai-data (0.92), atomic47-digital-transformation (0.81)
                evidence: "…develop an artificial intelligence strategy and modernize
                          approval workflows…" (notice synopsis)
                gates: none failed · preliminary — documents not yet reviewed
  72  Review    t-2026-0129  …
  48  Low       t-2026-0130  …
  12  Dismiss   t-2026-0131  Janitorial Services — excluded term "custodial", no profile signal

  → t-2026-0128: retrieve documents (login required, MERX) — create task?
```

## Boundaries

Scoring and analysis only. Status moves, decisions, dismissals, tasks → `tender-pipeline`. Change detection → `tender-monitor`. No direct facility writes — memory layer only.
