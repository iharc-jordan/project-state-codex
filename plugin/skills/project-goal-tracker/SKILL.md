---
name: project-goal-tracker
description: "Set and track objectives and KPIs — 'set a goal', 'add a KPI', 'record this month's numbers', 'are we on track', 'what should we measure'. Offers the work type's common KPIs; always asks for baseline and target."
map:
  tier: P1
  stage: keep
  reads: [objectives, milestones, manifest]
  writes: [objectives]
---

# Project Goal Tracker

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Track objectives, goals, and KPIs — the outcome layer over milestones. Milestones track outputs (did we ship it); this skill tracks outcomes (did shipping it move the number). Use whenever the user says 'set a goal', 'add an objective', 'track a KPI', 'what are our goals', 'how are we tracking against target', 'add a reading for <metric>', 'update the cycle-time metric', 'are we on track for the annual objective', 'set a north-star', 'record this month's numbers', 'link this milestone to a goal', or any request to read or write objectives/KPIs. Objectives live in objectives/O<NN>-<slug>.yaml (the aim), KPIs in kpis/KPI-<NN>-<slug>.yaml (baseline → current → target with a dated history). Also trigger when project-funder-reporting (board/investor packs) needs the KPI snapshot for a metrics section, or project-status-reporter wants outcome progress. All writes route through project-state; attainment and trend are computed on read, never stored.

## Purpose

Milestones are **outputs** — "did we ship the thing." Objectives and KPIs are **outcomes**
— "did shipping the thing move the number we care about." This skill owns the outcome
layer: high-level objectives (meta / leadership / north-star), the KPIs that quantify them,
and the dated readings that show the trend.

Two file-per-entity kinds (full schema in `docs/SCHEMA.md`):

- **Objective** `objectives/O<NN>-<slug>.yaml` — the qualitative aim. Owns a basket of KPIs
  (`key_results`), an explicit operator `status`, and optionally the `milestones` that
  advance it.
- **KPI** `kpis/KPI-<NN>-<slug>.yaml` — one metric with `baseline`, `target`, `current`,
  `direction` (up/down better), `cadence`, and an append-only `history` of `{date, value}`
  readings. Optionally `delivers_to` an objective.

This is the **lightweight** model: KPIs are the centre of gravity (you can track metrics
with no objective at all — they surface as "unassigned"), and objectives are an optional
grouping with a rollup. There is deliberately no quarterly OKR ceremony, no graded
key-result scoring — just baseline → current → target, a trend, and a status the operator sets.

## What this skill does NOT do

- It does not invent targets or judge whether a goal is "good." It records the operator's aim.
- It does not write files directly — every create/update/reading routes through
  `project-state` (the memory layer), which owns the lock + activity-log append.
- It does not compute or store attainment/trend. Those are derived on read (see below).

## Trigger phrases (priority order)

1. "set a goal" / "add an objective" / "new north-star"
2. "track a KPI" / "add a metric"
3. "add a reading for <metric>" / "this month <metric> is <value>" / "record this month's numbers"
4. "what are our goals?" / "how are we tracking?" / "show the KPI dashboard"
5. "are we on track for <objective>?"
6. "link <milestone> to <objective>"
7. Any pack/skill fetching the KPI snapshot for a report

## Operations

### Read — "what are our goals / how are we tracking?"
1. Read `objectives/*.yaml` and `kpis/*.yaml`.
2. For each objective, gather its KPIs (those in `key_results` **or** any KPI whose
   `delivers_to` points back to it). Compute each KPI's **attainment** and **trend**;
   the objective's attainment is the mean of its KPIs'.
3. Report: each objective with status + attainment, its KPIs (current vs target, trend),
   and any **unassigned** KPIs. Headline **coverage** = % of objectives with ≥1 KPI.

### Create an objective
Emit an `objective.created` intent to `project-state` with `title`, `horizon`
(north-star|annual|quarterly), `category` (leadership|growth|operational|financial|mission),
`status` (default `on-track`), and optional `narrative`, `key_results`, `milestones`,
`confidence` (0..1), `target_date`. The id is `O<NN>-<slug>` (next NN).

### Create a KPI
Emit a `kpi.created` intent with `metric`, `unit`, `baseline`, `target`, `current`
(defaults to baseline), `direction` (up|down), `cadence`, and optional `delivers_to`. The
id is `KPI-<NN>-<slug>`.

### Suggest KPIs for this kind of work
When the operator asks "what should we track?" — or a Goals-tab suggestion chip sends *Track "<title>"…* —
read the **primary work pack's** `seeds/kpis.yaml` (`packs/<project.kind>/seeds/kpis.yaml`;
`docs/PROJECT-TYPES-SPEC.md` §5.3.2). Offer the ones not already tracked, each with its unit and
direction. A seed is a *metric shape*, never a number: **always ask for the baseline and target** before
emitting `kpi.created`, and never invent them from the pack. Onboarding never writes these — goals are
this skill's.

### Add a reading (the bread-and-butter op)
Emit a `kpi.reading.added` intent with the KPI `id`, `value`, optional `date` (defaults to
today) and `note`. `project-state` appends `{date, value, note?}` to `history` (one per
date — a same-date reading replaces that day's entry), and sets `current` + `as_of`. Prior
readings are never rewritten.

## Computed fields (on read — never persisted)

- **attainment** (0..1), direction-aware along `baseline → target`:
  - higher-is-better: `(current − baseline) / (target − baseline)`, clamped 0..1
  - lower-is-better: `(baseline − current) / (baseline − target)`, clamped 0..1
- **trend** from the last two readings: *improving* if the latest move is toward target,
  *declining* if away, *flat* if equal, *unknown* with < 2 readings.
- **objective attainment** = mean of its KPIs' attainment.

## Surfaces

- **Goals view** (`/goals` in the kanban) renders objective cards with KPI sparklines
  (baseline + target guide lines), trend, attainment bars, and an "add reading" affordance.
- **Board/investor packs** read `kpis/*.yaml` for the monthly update's metrics section
  (see `packs/board-investor/profiles/funder-reporting.yaml`).
- **Wiki** `[[O01]]` / `[[KPI-01]]` resolve to objective/KPI entities and earn backlinks,
  so a narrative page can explain a goal and the goal links back.

## Examples

- "Our north-star is zero hand-written reports" → create objective `O01`, horizon
  `north-star`, category `mission`.
- "Track shipped skills: started at 18, target 40, now 30, higher is better" → create KPI
  `KPI-01-skills` with baseline 18, target 40, current 30, direction up, delivers_to O01.
- "Skills are at 31 this month" → add a reading `{value: 31}` to `KPI-01-skills`.
