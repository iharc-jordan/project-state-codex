---
kind: portfolio-card
variant: portfolio
as_of: "{{collect.date}}"
members: { active: {{counts.active}}, proposed: {{counts.proposed}}, paused: {{counts.paused}}, retired: {{counts.retired}} }
findings_open: { urgent: {{findings.urgent}}, soon: {{findings.soon}}, ondeck: {{findings.ondeck}} }
generated_at: "{{now}}"
generated_by: portfolio-reviewer
---

# {{portfolio.name}} — the card above the cards

As of {{collect.date}} · {{counts.active}} active members, {{counts.proposed}} in the hopper · last collect {{collect.time}} · {{findings.total}} findings open, {{findings.urgent_word}}.

## Attention order this week

Ranked by urgent findings, then stance-versus-evidence tension, then slip forecast. Computed; argue with it.

{{#each attention}}
1. **{{member}}** — {{why}} ({{finding_ids}}). {{action}}
{{/each}}

## Members

| Member | Kind | P | Phase | Milestones | Health | Perf | Innov | Portco | Next deadline | Trust | Stance | Moved? |
|---|---|:-:|---|:-:|:-:|:-:|:-:|:-:|---|:-:|---|:-:|
{{#each members}}
| {{id}} | {{member_kind}} | {{priority}} | {{current_phase}} | {{milestones}} | {{sets.health}} | {{sets.performance}} | {{sets.innovation}} | {{sets.portco}} | {{next_deadline}} | {{trust}} | {{stance.value}} | {{stance.evidence_moved}} |
{{/each}}

⚪ not measurable · trust = harvest freshness of the snapshot the row is built on

## Hopper

| Proposed | Kind | Origin | Waiting | What it would take |
|---|---|---|:-:|---|
{{#each hopper}}
| {{id}} | {{member_kind}} | {{origin}} | {{days_waiting}} d | {{cost_sentence}} |
{{/each}}

## Findings ledger (open)

| Id | Type | Sev | Members | Since | Status |
|---|---|:-:|---|---|---|
{{#each findings.open}}
| {{id}} | {{type}} | {{severity}} | {{members}} | {{first_seen}} | {{status_line}} |
{{/each}}

## Measurability

| Set | Measurable now | Blocked by |
|---|:-:|---|
{{#each measurability}}
| {{set}} | {{measurable}} | {{blocked_by}} |
{{/each}}

## Next 14 days, all members

| Date | Member | Deadline | Owner |
|---|---|---|---|
{{#each deadlines_14d}}
| {{date}} | {{member}} | {{label}}{{status_note}} | {{owner}} |
{{/each}}

---
_Rendered from portfolio/registry.yaml, the latest snapshot per member, the latest scorecard, portfolio/findings/ and each member's stance decision. Regenerate with `/portfolio-reviewer cards`._
