# Research or Study (work type)

Work type for a research project, study, evaluation or investigation that is not driven by a
funder's rules (pair it with a funder pack when it is). Stage-gate ladder read as questions →
method → data collection → analysis → findings, with ethics and data-quality risks seeded.

- **Ladder:** `stage-gate-default`. Onboarding asks: *When are the findings due?*
- **Seeds:** 6 dated milestone drafts, 4 risks, 3 KPI suggestions for the `project-goal-tracker` workflow.
- **Matrix:** weekly-team-update; monthly-research-update.

```yaml
project:
  kind: work-research
  packs_loaded: [work-research, sponsor-internal]
phases:
  preset: stage-gate-default
```
