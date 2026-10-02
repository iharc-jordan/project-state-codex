# Sales Pursuit (work type)

Work type for pursuing one significant private deal or account: a strategic sale, an enterprise
contract, a renewal worth planning. Stage-gate ladder read as qualify → propose → negotiate →
decision → handover, planned back from the expected decision date. Public tenders and RFP
pipelines belong to the tender capability instead — this is one deal, run as a project.

- **Ladder:** `stage-gate-default`. Onboarding asks: *When do you expect the buyer's decision?*
- **Seeds:** 6 dated milestone drafts, 4 risks, 4 KPI suggestions for the `project-goal-tracker` workflow.
- **Matrix:** weekly-deal-review; pursuit-win-loss-review.

```yaml
project:
  kind: work-sales-pursuit
  packs_loaded: [work-sales-pursuit, sponsor-internal]
phases:
  preset: stage-gate-default
```
