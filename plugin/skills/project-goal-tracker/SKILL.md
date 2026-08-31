---
name: project-goal-tracker
description: "Track project objectives, goals, and KPIs as the outcome layer over milestones. Use for setting or reviewing goals, recording KPI readings, checking progress against targets, linking milestones to objectives, or supplying outcome snapshots to reports. All writes route through project-state; attainment and trend are derived on read rather than stored."
---

> Codex adapter: Read [CODEX.md](../../CODEX.md) before using this skill.

# Project Goal Tracker

## Purpose

Milestones are **outputs** — "did we ship the thing." Objectives and KPIs are **outcomes**
— "did shipping the thing move the number we care about." This skill owns the outcome
layer: high-level objectives (meta / leadership / north-star), the KPIs that quantify them,
and the dated readings that show the trend.

Two file-per-entity kinds, with their public fields defined below:

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
1. Read bounded objective/KPI summary fields first (`limit=50`, stable cursor,
   optional status/horizon/category filters). Open full entities only for named
   details or the selected report scope.
2. For each objective, gather its KPIs (those in `key_results` **or** any KPI whose
   `delivers_to` points back to it). Compute each KPI's **attainment** and **trend**;
   the objective's attainment is the mean of its KPIs'.
3. Report: each objective with status + attainment, its KPIs (current vs target, trend),
   and any **unassigned** KPIs. Headline **coverage** = % of objectives with ≥1 KPI.

### Create an objective
Apply the materiality gate. Create only a shared outcome/commitment or an
explicit reasoned operator record; task-local implementation goals stay in the
active Codex task.

Emit an `objective.created` intent to `project-state` with `title`, `horizon`
(north-star|annual|quarterly), `category` (leadership|growth|operational|financial|mission),
`status` (default `on-track`), and optional `narrative`, `key_results`, `milestones`,
`confidence` (0..1), `target_date`. The id is `O<NN>-<slug>` (next NN).

### Create a KPI
Apply the same gate: the metric must be a durable shared/reporting outcome or an
explicit override, not a temporary task counter.

Emit a `kpi.created` intent with `metric`, `unit`, `baseline`, `target`, `current`
(defaults to baseline), `direction` (up|down), `cadence`, and optional `delivers_to`. The
id is `KPI-<NN>-<slug>`.

### Add a reading (the bread-and-butter op)
Emit a `kpi.reading.added` intent with the KPI `id`, `value`, optional `date` (defaults to
today) and `note`. `project-state` appends `{date, value, note?}` to `history` (one per
date — a same-date reading replaces that day's entry), and sets `current` + `as_of`. Prior
readings are never rewritten.

An exact same-date, same-value, same-note repeat is idempotent: return the
existing reading/event and do not append, increment, or update activity.

## Computed fields (on read — never persisted)

- **attainment** (0..1), direction-aware along `baseline → target`:
  - higher-is-better: `(current − baseline) / (target − baseline)`, clamped 0..1
  - lower-is-better: `(baseline − current) / (baseline − target)`, clamped 0..1
- **trend** from the last two readings: *improving* if the latest move is toward target,
  *declining* if away, *flat* if equal, *unknown* with < 2 readings.
- **objective attainment** = mean of its KPIs' attainment.

## Surfaces

- **Optional Goals view** — a separately installed compatible viewer may render
  objective cards from these canonical files. The public package does not bundle
  that viewer; use the computed fields above in file/report workflows.
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
