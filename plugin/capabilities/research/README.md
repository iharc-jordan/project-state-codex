# research — question-driven, evidence-graded research

**Hosting shape:** capability-only (decision `2026-09-27-research-capability-only`). A standing research desk is an
org-level Project with this capability enabled; there is no research-state facility. Spec:
[`docs/RESEARCH-CAPABILITY-SPEC.md`](../../docs/RESEARCH-CAPABILITY-SPEC.md).

**The line with intel:** facts about named players are intel; an argument that answers a question is research. The two
share field names where the concept is the same and cross only by an inbox proposal (`research-mandate promote`).

**Two shapes of work, one schema.** A *bounded* mandate answers its questions and completes with a deliverable that
keeps its evidence. A *standing* mandate never completes: each night's walk re-checks stale evidence, and each week's
delta says what changed — or, in one line, that nothing material did.

| Piece | What it is |
|---|---|
| `schema/` | RES-M mandates · RES-S steps · RES-F findings (append-only) · RES-C challenges · RES-L candidates · RES-X changes; `research.*` events |
| `skills/` | onboarding · mandate · ingest · step · deepweb · longlist · redteam · brief · walk · retro · ask |
| `agents/` | the four fan-out subagents — fetcher, ingestor, comparer, scorer: read-only, one unit each, JSON back |
| `validator/` | `validate-research.md` composing `scripts/check.py` — the whole §7 check, `--lock`, `--gate` |
| `scripts/` | redteam · walk · merge · render · learn · promote (read-only) · migrate_research_state (the one writer) |
| `views/` | `_research.py` (the one model) · At a glance · Library (studies and articles) · Evidence · Timeline · What changed |
| `routine.yaml` | eleven digest checks; the walk's parked decisions reach a person through `research.walk-gated` |
| `packs/research-default/` | the nightly walk, the weekly red-team sweep, the weekly delta, the glance after each walk |
| `examples/fixture/` | a four-mandate desk (bounded, standing, closed negative, drifting draft) the samples and tests use |

**Hard rules**, all enforced by a script or the state server: the mandate is locked before any step runs; findings are
never edited (only `status` and `became` advance); every finding states tier, confidence, epistemic status and
independence; a material finding is provisional until an independent origin agrees or a person confirms it; a
blocking challenge stops the deliverable; the walk performs no human decision.

Test: `python3 scripts/test-research.py` (repo root). Samples: `python3 scripts/build-capability-samples.py --only research`.
Migrate a standalone `.research-state` facility: `python3 capabilities/research/scripts/migrate_research_state.py <old> <project-state>`.
