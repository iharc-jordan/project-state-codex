---
kind: portfolio-card
variant: exec-set
set: "{{set.id}}"
as_of: "{{collect.date}}"
review: PL
generated_by: portfolio-reviewer
---

# {{set.label}} across the portfolio — {{period_long}}

**{{set.question}}** {{set.verdict}} {{set.distribution}}.

## Portfolio measures

| Measure | Portfolio value | How computed | Worst member / note |
|---|---|---|---|
{{#each measures}}
| {{label}} | {{portfolio_value_or_not_measurable}} | {{rollup_rule}} | {{worst_or_note}} |
{{/each}}

## By member

| Member | Status | Trend | Driver |
|---|:-:|:-:|---|
{{#each members}}
| {{id}} | {{status}} | {{trend}} | {{driver}} |
{{/each}}

## What changed since {{previous_period}}

{{#each movers}}
- {{line}}
{{/each}}

## The exec ask

{{ask}}

---
_Rolled up from the {{set.label_lower}} rows of the member cards, {{collect.date}}. A set card that ends without a question is a dashboard; this one ends with one._
