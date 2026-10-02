---
kind: portfolio-card
variant: external                     # portco-first, fewer lines; a DRAFT under the review rule
member: "{{member.id}}"
as_of: "{{snapshot.date}}"
audience: "{{audience}}"              # funder / board / partner reader
review: PL                            # never sent by the system
recipe: portfolio-card-external       # project-onepager recipe shipped by the capability
generated_at: "{{now}}"
---

# {{member.name}} — status card

*As of {{snapshot.date_long}} · prepared for external review · draft*

| Stage | Thesis fit | Committed | Delivery | Health |
|:--:|:--:|:--:|:--:|:--:|
| {{investment.stage}} | {{investment.thesis_fit}} / 5 | {{investment.committed}} | {{milestones.complete}} of {{milestones.total}}, {{schedule_word}} | {{sets.health.status}} |

**Where it is.** {{paragraph.where}}

**What is working.** {{paragraph.working}}

**What needs attention.** {{paragraph.attention}}

**What we are doing about it.** Portfolio stance is *{{stance.value}}*: {{stance.plain_language}}

**What this card does not show.** {{paragraph.not_measurable}}

---
_Generated from project state; every statement above corresponds to a recorded milestone, risk, decision or declared portfolio field. Draft — not sent._
