---
name: intel-monitor
description: "Watch competitors for change — 'run the monitor', 'what changed with our competitors', 'check the watch list', 'set up competitor monitoring'. Re-reads watched sources; writes claims and change events."
map:
  tier: capability
  stage: ingest
  requires: [memory, python, connector:web]
  inputs: [web, files, operator]
  reads: [manifest, intel, tenders, documents]
  writes: [intel, log]
  produces: [intel-competitive]
---

# intel-monitor — the scheduled change monitor

> **When to use.**
>
> The intel capability's change monitor (OCI competitive-change-monitor, intel 1.2). Re-reads the sources on the project's watch list (intel/watch.yaml) on a cadence — competitors' pricing, home, security and docs pages through web.read, the project's own deal records through deals.read, the inbox through documents.search — compares what each says with the current claims it can settle, and writes what changed as append-only claims (supersedes:) and change events classed material / notable / noise, each with its owners and a recommended action. Noise never reaches the digest. Verbs: 'run [--source <id>]' (the weekly matrix entry, unattended), 'watch' (propose the watch list from the sources the claims already cite), 'status' (what is due, what is not watched). Trigger on 'run the monitor', 'check our competitors for changes', 'what changed on Northline's pricing page', 'watch this page', 'which sources are overdue', or the intel-weekly-monitor matrix entry. Requires the intel capability enabled with a focus.

Detect material change without generating noise. A change is a **claim delta** — a new claim that
supersedes an old one, or a new assertion a watched source now makes — never prose about a page
having changed. Spec: `plugin/capabilities/intel/README.md`; OCI v0.1 §5.5 and §7.4.

The deterministic half is a script; this skill does the reading and the judgement, and every write
goes through `project-state` (`entity_put` / `entity_patch` / `log_append` when the local server or
the connector serves the project). `<plugin>` below is the plugin root — the folder holding
`capabilities/`, two levels up from this skill's folder; in this repo, the repo root.

## Context, every invocation

Via `project-state`: `capabilities.intel` (refuse when disabled or `focus` is missing — no focus,
no monitoring), `competitive.monitor` (connector defaults, material categories), `intel/watch.yaml`,
`state/intel.json → monitor`. Then:

```bash
python3 <plugin>/capabilities/intel/scripts/monitor.py <facility>/project-state plan --json
```

It returns the sources that are **due** (never read, or read longer ago than `every_days` /
`cadence_days`), for each the **current claims it can settle** (id, statement, status, derived
freshness), the sources already read this cycle, paused ones, in-scope competitors **not watched**,
and material categories no source covers.

## `run [--source <id>]` — the weekly matrix entry

For each due source (or the one named), in plan order:

1. **Read it through its connector, and only it.** `web.read` → fetch the `ref`. `deals.read` →
   the tender entities and `intel/deals/*/context.md` that name the entity (a CRM only through a
   connector exposing `deals.read`, never by product name). `documents.search` → registered
   documents and inbox files tagged for the entity. Read only what the source's `categories` can
   settle. **Lawful collection**: public pages on the publisher's terms; no logins, no pretexting,
   no paywalled or NDA'd material, no crawling beyond the listed `ref`. A source that moved, went
   behind a login or failed is **unreachable** — record it and move on; never work around it.
2. **Compare with its current claims.**
   - *Says the same* → nothing is written; the source's cursor records `unchanged`.
   - *Contradicts a stored claim* → a new claim (`templates/entities/C.yaml`) with
     `supersedes: <old id>`, `logged_by: intel-monitor`, `retrieved_at` today, `source.method`
     from the connector, `source.class` and `epistemic_status` from
     `competitive.monitor.connectors[<via>]` (`by-owner`: vendor-primary on the entity's own
     domain, press elsewhere; `by-document`: the registered document's class; deals and
     messages default to `internal-observation`, `reported`), confidence by the rubric. The old
     claim is never edited. Log `intel.claim.logged` and `intel.claim.superseded`.
   - *Says something new in its categories* → a new claim, `logged_by: intel-monitor`.
   - *Disagrees without settling it* (a page and a buyer's email differ) → the new claim and
     `conflicts_with` on **both**; `intel.conflict.recorded`. Never a silent choice.
   - *No longer says something it said* (a tier is gone) → that absence is the new assertion —
     write it as a claim that supersedes; do not delete anything.
3. **Classify the delta.** Run
   ```bash
   python3 <plugin>/capabilities/intel/scripts/monitor.py <facility>/project-state diff --since <monitor.last_run> --json
   ```
   Every non-noise delta with no change event (`unrecorded`) gets one — `templates/entities/X.yaml`:
   `before` / `after` claim ids, `change_type`, `significance`, `affected` teams and a specific
   `recommended_action`, `detected_by: intel-monitor`; log `intel.change.detected`. Start from the
   script's classification (a superseded material claim in a material category is material; a new
   material assertion from a watched source is notable; the rest is noise); you may move one
   step with a stated reason in the action ("cosmetic re-wording of the same three tiers → noise").
   **An event nobody owns is noise** — if you cannot name who acts, class it noise.
4. **Record the run.** `state/intel.json → monitor.sources[<id>] = {last_checked, last_status:
   unchanged|changed|unreachable, last_changed}` and `monitor.last_run`, through project-state.
   Write `intel/monitor/runs/YYYY-MM-DD.md` from `templates/monitor-run.md` (changed · checked,
   nothing changed — with the claim ids confirmed · could not read · not watched). Log
   `intel.monitor.completed` `{sources: {due, checked, unchanged, changed, unreachable}, claims_logged,
   changes: {material, notable, noise}}`.
5. **Re-render** the Competitive report:
   `python3 <plugin>/capabilities/intel/views/build-intel-competitive.py <facility>/project-state`.

**Unattended** (the matrix entry): no questions. Anything that needs a person — a proposed new
entity, a source that moved, a category no source covers — goes into the run report and the
digest (`intel.monitor-overdue`, `intel.change-material`), never into a write.

**Reply** (attended): material changes first, each with before → after ids and the action; then
what was confirmed unchanged; what could not be read; what is not watched. If nothing changed,
say so in one line: *the watch list was read; nothing changed.*

## `watch [--propose]` — build the watch list

Propose `intel/watch.yaml` entries from what the store already cites: for each in-scope competitor
(and `self`), the distinct `source.ref` values of its current claims, grouped with the categories
they settle; add a `deals.read` source per competitor when deals name it and a `documents.search`
source when the inbox does. Show the proposal; write only what the operator confirms
(`intel.watch.updated`). Retire a source by `status: retired`, never by deleting the line. A
competitor in scope with no source is named, not guessed at.

## `status`

The plan in words: due and overdue sources, the last run, connectors in use (L2 needs two beyond
`web.read`), competitors not watched and material categories nothing reads.

## Discipline

Change is a claim delta · claims and changes are append-only · noise suppressed, not deleted ·
every event owned or it is noise · only the listed sources, only their categories · unreachable is
recorded, never worked around · nothing leaves the project from here (a change worth telling a
team goes through `intel-brief` or `project-notifier`, gated) · all writes through `project-state`.
