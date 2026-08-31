# PIC PCAIS Pack

Reproduces v1.x suite behavior for projects funded by Protein Industries Canada under the PCAIS (Protein Consortia AI Stream) program.

## What you get

Six profile YAMLs that configure the generic v2.0 skills to behave per PIC requirements:

- `profiles/funder-reporting.yaml` — quarterly claim form (PIC MS & financial tracking xlsx), Apr/Jul/Oct/Jan 20 deadlines, percent-complete + technical-progress per-milestone fields, PIC PM cover-email template, 14-day pre-deadline draft trigger.
- `profiles/review-meeting.yaml` — Steering Committee lifecycle per PIC PM Guide Appendix A, 5-business-day notice + 5-business-day minutes distribution, four required designate roles per consortium member (Project Lead / Finance Rep / Communications Rep / Signing Authority), PIC PM as non-voting attendee, quarterly minimum cadence.
- `profiles/external-comms.yaml` — MPA-mandated 30-day full publication review, 14-day abstract review, PIC + ISED + Government of Canada funding acknowledgement, patent-filing-delay coordination, SC-as-reviewer.
- `profiles/ip-tracker.yaml` — disclosure recipient = PIC Director of Data and IP, IP Registry abstract format, Annual Questionnaire IP section template, foreground/background per PIC definitions, commercialization reporting cadence.
- `profiles/archive.yaml` — PIC final report per consortium member (~90-day pre-close template distribution, drafts by close date, finalized 30 days post-close), IP final reporting, FTE confirmation, holdback release tracking.
- `profiles/phase-gate.yaml` — augments `grant-default` preset with PIC-specific gate criteria (e.g. "MPA signed by all parties" as planning gate-out).

Plus templates (claim cover email, SC Appendix-A agenda, final report, IP disclosure, publication review form) and a `reporting-matrix-defaults.yaml` that seeds matrix entries for the funder.pic stakeholder group.

## Loading

In your project's `manifest.yaml`:

```yaml
project:
  packs_loaded: [pic-pcais]
```

Then run:

```
ask Codex to seed the reporting matrix from the active packs
```

## Compatibility

- Compatible with v2.0+ core
- Compatible alongside any non-PIC pack (e.g. add `client-services` to also handle customer invoicing, or `board-investor` to also handle board reporting; PIC funder reporting continues unchanged)

## License & support

Released for use by PIC-funded consortiums. Contact david@atomic47.co with questions, issues, or PIC PM Guide updates that need to flow into this pack.
