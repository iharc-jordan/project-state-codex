# validate-research — the research capability's validator

Composed with the core validator by `project-state validate` (the bundled capability contract); fails only records in the
`research` namespace. The checks are executable — `validator/scripts/check.py` — because the spec's gates are computed,
never prose (capabilities/research/README.md, §7):

```bash
python3 <plugin>/capabilities/research/validator/scripts/check.py <facility>            # everything below
python3 <plugin>/capabilities/research/validator/scripts/check.py <facility> --lock RES-M-NNN   # the lock checklist
python3 <plugin>/capabilities/research/validator/scripts/check.py <facility> --gate RES-M-NNN   # the evidence gate
```

Exit 0 clean, 1 errors (warnings too under `--strict`). Report what it prints plainly; fix nothing silently.

1. **Enablement.** `capabilities.research` present; `version:` against the installed plugin — warn on drift.
2. **Schema.** Required fields and enums per `schema/entities.yaml`; the file name is the id; ids in the fixed formats.
3. **Counters.** `state/research.json` counters are not behind the highest id on disk — an error, since the next id would collide.
4. **References.** step → mandate; finding → mandate, step (of the same mandate) and the mandate's question ids;
   `answered_by` → findings that answer that question; `supersedes` / `contradicts` / `supports` resolve; challenge →
   finding and mandate; change → mandate and findings; candidate scores → criteria of the mandate and findings.
5. **The lock checklist,** for every mandate at `locked` or later: questions; ≥ 3 concrete methodology steps; a
   deliverable with format, structure and audience; success criteria; a corpus link (`source_relevance` with a score
   ≥ 2 on a document the curator registered) or `corpus_independent: true`; longlist weights summing to 1.0 with a
   rubric each; comparative subjects (≥ 2) and typed dimensions. `closed-negative` requires `null_result_statement`;
   `standing` names its cadence.
6. **Append-only.** Findings, challenges and changes unchanged since first committed except for their lifecycle fields
   (a finding's `status` and `became`; a challenge's `status`, `resolution`, `resolved_by`, `proposed_resolution`).
   Needs git; the state server enforces the same rule on every write.
7. **Scoped supersession.** Same mandate, a shared question in `answers`, the same category; the target older; no cycle.
8. **Independence.** `independent_sources` ≤ the evidence it counts; no finding supports itself or its own supersession
   chain; an established material finding has an independent origin (≥ 2 independent sources and no `derives_from`, or a
   corroborating finding from another origin) or a person's confirmation (`research.finding.established` by a person).
9. **Excerpts** on every evidence item of a material primary or secondary finding; speculative tier ⇔ speculative confidence.
10. **Rulings.** An accepted, rejected or resolved challenge names the person who ruled (`resolved_by`, never a skill);
    a rejection carries its reason; the log shows no skill ruling.
11. **The evidence gate** — warned for in-progress and standing mandates here; `research-brief` refuses on it (`--gate`).
12. **The walk marker** — an expired `walk.active` is reported (the digest's `research.walk-abandoned`).
