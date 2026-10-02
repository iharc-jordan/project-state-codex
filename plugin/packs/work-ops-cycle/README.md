# Operating Cycle (work type)

For recurring operational work: month-end or quarter-end close, budget cycles, compliance
calendars, recurring reporting processes. The work never finishes; each period does.

- **Ladder:** `cycle-default` (prepare → execute → review → close → prepare…), with the continuous
  lifecycle suggested so each period is its own increment and a closed period is never reopened.
- **Asks:** the cycle length (`monthly` | `quarterly`), written to `project.ops.period`.
- **Seeds:** three set-up milestones, four risks, four KPI suggestions.
- **Matrix:** a period checklist five days before month end; a period close report to the sponsor.
  For a quarterly cycle, switch both entries to `kind: quarterly` after seeding.

```yaml
project:
  kind: work-ops-cycle
  ops: { period: monthly }
  packs_loaded: [work-ops-cycle, sponsor-internal]
phases:
  preset: cycle-default
  lifecycle: continuous
```
