---
kind: portfolio-answer
question: "{{question}}"
asked_by: "{{asked_by}}"
asked_at: "{{now}}"
read: {{files_read}}              # index files read first
drilled: {{files_drilled}}        # member files opened second
basis: "{{basis}}"                # declared | inferred-from-owners | inferred-from-activity
kept: true
---

# {{question}}

**Short answer.** {{short_answer}}

{{body}}                          <!-- evidence by member and path; a figure when the question implies one -->

**What this answer does not know.** {{does_not_know}}

---
_Answered from the index compiled {{index.compiled_at}} and {{drilled_count}} member file(s). Re-ask to refresh._
