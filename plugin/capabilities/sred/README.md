# `sred` — SR&ED capability plugin

**Hosting shape:** capability (extension *into* a project-state facility, enabled per project).
SR&ED has no standalone existence — it rides a delivery project's milestones, people, and
harvest — so it does not meet the state bar (the bundled capability model). There is no
desk-pattern variant: SR&ED intelligence belongs to the project doing the experimental work.

The bundled `plugin.yaml`, `schema/`, `validator/`, and skills define this capability.

## What enabling this capability adds to a project

| Payload | What it adds |
|---|---|
| `schema/` | `sred/` entity dirs (TU/EX/ADV, cost-tracking), append-only `sred/evidence-log.ndjson`, `sred/inbox/` for harvester proposals, `state/sred.json` per-fiscal-year claim state, and the `sred.*` event vocabulary |
| `skills/` | `project-sred-tracker` (continuous capture, gap analysis, quarterly review, cost roll-up) and `project-sred-reviewer` (T661 audit-risk review, CRA attack simulation, review gate for the advisor handoff) |
| `templates/` | T661 narrative (Sections E/F/G), evidence map, cost categorization, project summary, entity skeletons, and the manifest block `enable` writes |
| `validator/` | traceability + contemporaneity checks, composed with `project-state validate` |
| `views/` | declarative traceability board + per-FY deadline strip (V1.1) |
| `packs/sred-canada/` | bundled default behavior pack: CRA language guidance, claim-chain matrix defaults, phase-gate injections, external-comms coordination, archive-tail rules |

## Hard rules

1. **Draft-only** — the terminal artifact of every chain is a draft; a human sends, a human files.
2. **No eligibility assertions** — structure and language guidance only; eligibility is the advisor's call.
3. **Never invent** — no fabricated experiments, results, or evidence.
4. **Contemporaneity** — evidence carries the work date and the logged-at date; back-fill is marked.
5. **The 18-month deadline is hard** — deadline state is computed at enable, escalated by the tick, and survives project archive (the archive tail).
6. **CRA is not a project stakeholder.**

## Enable

Requires `fiscal_year_end`. Writes the `capabilities: sred:` manifest block
(`templates/manifest-block.yaml`), scaffolds `sred/`, initializes `state/sred.json` with the
current fiscal year's target (FY end + 15 months) and hard deadline (FY end + 18 months),
seeds the reporting matrix from the bundled pack, and arms `automation/tasks.yaml`.

Disable keeps all data and refuses silently walking away from a live filing window: any
fiscal year not in `{filed, waived, forfeited}` requires explicit confirmation.

## Dashboard (declared report)

`node views/build-sred-dashboard.mjs <facility>/project-state` renders `reports/adhoc/sred-dashboard.html`,
declared in `surfaces.yaml → reports:` (scripted; the app renders it in a trusted frame). `project-sred-tracker`
re-runs it after every write. `samples/dashboard.html` is the same dashboard rendered from
`examples/fixture/` (a fictional stream-join project; every fact invented) — the template the app previews
before the capability is enabled. Regenerate with `python3 scripts/build-capability-samples.py --only sred`.
