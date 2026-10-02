# General Project (work type)

For work with a goal, a team and a finish line that no more specific type describes. Choosing it
is not a fallback: it gives the project the `stage-gate-default` ladder (define → plan → deliver →
review → close), five dated milestone drafts, three starter risks, two KPI suggestions for the
`project-goal-tracker`, and a weekly team update.

Pair it with an accountability pack — usually `sponsor-internal`, or `client-services` when
the work is for a customer.

```yaml
project:
  kind: work-general
  packs_loaded: [work-general, sponsor-internal]
phases:
  preset: stage-gate-default
```
