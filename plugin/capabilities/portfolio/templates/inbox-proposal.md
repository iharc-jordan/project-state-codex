---
kind: portfolio-proposal
source: "portfolio:{{finding.id}}"
portfolio: "{{portfolio.project_slug}}"
finding_type: "{{finding.type}}"
severity: "{{finding.severity}}"
proposed_entity: "{{proposal.kind}}"          # risk | decision | milestone-note
dropped_at: "{{now}}"
dropped_by: portfolio-reviewer
---

# Portfolio proposal — {{finding.type}} ({{finding.id}})

**From:** the {{portfolio.name}} portfolio · **To:** {{member.name}} · **Severity:** {{finding.severity}}

## What the portfolio observed

{{finding.summary}}

Basis: `{{finding.basis}}`. Evidence, by snapshot:

{{#each finding.evidence}}
- {{member}} · snapshot {{snapshot}} · `{{ref}}`
{{/each}}

## What is proposed — for this project's people to decide

{{proposal.body}}

If you record a {{proposal.kind}} from this, give it `source: portfolio:{{finding.id}}` so the
portfolio can see it was accepted. If it does not apply, dismiss this file in the inbox with a
reason — the portfolio never re-drops the same finding.

_This file was written by the portfolio's reviewer into `documents/inbox/`. Nothing else in this
project was touched. Triage with `/project-inbox`._
