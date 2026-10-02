# Partnership or Collaboration (work type)

Work type for establishing a partnership, alliance or cross-organisation collaboration: agree
shared goals, sign the agreement, build a joint plan, deliver something together, then review.
Stage-gate ladder, with the partner relationship itself treated as the thing being built.

- **Ladder:** `stage-gate-default`.
- **Seeds:** 6 dated milestone drafts, 4 risks, 3 KPI suggestions for the `project-goal-tracker` workflow.
- **Matrix:** monthly-partner-update; quarterly-partner-review.

```yaml
project:
  kind: work-partnership
  packs_loaded: [work-partnership, sponsor-internal]
phases:
  preset: stage-gate-default
```
