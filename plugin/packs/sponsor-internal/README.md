# Internal Sponsor Pack

For projects commissioned by someone inside your own organisation — a manager, an executive, a
steering group. It is the default answer to *"who needs to hear how it's going?"* in onboarding
(decision D3, `skills/project-scaffolder/SKILL.md`).

## What you get

- `profiles/funder-reporting.yaml` — the **weekly sponsor update**: RAG status with its reason,
  progress, what's coming, decisions needed (who, by when), top three risks.
- `profiles/review-meeting.yaml` — the **monthly steering review**: agenda, pre-read, actions.
- `reporting-matrix-defaults.yaml` — both of the above on their cadences.

The sponsor plays the funder role, the same way `client-services` treats a customer. Add a
`stakeholders.sponsor` entry to the manifest so the update has somewhere to go.

## Loading

```yaml
project:
  kind: work-campaign
  packs_loaded: [work-campaign, sponsor-internal]
```

Composes with every work pack, and alongside `client-services`, `board-investor` or a funder pack.

## Maturity

Starter — the shape is common practice; tune the sections to your sponsor.
