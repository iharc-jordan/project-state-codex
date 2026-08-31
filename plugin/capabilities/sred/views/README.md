# capabilities/sred/views

Declarative view specs for the SR&ED capability, plus the first mounted renderer.

| File | What it is |
|---|---|
| `sred-traceability.dash.yaml` | Declarative spec — TU → EX → ADV board, for the generic view engine |
| `sred-deadlines.dash.yaml` | Declarative spec — one strip per open fiscal year |
| `build-sred-dashboard.mjs` | **Renderer.** Both views above, plus gap findings, effort basis and handoff gates, as one self-contained HTML page |
| `dashboard.template.html` | The page shell the renderer fills — edit here to change the design |
| `lib-yaml.mjs` | Minimal YAML reader scoped to substrate shapes (no dependencies) |

## Running it

```sh
node capabilities/sred/views/build-sred-dashboard.mjs <facility-dir>
```

Writes `<facility>/reports/adhoc/sred-dashboard.html` by default. Options:

| Flag | Effect |
|---|---|
| `--out`, `-o <path>` | Write somewhere else |
| `--artifact` | Emit body-only HTML for embedding surfaces (no `<html>`/`<body>` wrapper) |
| `--as-of <YYYY-MM-DD>` | Compute countdowns from a date other than today |
| `--json <path>` | Also write the derived data, for other consumers |

No dependencies, no install step, no network. Node 18+.

## What it reads

`sred/uncertainties/`, `sred/experiments/`, `sred/advancements/`, `sred/evidence-log.ndjson`,
`sred/inbox/`, `sred/cost-tracking/`, `sred/criteria.yaml`, `state/sred.json`, `manifest.yaml`,
`milestones/`. Everything except `sred/` is optional — a facility missing a piece renders
without that section rather than failing.

**Read-only.** The renderer never writes into the substrate. It is a lens over
`project-sred-tracker`'s records, not a second writer, so it can be run any number of times
and needs no lock.

## What it computes

- **Chain state** per uncertainty: complete (every experiment reaches an advancement), partial, broken.
- **Findings** — the `gap_analysis()` checks from `project-sred-tracker`, grouped by check:
  uncertainty with no experiment, experiment with no uncertainty / evidence / results,
  advancement with no basis, uncertainty identified after the work began (downgraded to `low`
  when a `capture_note` discloses the back-fill), evidence going stale on an active experiment,
  completed experiment with no advancement, milestone anchors that have not started,
  and drift between `state/sred.json` counters and the files on disk.
- **Filing window** — the rail runs from the first day of the fiscal year to the statutory
  FY+18mo deadline, with the internal FY+15mo target marked. Tiers follow
  `sred-deadlines.dash.yaml`: red ≤90d, amber ≤180d, green beyond.
- **Handoff gates** — the things a human has to close before an advisor package is real. The
  claim-identity gate reads unresolved `ASSUMED` / `CONFIRM` / `TODO` annotations straight out
  of the manifest's `capabilities.sred` block, so a note-to-self stays visible until it is settled.

## What it does not do

It makes no eligibility determination and never will. Severity is about the *record* — whether
an assessor could follow it — not about whether the work qualifies. That call belongs to a
qualified SR&ED advisor.

## Regenerating the published artifact

The page is designed to be republished to the same Artifact URL after each run:

```sh
node capabilities/sred/views/build-sred-dashboard.mjs project-state --artifact -o /tmp/sred.html
# then publish /tmp/sred.html to the existing artifact URL
```
