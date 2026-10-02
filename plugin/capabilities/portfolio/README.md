# portfolio — cross-project oversight capability (lean V1: understand · query · synthesize)

**Hosting shape:** capability on an **org-level Project**. The portfolio is a Project whose
subject is a set of other projects — its own manifest, people, decisions, matrix, log and
kanban like any Project; this capability adds members, dated snapshots, a compiled
cross-member index, dependencies and findings. Same hosting convention as intel's standing
desk (decision `2026-08-28-intel-capability-only`, item 4), and the shape set up live at the
2026-09-11 P-S kickoff.

Rescoped
2026-09-22 from a reporting machine to a knowledge machine; the reporting material is parked
under `parked/`, not deleted.

| Piece | What it is |
|---|---|
| `plugin.yaml` | identity, `portfolio` namespace, payload declaration |
| `schema/` | `portfolio-member` / `-snapshot` / `-dependency` / `-finding` kinds, `portfolio/` directories, `portfolio.*` events |
| `templates/` | manifest block (`workspace_root` + `subject` REQUIRED), snapshot shape, understanding page, kept answer, inbox proposal, entity templates |
| `skills/` | `portfolio-onboarding` (enable, seed, admit one) · `portfolio-collector` (snapshot, index, understand, weekly note, the at-a-glance report — scripts `collect.py` + `render_glance.py`) · `portfolio-reviewer` (query, synthesize, promote) |
| `routine.yaml` | the digest strip and three checks: unreachable, silent, harvest stale |
| `surfaces.yaml` | kanban: Members and Findings boards, setup stages, and the declared **At a glance** report the app renders in place |
| `views/` | the two mounted figures — Home (lanes over 90 days) and Project (one member at a glance) |
| `validator/` | composed with the core validator; polices only `portfolio/` records |
| `packs/portfolio-default/` | one matrix default: the weekly collect |
| `examples/lean/` · `examples/html/` | the V1 fixture and its rendered page, "five questions, five pictures" |
| `parked/` | measure sets, card templates, V2 views — designed, not shipped |

**The one rule that matters:** the portfolio is read-only toward its members. The collector
reads each member's own `project-state/` and writes here; the reviewer answers from the index
and the member files, never from memory. The only file placed in a member is a proposal into
its `documents/inbox/`, which the member's own `project-inbox` triages.

`samples/at-a-glance.html` is the same report rendered from `examples/fixture/` (invented data) — the
template the app previews on the Capabilities page before the capability is enabled or has run.
Regenerate with `python3 scripts/build-capability-samples.py --only portfolio`.
