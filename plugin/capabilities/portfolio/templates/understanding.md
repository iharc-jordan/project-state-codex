---
kind: portfolio-understanding
member: "{{member.id}}"
as_of: "{{snapshot.date}}"
source_rev: "{{snapshot.source_rev}}"
regenerated_by: portfolio-collector
regenerable: true
---

# {{member.name}} — what we understand

*As of {{snapshot.date}} (rev {{snapshot.source_rev}}). Every line cites the member file it came from. Regenerated on each collect; do not edit.*

**What it is.** {{what_it_is}} `{{cite.identity}}`

**Where it is.** {{where_it_is}} `{{cite.progress}}`

**Who.** {{who}} `{{cite.people}}`

**What is open.**
{{#each open}}
- {{line}} `{{cite}}`
{{/each}}

**What changed since the last collect ({{previous.date}}).** {{what_changed}} `logs/activity.ndjson {{previous.ts}} → {{snapshot.ts}}`

**What it depends on and what depends on it.** {{dependencies}} `{{cite.dependencies}}`

**Harvest.** {{harvest_line}} `harvest/cursors/`

**Words this project uses that others also use.** {{shared_tags}} `portfolio/index/tags.yaml`

---
_Cited paths are relative to the member's `project-state/`. To ask something this page does not answer: `/portfolio-reviewer query "…" --member {{member.id}}`._
