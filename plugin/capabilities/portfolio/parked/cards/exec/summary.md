---
kind: portfolio-card
variant: exec-summary
as_of: "{{collect.date}}"
period: "{{period}}"
members: { active: {{counts.active}}, proposed: {{counts.proposed}} }
sets: {{scorecard.sets}}
audience: "executive / board"
review: PL
generated_at: "{{now}}"
generated_by: portfolio-reviewer
---

# {{portfolio.name}} — executive summary, {{period_long}}

*{{counts.active}} active projects, {{counts.proposed}} waiting. Everything below is rolled up from each project's own records as of {{collect.date_long}}; nothing is estimated. Grey means the projects do not yet record what the measure needs.*

## Five questions

| Question | Answer this month | Set |
|---|---|---|
| Are the projects well run? | **{{q.health.verdict}}** {{q.health.sentence}} | Health |
| Are they delivering? | **{{q.performance.verdict}}** {{q.performance.sentence}} | Performance |
| Are they creating new knowledge? | **{{q.innovation.verdict}}** {{q.innovation.sentence}} | Innovation |
| Is capital where the thesis is? | **{{q.portco.verdict}}** {{q.portco.sentence}} | Portco |
| What needs a decision? | **{{decisions.count_word}}** — below. | — |

## Set roll-ups

| Set | Distribution | Portfolio measures | Movers since {{previous_period}} |
|---|---|---|---|
{{#each sets}}
| **{{label}}** | {{distribution}} | {{portfolio_measures}} | {{movers}} |
{{/each}}

## Capital and risk, declared

| Project | Stage | Thesis fit | Committed | Top risk score | Risk-adjusted exposure |
|---|---|:-:|--:|:-:|---|
{{#each capital}}
| {{member}} | {{stage}} | {{thesis_fit}} | {{committed}} | {{top_risk}} | {{exposure_band}} |
{{/each}}

Stage, fit and commitment are declared by the portfolio on each row; risk scores are the projects' own. Thesis fit weighted by commitment is {{fit_weighted}} / 5 — both numbers are declared on the same row by the same person, which is why the quarterly health pass re-reviews fit.

## Decisions this month

{{#each decisions}}
1. **{{subject}}** — {{question}} ({{ref}})
{{/each}}

---
_Draft under the review rule. Rolled up from the {{counts.active}} member cards of {{collect.date}}; every figure traces to a member snapshot, a scorecard cell, or a declared field on a portfolio row. Regenerate with `/portfolio-reviewer cards --exec`._
