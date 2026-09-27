---
name: intel-harvester
description: "Research competitors and the market on the web — 'research X', 'harvest intel', 'refresh stale claims', 'what's new with our competitors'. Writes append-only signals and entity updates for the intel capability."
map:
  tier: capability
  stage: ingest
  inputs: [web]
  reads: [manifest, intel]
  writes: [intel, log]
  produces: [intel-brief, intel-competitive]
---

# intel-harvester — the research engine

> **When to use — full trigger description.** The frontmatter carries a short, trigger-first
> description so all of the suite's skills fit Claude Code's skill-listing budget (see
> docs/SKILL-SPEC.md, *Description budget*). The complete version, kept here:
>
> The intel capability's research engine. Takes an entity, a question, an agenda tier or the whole facility and investigates via web search, writing append-only INT-S signals and entity updates through project-state. Relevance is judged against capabilities.intel.focus — no focus, no harvest. Verbs: 'entity INT-E-NNN', 'question "..."', 'agenda p0..p3', 'longlist [--tier --max --entities-only --agenda-only --dry-run]' (breadth-first, unattended), 'sweep' (news check), and 'competitor INT-E-NNN|self|all [--depth --refresh --stale-only]' — OCI competitor-research: INT-C claims before prose (epistemic status, source class, rubric confidence), sourced signals lifted into claims, supersedes: chains and change events on reconciliation, the cited profile with its coverage block. Trigger on 'research entity', 'run the longlist', 'sweep the landscape', 'answer the P0 questions', 'what's new on <entity>', 'research competitor X', or matrix entries from the intel-default pack. Requires the intel capability enabled.

Research the ecosystem the project declared in `capabilities.intel.focus`, and write what
is learned as signals. Scheduling lives in the reporting matrix (the intel-default pack
seeds the cadences the old intel-runner carried); this skill only ever does the work.

## Context, every invocation

Via `project-state`: `capabilities.intel` (refuse if disabled; `focus` is the relevance
lens), entity list, `intel/agenda.yaml`, `state/intel.json` cursors and counters. A
finding is relevant if it affects the focus's strategy, market position, integration
options, or competitive landscape.

## Verbs

### `entity <id>`
Read the entity, answer its open `research_questions` via targeted web search + fetch,
write one signal per finding, update `key_facts`, mark answered questions on the entity so
future sweeps skip them.

### `question "<text>"`
Research one question; link resulting signals to the entities they reference; if it
matches an agenda item, log `intel.agenda.answered` citing the signal.

### `agenda <p0|p1|p2|p3>`
Work the tier from `intel/agenda.yaml`: skip answered questions, research the rest, report
answered / still-open / new entity candidates.

### `longlist` — breadth-first, built for unattended runs
Queue, in priority order: unanswered P0 agenda → `active_research` entities with open
questions → unanswered P1 → entities past `staleness_threshold_days` →
`active_engagement` entities (news check) → P2–P3 → `watch` entities silent >30 days.
Process 2–4 searches per item; write signals and entity updates; log progress to
`intel/reports/longlist-YYYY-MM-DD.md`; finish with the report (summary counts, findings
by tier, new entity candidates, remaining gaps) and log `intel.longlist.completed`.
Candidates are **listed for morning review, never auto-created**; unattended runs do not
ask for confirmation, they defer.
Options: `--tier <p0..p3>` · `--max <N>` · `--entities-only` · `--agenda-only` ·
`--dry-run` (print the queue, write nothing).

### `sweep`
Lightweight: check listed URLs and recent news for every `active_research` entity, flag
what is new. Catch-up, not deep research. Stamp `last_sweep`.

### `competitor <id>` — OCI `competitor-research` (docs/INTEL-CI-SPEC.md §5.1)
`competitor <INT-E-NNN> [--depth quick|full] [--refresh] [--stale-only]` ·
`competitor self` (claims about our own product — the battlecard cannot pass its three-part
test without them) · `competitor all --stale-only` (the weekly matrix entry: every in-scope
competitor, only the material claims past their half-life).

The record here is the **claim** (`templates/entities/C.yaml`), not only the signal: one
assertion about one entity, `epistemic_status` (verified · reported · inferred · hypothesis ·
unknown), `source.class` (§3.8 of the spec), rubric `confidence`, `material:` flag,
`retrieved_at`, `source_date`. Freshness is never written; it is derived from
`competitive.half_lives_days[category]` when rendered.

1. **Read** the entity, its claims (with freshness derived now), its signals.
2. **Lift** sourced signals about the subject that are not yet claims: one claim per
   assertion, `method: lifted-signal`, `derived_from: INT-S-NNN`, source class from the
   signal's source (`web_harvest` → `vendor-primary` or `press` by the URL's owner;
   `document_inbox` → the document's class; slack/email/meeting → `internal-observation`,
   `reported`). The signal is untouched.
3. **Research** the nine dimensions — company · positioning · product & capabilities ·
   pricing & packaging · customers · go-to-market · strengths · vulnerabilities · recent
   changes — through the source strategy below, within the collection rules. `--stale-only`
   restricts to categories whose material claims are stale; `--depth quick` stops after
   pricing, positioning and recent changes.
4. **Emit claims before prose.** Every finding is a claim first (`intel.claim.logged`);
   `unknown` is a claim too (`source.class: inference`, `ref` the search that failed) —
   never estimate unpublished pricing from weak signal. Confidence by the rubric: first-party
   for its category or two independent origins and fresh → high; one reliable source → medium;
   anecdotal, single weak, stale, inferred → low. Independent means different origin, not
   different URL.
5. **Reconcile.** New evidence that contradicts a stored claim → a new claim with
   `supersedes:` (the old claim is never edited), and when the old claim was material, an
   `intel-change` (`templates/entities/X.yaml`, `before`/`after`, significance, affected
   teams, an action) with `intel.change.detected`. Evidence that disagrees without settling
   → `conflicts_with` on **both** claims and `intel.conflict.recorded`. Never a silent
   overwrite, never a silent choice.
6. **Project.** Regenerate `intel/profiles/<id>.md` from `templates/profile.md` — every
   material line cites `[INT-C-…]`; vulnerabilities labelled verified limitation / buyer
   complaint / internal observation / inferred; the `coverage` block counts claims by
   freshness and names uncovered categories. Record the hash in `state/intel.json →
   projections`; log `intel.profile.generated`.
7. Still log the signal-level findings as before, and the key_facts on the entity.

Done when a reader can see the claim behind every material line and coverage shows what is
thin. Then re-render both declared reports (below).

## Research protocol

Read manifest block → read the entity → review its questions → search specifically →
fetch what matters → one signal per distinct finding via `project-state`
(`intel.signal.logged`) → update the entity → report found / unknown / next.

## Signal rules

One signal per finding · always reference entities · `intelligence_value` honest (high =
changes strategy) · `source_url` when available · tag with the prompting question ·
`logged_by: intel-harvester` · confirmed fact vs. inference distinguished in the summary ·
never fabricate — a search that returns nothing is reported as nothing.

## Source strategy (by entity type)

Vendors/companies: site, partner and developer pages, job postings, press, trade pubs,
conference decks. Government/regulatory: department pages, API registries, standards,
consultations. Competitors: pricing, reviews, LinkedIn hiring, funding databases, app
stores. Infrastructure/networks: technical docs, partner directories, standards bodies.
The manifest block's `entity_types` and the focus say which strategies apply.

## The declared reports

Every verb ends by re-rendering the desk's **At a glance** page, and the competitive verbs
also the **Competitive** page — both declared in `capabilities/intel/surfaces.yaml →
reports:` and shown in place on the app's Intel page:

```bash
python3 capabilities/intel/views/build-intel-glance.py <facility>/project-state
python3 capabilities/intel/views/build-intel-competitive.py <facility>/project-state
```

The Competitive page draws coverage per competitor (claims stacked fresh / aging / stale),
the contested grid, open unknowns, battlecard currency, and the last 30 days of change events.

Four pictures from state: the entity map (dot size = signal count, colour = status, faded past
`staleness_threshold_days`), the 30-day signal stream by intelligence value, agenda coverage
per tier, and mandates by stage. It reads `intel/`, `intel/agenda.yaml` and `state/intel.json`
and writes only `intel/reports/at-a-glance.html`. A lens, not a writer. Before the first signal
the app shows `samples/at-a-glance.html` (fixture data) banded "Template".

## Discipline

All reads and writes through `project-state` · date-stamp everything · answered questions
marked on the entity · reports are regenerable artifacts in `intel/reports/`, never state ·
claims and changes are append-only · freshness derived, never authored · a search that finds
nothing writes an `unknown` claim, not a guess.
