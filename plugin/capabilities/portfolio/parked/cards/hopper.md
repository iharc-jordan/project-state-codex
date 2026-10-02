---
kind: portfolio-card
variant: hopper
member: "{{member.id}}"
status: proposed
source: "{{member.source_row}}"       # master-log row, finding:<id>, or discovery
added: "{{member.added}}"
days_waiting: {{days_waiting}}
generated_at: "{{now}}"
---

# {{member.name}} — hopper card

**proposed · {{member.member_kind}} · {{member.priority}} · {{owner_or_no_owner}} · no substrate**
Origin: {{origin_line}}.

## What we know (from the row and its origin, not from a project)

{{#each known}}
- {{line}}
{{/each}}

## What admitting it would mean

- `project-intake` seeded from {{seed_source}}.
- {{shape_line}}
- Cost to admit, in one sentence: {{cost_sentence}}

## Stance

None yet. Options at the review: **admit** (run intake), **fold into {{fold_candidate}}** as a milestone and retire this row, or **retire with a note**.

---
_A hopper card carries only what the registry row and its originating finding hold. It gains measures the day it becomes a member._
