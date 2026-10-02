# Content or Publication (work type)

Work type for making and publishing content: a report, a book, a course, a video series, a
website or documentation set. Countdown ladder anchored on the publish date: outline, draft, review,
production, publish, then promotion and a results check.

- **Ladder:** `countdown-default`. Onboarding asks: *What's the publish date?*
- **Seeds:** 7 dated milestone drafts, 4 risks, 3 KPI suggestions for the `project-goal-tracker` workflow.
- **Matrix:** weekly-content-status; publish-readiness-check.

```yaml
project:
  kind: work-content
  packs_loaded: [work-content, sponsor-internal]
phases:
  preset: countdown-default
```
