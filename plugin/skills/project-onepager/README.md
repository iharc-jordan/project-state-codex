# project-onepager

**Audience-framed documents generated from project state — one-pagers to whitepapers.
Regenerable, with every claim carrying provenance back to a typed record.**

Part of the [project-state](../../README.md) skill suite. A document here is not a
file someone wrote — it's a **recipe** (audience × altitude × purpose × evidence
filters) rendered against the current substrate. When state moves, re-run the
recipe: fresh document, plus a change note of what moved.

## Why this exists

Status decks and whitepapers rot the moment they're exported, and nobody can tell
which claims are still true. This skill applies the suite's core principle to
prose — *state is the source of truth; when an artifact disagrees with state,
regenerate the artifact* — and adds the property that makes documents survive
diligence: **receipts**. Every substantive claim cites the record it came from
(`M10`, `R-01`, `decision 2026-05-29`, `KPI-01`) as a small provenance chip or
footnote.

## What's in this directory

| Path | What |
|---|---|
| `SKILL.md` | The skill definition — workflow, recipe schema, altitude ladder, audience rules |
| `templates/onepager-template.html` | Terracotta document theme, print CSS (PDF via headless Chrome) |
| `templates/onepager-recipe.yaml` | Recipe schema, ready to copy |
| `examples/exec-onepager.yaml` | A real recipe |
| `examples/2026-07-15-exec-onepager.html` | The document it generated, from live state |

## Install

Standalone (any Claude Code setup):

```bash
cp -R project-onepager ~/.claude/skills/
```

As part of the project-state plugin, it ships in `plugin/skills/` automatically.
It expects a `project-state/` substrate (found by walking up from cwd) and reads
it through the `project-state` memory-layer skill.

## Quickstart

```
/project-onepager audience: exec altitude: onepager
/project-onepager audience: funder altitude: brief purpose: "reassure on schedule, surface the M10 decision"
/project-onepager regenerate exec-onepager
```

Or drop a recipe into `reports/custom-defs/<slug>.yaml` (schema in
`templates/onepager-recipe.yaml`) and ask for it by slug. Recurring documents are
one line in `reporting-matrix.yaml` with `generator: project-onepager`.

Outputs land as `reports/onepagers/<date>-<slug>.html` (+ `.pdf`), with a review
card in `outbox/queue/` — **nothing is sent or published without human approval**
(delivery routes through `project-notifier` / `project-blog-publisher` /
`project-website-publisher`).

## The two axes

**Altitude** — same evidence tree, different pruning:

| altitude | shape |
|---|---|
| `onepager` | headline claim → 3 proof points with receipts → one honest risk → the ask (1 page) |
| `brief` | + milestone table, decision highlights, KPI movement (2–3 pages) |
| `deepdive` | + approach/architecture from the wiki & docs corpus, full risk posture, roadmap (5–8 pages) |
| `whitepaper` | thesis-driven; outline → per-section drafts → assembly → consistency pass; runs as a queued job |

**Audience** — voice profiles from the active pack's `profiles/onepager.yaml`
(see `packs/pic-pcais` for funder/steering-committee, `packs/board-investor` for
exec/investor), falling back to built-in defaults (funder, exec, technical,
public). Profiles set tone, what to lead with, what **must never appear**
(a safety contract, including paraphrase), provenance style, format, and signoff.

## Design invariants

1. **Receipts** — no substantive claim without a record reference.
2. **Regeneration** — recipes record `last_generated` (timestamp + activity-log
   sequence); re-runs diff against it and prepend a change note.
3. **The honest risk is mandatory** at every altitude except `public`. Documents
   without acknowledged risk read as marketing and die in diligence.
4. **Review-not-author** — drafts stop in the outbox, always.
