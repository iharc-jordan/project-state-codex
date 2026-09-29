# intel — ecosystem intelligence capability

**Hosting shape:** capability-only. There is no intel-state facility — decision
`2026-08-28-intel-capability-only` closed the both-shapes carve-out
(CAPABILITY-PLUGINS.md §3–4). A project that needs intelligence enables this capability;
the firm's **standing desk is an org-level Project** (subject: the firm or the market)
with the same capability enabled — the desk pattern is a hosting convention, not a
second schema home.

Spec: [`docs/INTEL-CAPABILITY-SPEC.md`](../../docs/INTEL-CAPABILITY-SPEC.md).
Lineage: ported from the standalone generic intel suite (intel-state / -scaffolder /
-harvester / -ingest / -orchestrator / -runner); the six-skill mapping is spec §2.1.
The spine dissolved into the memory layer, the orchestrator into `routine.yaml`, the
runner into the bundled pack's reporting-matrix defaults.

| Piece | What it is |
|---|---|
| `plugin.yaml` | identity, `intel` namespace, payload declaration |
| `schema/` | INT-E / INT-S / INT-M kinds, `intel/` directories, `intel.*` events |
| `templates/` | manifest block (`focus` REQUIRED), agenda, entity templates |
| `skills/` | `intel-onboarding` · `intel-harvester` · `intel-ingest`; 1.1 `intel-battlecard` · `intel-deal-coach` · `intel-brief` · `intel-ask`; 1.2 `intel-monitor` · `intel-winloss` |
| `scripts/` | 1.2: `monitor.py` · `winloss.py` · `eval_metrics.py` (read-only lenses) · `migrate_intel_state.py` (the one writer) · `intel_lib.py` |
| `routine.yaml` | the digest checks (was the intel-orchestrator briefing) |
| `validator/` | composed with the core validator; polices only `intel/` records |
| `packs/intel-default/` | matrix defaults that absorb intel-runner's cadences |

Signals are append-only and carry lineage edges — promoting a signal into a risk, a
decision, or a document citation is a `became:` edge, not a copy. The inbox is the house
inbox (`documents/inbox/`); `intel/inbox/` does not exist.

## At a glance (declared report)

`views/build-intel-glance.py <facility>/project-state` renders `intel/reports/at-a-glance.html` — the
entity map (dot size = signal count, colour = status, faded past the staleness threshold), the 30-day
signal stream by intelligence value, agenda coverage per tier, and mandates by stage. It is declared in
`surfaces.yaml → reports:` so the app's Intel page renders it in place; `intel-harvester`,
`intel-ingest` and `intel-onboarding` re-run it after they write. `samples/at-a-glance.html` is the
same page rendered from `examples/fixture/` (invented data) — the template the app previews before the
capability is enabled. Regenerate both with `python3 scripts/build-capability-samples.py --only intel`.

## The competitive layer (1.1) — `docs/INTEL-CI-SPEC.md`

Intel 1.1 implements the Open Competitive Intelligence spec (OCI v0.1) at L1 Grounded inside the
same namespace. The **claim** (`intel/claims/INT-C-NNN.yaml`) is the atom: one sourced, dated,
scoped assertion with an epistemic status (verified · reported · inferred · hypothesis · unknown),
a source class and a rubric confidence; append-only, superseded never edited, conflicts recorded on
both sides, freshness derived from the per-category half-life table in the manifest block. The
harvester's `competitor` verb writes claims before prose and lifts sourced signals into claims.
Four skills project them: `intel-battlecard` (the three-part test, a required avoid-saying list,
zero unsourced lines), `intel-deal-coach` (one deal's context — a tender, the deals directory, the
inbox — into ranked moves), `intel-brief` (the period's material changes, allowed to say nothing
changed), `intel-ask` (answers from retrieved claims, staleness inline, unknown is an answer).
Every material line of every projection carries `[INT-C-…]`; a hand-edited projection is a fork.
The **Competitive** page (`views/build-intel-competitive.py`) is the second declared report:
coverage per competitor by freshness, the contested grid, open unknowns, battlecard currency,
30 days of change events. `samples/competitive.html` is its fixture render.

## Watch, learn, measure (1.2) — `docs/INTEL-CI-SPEC.md` §14

- **`intel-monitor`** re-reads the watch list (`intel/watch.yaml`) on a weekly cadence through its
  connectors — `web.read`, `deals.read`, `documents.search` — and writes what changed as claim deltas:
  superseding claims and change events classed material / notable / noise, each owned. `scripts/monitor.py`
  says what is due and what changed; the skill reads and judges.
- **`intel-winloss`** records every closed deal (`intel/winloss/INT-W-NNN.yaml`) with the seller's and the
  buyer's reasons in separate fields, writes the claims each deal teaches, and analyses them with the
  sample behind every pattern, segmented before generalised (`scripts/winloss.py`). The tender
  capability's won / lost offers it.
- **The evaluation harness.** `examples/fixture/golden.yaml` is the OCI §13 golden set, generated with the
  fixture; `scripts/eval_metrics.py` computes the six headline metrics over any project's projections;
  `examples/fixture/eval-results.md` publishes the fixture baseline, and the `intel-*` cases under
  `evals/` ask the skills the golden questions. `scripts/test-intel.py` (repo root) holds it all together.
- **Migration.** `scripts/migrate_intel_state.py <intel-state> <project-state>` moves a standalone
  intel-state facility in, non-destructively (`intel-onboarding migrate`).
- The Competitive page gains *Is the watch list being read?* and *What are closed deals teaching us?*

