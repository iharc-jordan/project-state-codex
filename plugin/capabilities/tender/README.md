# tender — public-sector tender capability

**Hosting shape:** capability — a tender is watched *by* a project, decided and pursued
inside it (the bundled capability contract names tender as the case that fails the state bar).
The pursuit desk rides the enabling project's substrate: same activity log, decisions,
documents registry, notifier, kanban, weekly review. A won tender hands off via
`project-scaffolder` to become a delivery project; the pursuit record stays.

Formalized to the sred shape 2026-08-28 — before that, `capabilities/tender/`
held only `surfaces.yaml` while the four skills sat at repo-root `skills/` and the pack at
repo-root `packs/`, reaching the published plugin via the wholesale mirror with **no
declared payload** (the exact undeclared-drift path the payload mechanism exists to close;
the build script printed a warning about it on every run).

| Piece | What it is |
|---|---|
| `plugin.yaml` | identity, `tender` namespace, declared payload |
| `surfaces.yaml` | the operative contract: entities, boards, workspaces, guided setup, connectors — the reference implementation of capability-conditional app views |
| `schema/` | tender + tender-profile kinds, `tender.*` events (extracted from the skills) |
| `templates/manifest-block.yaml` | the enable block — `mailbox_label` REQUIRED; derived from `surfaces.yaml → enablement.defaults`, which wins on disagreement |
| `skills/` | `tender-harvester` · `tender-qualifier` · `tender-monitor` · `tender-pipeline` |
| `routine.yaml` | digest checks, lifted from surfaces.yaml's operations prose |
| `validator/` | composed with the core validator; polices only `tender` records |
| `packs/tender-pursuit/` | bundled pack: notifier thresholds, weekly pipeline review, matrix lines |

**Known gap:** no prose spec document. `surfaces.yaml` plus the four skills are the
operative contract (`plugin.yaml → spec:` points there); `schema/` here is extracted from
them, not the other way round. If the contract and this extraction disagree, the skills
and surfaces.yaml win — re-derive.

State convention is already modern: per-capability runtime in
`state/tender.json` (the bundled capability contract), typed events in
`tenders/events.ndjson`, append-only with `superseded_ts` corrections.

## At a glance (declared report)

`views/build-tender-glance.py <facility> [--as-of]` renders the tender desk from state — pipeline lanes by stage on a closing-date axis, the bid/no-bid queue, connector health, the last 14 days of typed events — into `tenders/reports/at-a-glance.html`. `surfaces.yaml` declares it (`reports:`), so the app's Tender page renders it in place as its default tab. Self-contained, script-free. Fixture: `examples/fixture/make_fixture.py` builds a project-state with the capability enabled, two profiles, ten tenders and four connectors; run the builder on it to regenerate the golden output.

`samples/at-a-glance.html` is the same report rendered from `examples/fixture/` (invented data) — the
template the app previews on the Capabilities page before the capability is enabled or has run.
Regenerate with `python3 scripts/build-capability-samples.py --only tender`.
