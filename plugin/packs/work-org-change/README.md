# Organisational Change (work type)

Work type for change that lands on people: a reorganisation, a new process or system rollout,
a policy change, a hiring or onboarding wave. Stage-gate ladder read as case for change → plan and
communications → pilot → rollout → adoption review, with adoption rather than delivery as the measure.

- **Ladder:** `stage-gate-default`. Onboarding asks: *When should the change be fully in place?*
- **Seeds:** 5 dated milestone drafts, 4 risks, 4 KPI suggestions for the `project-goal-tracker` workflow.
- **Matrix:** weekly-team-update; monthly-change-pulse.

```yaml
project:
  kind: work-org-change
  packs_loaded: [work-org-change, sponsor-internal]
phases:
  preset: stage-gate-default
```
