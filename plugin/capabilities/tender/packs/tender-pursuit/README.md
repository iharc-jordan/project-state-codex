# tender-pursuit pack

Profiles for facilities running the tender package.

Provides: `notifier` (score bands + ten immediate-alert rules, spec §17),
`review-meeting` (weekly 30-minute Tender Pipeline Review), and
reporting-matrix lines (daily digest, weekly pipeline report, monthly buyer
activity, quarterly win/loss).

A facility that enables the tender package without adopting this pack still
functions — the pack supplies sensible defaults. It composes with any other
pack (grant-canada, client-services, agile-default…): tender profiles add to,
and never replace, the facility's existing reporting matrix.

Activate in `manifest.yaml`:

```yaml
packages:
  tender:
    enabled: true
    pack: tender-pursuit
```
