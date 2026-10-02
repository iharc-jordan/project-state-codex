# Campaign or Launch (work type)

For marketing campaigns, product or feature launches and fundraising drives — work planned back
from a launch date and then measured in market.

- **Ladder:** `countdown-default` (plan → build-out → final countdown → live → wrap), anchored on
  `phases.anchor_date` = launch day. Onboarding asks for it.
- **Seeds:** seven dated milestone drafts (brief at T−60 through wrap), four risks, five KPI
  suggestions for the `project-goal-tracker` workflow.
- **Matrix:** weekly campaign status; a launch readiness check at T−7; a weekly performance report
  that fires only in `04-live`; a results report a week before the campaign comes out of market.

```yaml
project:
  kind: work-campaign
  end_date: 2027-05-31
  packs_loaded: [work-campaign, sponsor-internal]
phases:
  preset: countdown-default
  anchor_date: 2027-04-15
```
