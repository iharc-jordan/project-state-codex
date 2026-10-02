# Event (work type)

For conferences, summits, offsites, galas and trade-show presences — work planned back from a
fixed event date.

- **Ladder:** `countdown-default`, anchored on `phases.anchor_date` = event day (asked at onboarding).
- **Seeds:** seven dated milestone drafts (venue at T−120 through wrap at T+30), five risks, five
  KPI suggestions.
- **Matrix:** a weekly countdown digest in plan and build-out that hands over to a daily digest in
  the final countdown; a run-of-show readiness brief at T−7; a post-event report at T+10.

```yaml
project:
  kind: work-event
  packs_loaded: [work-event, sponsor-internal]
phases:
  preset: countdown-default
  anchor_date: 2027-03-12
```
