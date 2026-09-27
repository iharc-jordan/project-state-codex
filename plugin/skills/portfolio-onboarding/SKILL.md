---
name: portfolio-onboarding
description: "Set up portfolio oversight on an org-level project — 'set up the portfolio', 'enable portfolio', 'add member projects'. Asks for the workspace root and subject, then admits members one at a time."
map:
  tier: capability
  stage: ingest
  inputs: [operator, files, projects]
  reads: [manifest]
  writes: [manifest, portfolio, log]
  calls: [project-state, project-scaffolder, portfolio-collector]
---

# portfolio-onboarding — the enable flow

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> Guided enablement of the portfolio capability on an org-level Project — the project whose subject is a set of other projects. Gathers the REQUIRED workspace_root (the collector's reach) and subject conversationally; calls the memory layer's `enable portfolio` (manifest block, portfolio/ directories, state/portfolio.json, the pack's weekly collect); then seeds the member registry from three merged sources — discovery of */project-state/ under the workspace, an imported master log (xlsx/csv/markdown table), and the kanban registry.json — proposed and confirmed before writing. Admits members one at a time by handing off to project-intake. Trigger on 'set up a portfolio', 'enable portfolio', 'import my master log', 'add a project to the portfolio', 'admit the pilot project', 'pause this member', or when the digest reports portfolio.not-initialized or portfolio.member-silent. Refuses without workspace_root and subject. Never scaffolds or writes into a member. Routes every write through project-state.

Make the portfolio capability active on one org-level Project, with a registry that reflects
what exists on disk and what the operator's own master log says is in the hopper. Enable
without a reach is refused — `workspace_root` is this capability's `fiscal_year_end`.

## Step 1 — Preconditions

- Locate the host `project-state/` (walk up from cwd). None → this Project does not exist yet:
  point at `project-intake` ("create the portfolio project first, then enable portfolio on
  it") and stop.
- Already enabled → report status and offer only Steps 4–6.
- If the host project is itself listed in another portfolio's registry under the same
  workspace, say so and ask before continuing.

## Step 2 — Gather (one conversational pass)

**Required:** `workspace_root` — pre-fill with the parent of this project-state's parent and
confirm; show the `*/project-state/manifest.yaml` hits under it so the reach is visible before
it is agreed. `subject` — 1–2 sentences, pre-filled from the manifest's one-liner.

**Offered with defaults:** `discovery` (auto) · `snapshot_cadence_days` (7) ·
`silence_threshold_days` (14) · `harvest_stale_after_days` (3) · `index` windows (30 / 90) ·
`answers.keep` (ask) · pack (`portfolio-default`).

## Step 3 — Enable

`project-state enable portfolio` with the gathered config. That verb takes the manifest lock,
writes the block, scaffolds `portfolio/{members,snapshots,index,understanding,dependencies,
findings,answers,reports}`, seeds `state/portfolio.json`, seeds and arms the weekly collect
through `project-automator`, logs `capability.enabled`.

## Step 4 — Seed the registry (three sources, merged, always confirmed)

1. **Discovery.** Every `<dir>/project-state/manifest.yaml` under `workspace_root`, except this
   project → an `active` member: id = directory slug, name from its manifest, `member_kind`
   guessed and shown as a guess, `location: {type: local, path}`, `owner` = its lead when that
   person exists in this project's `people/`.
2. **Master log import** when the operator names a file (xlsx, csv, markdown table). Show the
   column → field mapping and the columns that cannot be mapped. Each row → a `proposed`
   member with `source_row` provenance; a row matching a discovered directory merges into it
   (discovered facts win; the conflict is shown).
3. **Kanban registry** `<workspace_root>/registry.json` when present.

Existing rows (a hand-rolled registry, a previous run) are shown side by side and never
overwritten silently. On confirmation, write through `project-state`
(`portfolio.member.added`). Never invent a member; never activate a row with no substrate.

## Step 5 — Start with one

Show the hopper and offer to admit **exactly one** proposed member now: run `project-intake`
for it under `workspace_root/<slug>/`, then activate its row with the new location. The rest
stay proposed.

## Step 6 — First collect and report

Run `portfolio-collector all` so the index and the understanding pages exist. Report: config,
members written (active / proposed), the one admitted, anything from an existing registry the
schema did not carry ("not migrated — tell us if it matters"), and how to ask:
`/portfolio-reviewer query "…"`.

## Also: pause / resume / retire a member

`portfolio-onboarding pause <id> --reason …` flips the row so silence stops reading as risk;
`resume` and `retire` likewise. Row edits only; nothing in the member is touched.

## Discipline

- Refuse on missing `workspace_root` or `subject`; refuse on prefix collision.
- Read-only toward members: discovery reads manifests and nothing else.
- All writes through `project-state`; no state, no locks here.
