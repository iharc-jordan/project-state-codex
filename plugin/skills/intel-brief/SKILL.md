---
name: intel-brief
description: "Write the recurring competitive brief for an audience (exec, sales, product) — 'competitive brief', 'what changed with competitors this month', 'intel digest'. Built from the period's change events and new claims."
map:
  tier: capability
  stage: generate
  inputs: [operator]
  reads: [intel, manifest]
  writes: [intel, log]
  produces: [intel-competitive]
---

# intel-brief — the period's competitive picture, honestly sized

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The intel capability's competitive brief (OCI §7.6 competitive-brief) — a recurring digest for a named audience (exec, sales, product) built from the period's change events (noise suppressed), new material claims and deal briefs: what changed · why it matters · deals affected · recommended actions · what we are watching next. Prioritizes significance over volume, states the period, carries provenance (claim and change ids on every line), and is allowed to say 'nothing material changed this period'. Usage: 'intel-brief [--period YYYY-MM] [--audience exec|sales|product]'. Trigger on 'competitive brief', 'what changed with competitors this month', 'brief leadership on the competitive picture', or the intel-monthly-competitive-brief matrix entry. Writes intel/reports/brief-YYYY-MM.md through project-state; PL review before it leaves the Project.

A brief that always finds five things is a brief nobody reads by month three. This one
reports what the claim set and the change events actually say about the period, and says
*nothing material changed* when that is true. Spec: `docs/INTEL-CI-SPEC.md` §5.4, OCI §7.6.

## Inputs

Via `project-state`: the period (default: the previous calendar month); `intel/changes/`
with `detected_at` in the period and `significance` material or notable — **noise is
suppressed by default**; claims created in the period with `material: true`; deal briefs
generated in the period (`intel/deals/*/brief.md` frontmatter); the audience.

## Sections

1. **What changed** — one line per material change, then notable: date · entity · change
   type · significance · the delta as claim ids `[before → after]` and the change id.
2. **Why it matters** — for this audience: sales sees positioning and objections; product
   sees feature and product-gap; exec sees market, funding, leadership, pricing.
3. **Deals affected** — deal briefs in the period naming the changed competitor; open tenders
   where the competitor is a known bidder (when the tender capability is enabled).
4. **Recommended actions** — by team, each traceable to a change or claim.
5. **What we are watching next** — open unknowns on P0 competitors, contested categories,
   claims about to cross their half-life.
6. **What this brief does not cover** — entities out of scope, categories with no claims.

## MUST

Prioritize significance over volume · state the period covered · cite ids on every material
line · return the one-line brief when `material_changes == 0` rather than padding · never
present an inferred or hypothesis claim in the register of fact.

## Output

Write `intel/reports/brief-YYYY-MM.md` from `templates/brief.md`; record its hash in
`state/intel.json → projections` and stamp `last_brief`; log `intel.brief.generated`
`{period, material_changes}`. Re-render the Competitive report. The matrix entry carries
`review: PL`: the brief is a file until a person sends it, through `project-notifier`
(Slack) or a Gmail draft, logged `intel.approval.logged`.
