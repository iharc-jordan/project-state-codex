---
kind: portfolio-card
variant: operator
member: "{{member.id}}"
as_of: "{{snapshot.date}}"
source_rev: "{{snapshot.source_rev}}"
trust: "{{trust.level}}"              # from harvest freshness: green | amber | red
measure_sets: {{scorecard.sets}}
generated_at: "{{now}}"
generated_by: portfolio-reviewer
regenerable: true
---

# {{member.name}} — battle card

**{{member.member_kind}} · {{member.priority}} · owner {{member.owner}} · phase {{snapshot.project.current_phase}} · {{member.status}} since {{member.added}}**
As of {{snapshot.date}} (rev {{snapshot.source_rev}}). Trust: **{{trust.level}}** — {{trust.reason}}.

| Health | Performance | Innovation | Portco |
|:--:|:--:|:--:|:--:|
| {{sets.health.status}} {{sets.health.trend}} | {{sets.performance.status}} {{sets.performance.trend}} | {{sets.innovation.status}} {{sets.innovation.trend}} | {{sets.portco.status}} {{sets.portco.trend}} |

## The number that matters this week

**{{next_deadline.label}} — due {{next_deadline.date}}, {{next_deadline.days}} days, status {{next_deadline.status}}.**
{{slip_forecast.line}}

## Measures

{{#each sets}}
**{{label}} — {{status}}, {{trend_word}}**

| Measure | Value | Trend | Threshold | Evidence |
|---|---|---|---|---|
{{#each measures}}
| {{label}} | {{value_or_not_measurable}} | {{trend}} | {{threshold_chip}} | `{{evidence}}` |
{{/each}}
{{/each}}

## What it needs (asks to the member)

{{#each asks}}
1. {{question}}
{{/each}}

## What it blocks / what blocks it

{{#each dependencies}}
- **{{id}}** {{direction}} {{other_member}} {{other_ref}} ({{type}}, {{status}}{{at_risk_note}})
{{/each}}

## Open findings naming this member

{{#each findings}}
- **{{id}}** {{type}}, {{severity}} — {{status_line}}
{{/each}}

## Our stance

**{{stance.value}}** — decided {{stance.date}} ({{stance.decision}}), review by {{stance.review_by}}.
**Evidence has moved since:** {{stance.evidence_moved_line}}

---
_Every line above traces to snapshot {{member.id}}/{{snapshot.date}}, scorecard {{scorecard.date}}, or a portfolio entity by id. Nothing here was narrated beyond state. Regenerate with `/portfolio-reviewer cards {{member.id}}`._
