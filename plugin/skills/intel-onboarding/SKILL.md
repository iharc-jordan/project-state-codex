---
name: intel-onboarding
description: "Set up the intel (competitive intelligence) capability on a project — 'enable intel', 'set up competitive intelligence', 'onboard intel'. Asks for the focus, entity types and staleness threshold."
map:
  tier: capability
  stage: ingest
  requires: [memory, python]
  inputs: [operator]
  writes: [manifest, intel]
  calls: [project-state]
---

# intel-onboarding — the enable flow

> **When to use.**
>
> Guided enablement of the intel capability for a project. Gathers the REQUIRED focus (the harvester's relevance lens), entity and mandate types, and staleness threshold conversationally; calls the memory layer's `enable intel` (manifest block, intel/ directories, agenda, state/intel.json); then optionally seeds 3-5 starter entities and first P0 agenda questions, proposed and confirmed before writing. Also 'intel-onboarding competitive' — the competitive layer's setup (plugin/capabilities/intel/README.md): declares the self entity (us), confirms which competitor entities are in scope, optional audiences and half-life overrides, writes capabilities.intel.competitive. Trigger on 'enable intel', 'set up intelligence for this project', 'turn on the intel capability', 'start tracking the ecosystem', 'set up competitive intelligence', 'declare our self entity', or the digest's intel.not-initialized, intel.no-focus or intel.no-self. Refuses to enable without a focus. Routes every write through project-state.

Make the intel capability active for one project, with enough declared context that the
harvester can judge relevance from day one. Enable without a focus is refused — that is
the capability's `fiscal_year_end`.

## Step 1 — Preconditions

- Locate the host `project-state/` (walk up from cwd). No facility → point at
  `project-intake` / `project-scaffolder` and stop.
- `capabilities.intel` already enabled → report status and offer the seeding steps only.

## Step 2 — Gather (one conversational pass, not one-at-a-time)

**Required:** `focus` — 1–3 sentences: what ecosystem is being mapped, for what product or
pursuit, and what "relevant" means here. Pre-fill from the project manifest's description
and confirm rather than asking cold.

**Offered with defaults:** `entity_types` (vendor, competitor, regulator, partner,
infrastructure) · `mandate_types` (integration-partnership, licensing, pilot,
research-engagement) · `staleness_threshold_days` (14) · pack (`intel-default`).

## Step 3 — Enable

Call the memory layer: `project-state enable intel` with the gathered config. That verb —
not this skill — takes the manifest lock, writes the `capabilities.intel` block, scaffolds
`intel/{entities,signals,mandates,network,reports}`, seeds `intel/agenda.yaml` and
`state/intel.json` from the capability templates, and logs `capability.enabled`.

## Step 4 — Seed (optional, always confirmed)

- **Starter entities:** propose 3–5 obvious players from the focus, each with name, type,
  priority, one-line why. On confirmation write via `project-state` (`intel.entity.added`).
- **First agenda:** propose 3–5 P0 questions the focus implies. On confirmation write to
  `intel/agenda.yaml`.

Never auto-create — the operator decides what to track.

## Step 5 — Report

Enabled config, seeded entities and questions, and next steps: `/intel-harvester longlist
--dry-run` to preview research, drop documents in `documents/inbox/` for `/intel-ingest`,
and note that the daily digest now carries the intel checks — there is no separate intel
briefing to run. Render the desk's first **At a glance** page now
(`python3 capabilities/intel/views/build-intel-glance.py <facility>/project-state`) so the
app's Intel page shows this project's own map — however sparse — instead of the shipped
fixture sample it displays until the first render.

## `competitive` — the competitive layer's setup (intel 1.1)

Run after enablement, or when the digest raises `intel.no-self`. One conversational pass:

1. **Self.** "What are we, in this Project's terms?" Create (or pick) an entity of type
   `self` — name, one-line summary, URLs — and write `competitive.self_entity`. Add `self`
   and `adjacent` to `entity_types` if a 1.0 project lacks them.
2. **Scope.** List the entities of type `competitor`; confirm which are in scope
   (`competitive.competitors`, empty = all of them). Propose obvious missing competitors
   from the focus; write only the ones confirmed.
3. **Audiences** (optional). `{id, persona, segment, geography}` variants a battlecard
   should exist for — e.g. `cio-enterprise`.
4. **Half-lives** (optional). Show the OCI defaults; record overrides only when the
   operator has a reason (a fast-moving pricing market → 60). The table in the manifest
   block is the documented one.
5. **Next steps.** `/intel-harvester competitor self` first — the battlecard's three-part
   test needs claims about us — then `competitor <id>` per competitor, then
   `/intel-battlecard <id>`. The weekly refresh and the monthly brief are already in the
   matrix from the pack.

The app's Position setup stage writes `self_entity` as a scalar (`manifest_set`); older manifests
may hold a one-element list from the list-only action — read either shape.

## `watch` — the monitor and win-loss setup (intel 1.2)

After `competitive`, or when the digest raises `intel.unwatched-competitor`: hand over to
`/intel-monitor watch` to propose the watch list from the sources the claims already cite, confirm
the weekly monitor and the quarterly win-loss analysis are in the matrix (`intel-weekly-monitor`,
`intel-quarterly-winloss` from the pack), and ask for the last two or three closed deals —
`/intel-winloss record <ref>` each — so the first analysis has a sample. A project on 1.1 gains
`intel/watch.yaml`, `intel/winloss/`, `intel/monitor/` and the new counters the first time either
skill writes; `version:` in the manifest block moves to 1.2.0 through project-state.

## `migrate <intel-state folder>` — from a standalone facility

A project that used the retired standalone intel-state suite moves into the capability with the
migration script (plugin/capabilities/intel/README.md). Plan first, always:

```bash
python3 <plugin>/capabilities/intel/scripts/migrate_intel_state.py <intel-state folder> <facility>/project-state
```

Show the plan — counts, the id map (`FRM-C-002 → INT-E-002`), the types it will add, the
proposed focus from the old facility's description, mandates with no named client (they get the
self entity, tagged `migration:entity-unassigned`), inbox files it will not move. Settle the
focus with the operator (the old description is a proposal, not the focus), then:

```bash
python3 <plugin>/capabilities/intel/scripts/migrate_intel_state.py <intel-state folder> <facility>/project-state --write --actor <operator email> --focus "<the focus>"
```

The old tree is never changed; re-running skips what was already migrated. Then validate, run
`competitive`, and tell the operator the old folder can be archived when they are ready — theirs
to do, not this skill's.

## Discipline

- Refuse on missing `focus`; refuse on prefix collision (memory layer enforces).
- All writes through `project-state`; this skill holds no state and takes no locks itself.
